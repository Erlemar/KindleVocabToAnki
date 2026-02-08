import datetime
import sqlite3
import tempfile
from typing import List

import altair as alt
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from stqdm import stqdm


def init_session_state():
    """Initialize all session state keys with defaults."""
    defaults = {
        'load_state': False,
        'translated_df': pd.DataFrame(),
        'loaded_data': pd.DataFrame(),
        'data_type': None,
        'data_exists': False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_data_from_vocab(db: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    """
    Extract the data from vocab.db and convert it into pandas DataFrame.

    Args:
        db: uploaded vocab.db

    Returns:
        extracted data.

    """
    con = None
    try:
        with tempfile.NamedTemporaryFile() as fp:
            fp.write(db.getvalue())
            con = sqlite3.connect(fp.name)

        cur = con.cursor()

        sql = """
            SELECT WORDS.word, WORDS.stem, WORDS.lang, LOOKUPS.usage, BOOK_INFO.title, BOOK_INFO.authors, LOOKUPS.timestamp
              FROM LOOKUPS
              LEFT JOIN WORDS
                ON WORDS.id = LOOKUPS.word_key
              LEFT JOIN BOOK_INFO
                ON BOOK_INFO.id = LOOKUPS.book_key
             ORDER BY WORDS.stem, LOOKUPS.timestamp
        """

        cur.execute(sql)
        data_sql = cur.fetchall()
        data = pd.DataFrame(
            data_sql, columns=['Word', 'Stem', 'Word language', 'Sentence', 'Book title', 'Authors', 'Timestamp']
        )
        data['Timestamp'] = data['Timestamp'].apply(
            lambda t: datetime.datetime.fromtimestamp(t / 1000).strftime('%Y-%m-%d %H:%M:%S')
        )
        data = data.sort_values('Timestamp').reset_index(drop=True)
        return data
    except Exception as e:
        st.error(f'Failed to parse vocabulary database: {e}')
        return pd.DataFrame()
    finally:
        if con:
            con.close()


@st.cache_data(ttl=3600)
def translate(data: List, lang: str) -> List[str]:
    """
    Translate text.

    Args:
        data: pandas dataframe with the data
        lang: target language for translating

    Returns:
        the list of the translated words
    """
    translated = []
    for text_lang, text in stqdm(data, total=len(data), desc='Translating...'):
        try:
            translated.append(GoogleTranslator(source=text_lang, target=lang).translate(text))
        except Exception as e:
            st.warning(f'Translation failed for "{text}": {e}')
            translated.append(text)

    return translated


@st.cache_data(ttl=3600)
def translate_with_context(data: List, lang: str) -> List[str]:
    """
    Translate text.

    Args:
        data: pandas dataframe with the data
        lang: target language for translating

    Returns:
        the list of the translated words
    """
    translated = []
    for text_lang, text, word in stqdm(data, total=len(data), desc='Translating...'):
        try:
            translated_text = GoogleTranslator(source=text_lang, target=lang).translate(
                text.replace(word, f'||{word}|')
            )
            translated_word = translated_text.split('||')[1].split('|')[0]
            if translated_word == word:
                translated_word = GoogleTranslator(source=text_lang, target=lang).translate(text)
            translated.append(translated_word)
        except Exception as e:
            st.warning(f'Context translation failed for "{word}": {e}')
            try:
                translated.append(GoogleTranslator(source=text_lang, target=lang).translate(word))
            except Exception:
                translated.append(word)

    return translated


@st.cache_data(ttl=3600)
def translate_openai(data: List, lang: str, api_key: str, model: str) -> List[str]:
    """
    Translate words using OpenAI with sentence context.

    Args:
        data: list of tuples (source_lang, sentence, word)
        lang: target language for translating
        api_key: OpenAI API key
        model: OpenAI model name

    Returns:
        the list of the translated words
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    translated = []

    # Batch translations: process multiple words per API call
    batch_size = 10
    items = list(data)

    for i in stqdm(
        range(0, len(items), batch_size),
        total=(len(items) + batch_size - 1) // batch_size,
        desc='Translating with OpenAI...',
    ):
        batch = items[i : i + batch_size]

        if len(batch) == 1:
            source_lang, sentence, word = batch[0]
            prompt = (
                f'Translate the word "{word}" into {lang}.\n'
                f'Context sentence: "{sentence}"\n'
                f'Source language: {source_lang}\n\n'
                f'Rules:\n'
                f'- Provide 1-3 most common translations, separated by comma\n'
                f'- Use the context to pick the most relevant meaning first\n'
                f'- For verbs, give the base/infinitive form\n'
                f'- Return only the translations, nothing else'
            )
            try:
                result = client.responses.create(model=model, input=prompt)
                translated_word = result.output_text.strip().replace('"', '').replace('\n', ', ')
                if translated_word == word:
                    translated_word = GoogleTranslator(source=source_lang, target=lang).translate(word)
                translated.append(translated_word)
            except Exception as e:
                st.warning(f'OpenAI translation failed for "{word}": {e}')
                try:
                    translated.append(GoogleTranslator(source=source_lang, target=lang).translate(word))
                except Exception:
                    translated.append(word)
        else:
            # Build batch prompt
            words_list = []
            for idx, (source_lang, sentence, word) in enumerate(batch):
                words_list.append(
                    f'{idx + 1}. Word: "{word}" | Sentence: "{sentence}" | Source language: {source_lang}'
                )

            words_block = '\n'.join(words_list)
            prompt = (
                f'Translate each word below into {lang}.\n\n'
                f'{words_block}\n\n'
                f'Rules:\n'
                f'- For each word, provide 1-3 most common translations, separated by comma\n'
                f'- Use the context sentence to pick the most relevant meaning first\n'
                f'- For verbs, give the base/infinitive form\n'
                f'- Return one translation per line, numbered to match the input\n'
                f'- Format: "1. translation1, translation2"\n'
                f'- Return only the numbered translations, nothing else'
            )
            try:
                result = client.responses.create(model=model, input=prompt)
                lines = result.output_text.strip().split('\n')
                parsed = {}
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # Parse "1. translation" format
                    parts = line.split('.', 1)
                    if len(parts) == 2:
                        try:
                            num = int(parts[0].strip())
                            parsed[num] = parts[1].strip().replace('"', '')
                        except ValueError:
                            pass

                for idx, (source_lang, _sentence, word) in enumerate(batch):
                    t = parsed.get(idx + 1, '')
                    if not t or t == word:
                        try:
                            t = GoogleTranslator(source=source_lang, target=lang).translate(word)
                        except Exception:
                            t = word
                    translated.append(t)
            except Exception as e:
                st.warning(f'OpenAI batch translation failed: {e}')
                for source_lang, _sentence, word in batch:
                    try:
                        translated.append(GoogleTranslator(source=source_lang, target=lang).translate(word))
                    except Exception:
                        translated.append(word)

    return translated


@st.cache_data(ttl=3600)
def add_furigana(sentences: List[str], api_key: str, model: str) -> List[str]:
    """
    Add furigana readings to kanji in Japanese sentences.

    Args:
        sentences: list of Japanese sentences
        api_key: OpenAI API key
        model: OpenAI model name

    Returns:
        list of sentences with furigana annotations
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    results = []
    for s in stqdm(sentences, total=len(sentences), desc='Adding furigana...'):
        prompt = (
            'Add furigana readings to the kanji in this Japanese sentence for use in Anki.\n'
            'Format: place the reading in square brackets immediately after each kanji or kanji compound.\n'
            'Add a space before each word that gets furigana — this is required for Anki to render it correctly.\n\n'
            'Rules:\n'
            '- Only add furigana to kanji, never to hiragana, katakana, or punctuation\n'
            '- Preserve the original sentence exactly, only inserting [reading] after kanji\n'
            '- For kanji compounds (jukugo), give the full compound reading as one unit\n'
            '- Always add a space before the kanji/compound that receives furigana\n\n'
            'Examples:\n'
            '- Input: 目を凝らしてよく見てみると、体に、何か網のようなものが絡まっているようだ。\n'
            '  Output: 目[め]を 凝[こ]らしてよく 見[み]てみると、 体[からだ]に、 何[なに]か 網[あみ]のようなものが 絡[から]まっているようだ。\n'
            '- Input: 「変身って…。俺は、戦隊ヒーローか。\n'
            '  Output: 「 変身[へんしん]って…。 俺[おれ]は、 戦隊[せんたい]ヒーローか。\n'
            '- Input: 黄金に輝く海と太陽の狭間にあって、永遠に時を止められた閉じた世界。\n'
            '  Output: 黄金[おうごん]に 輝[かがや]く 海[うみ]と 太陽[たいよう]の 狭間[はざま]にあって、 永遠[えいえん]に 時[とき]を 止[と]められた 閉[と]じた 世界[せかい]。\n\n'
            f'Sentence: {s}\n'
            'Return only the annotated sentence. If a word consists only of hiragana or katakana, do not add furigana to it.'
        )
        try:
            result = client.responses.create(model=model, input=prompt)
            results.append(result.output_text.strip().replace('"', ''))
        except Exception as e:
            st.warning(f'Furigana generation failed for sentence: {e}')
            results.append(s)

    return results


@st.cache_data(show_spinner=False, ttl=3600)
def make_more_columns(
    data: pd.DataFrame,
    lang: str,
    to_translate: List[str],
    translate_option: str,
    translation_backend: str = 'Google Translate',
    openai_api_key: str = '',
    openai_model: str = 'gpt-4o-mini',
    add_furigana_col: bool = False,
) -> pd.DataFrame:
    """
    Create additional columns.

    Args:
        data: pandas DataFrame with the data
        lang: target language for translation
        to_translate: columns to translate
        translate_option: how to translate the word
        translation_backend: 'Google Translate' or 'OpenAI'
        openai_api_key: OpenAI API key (required if backend is OpenAI)
        openai_model: OpenAI model to use
        add_furigana_col: whether to add furigana column for Japanese sentences

    Returns:
        processed data.

    """

    if translation_backend == 'OpenAI' and openai_api_key:
        data['translated_word'] = translate_openai(
            list(data[['Word language', 'Sentence', 'Word']].itertuples(index=False, name=None)),
            lang,
            openai_api_key,
            openai_model,
        )
    elif translate_option == 'Use context':
        data['translated_word'] = translate_with_context(
            list(data[['Word language', 'Sentence', 'Word']].itertuples(index=False, name=None)), lang
        )

    for col in to_translate:
        if col != 'Word' or (col == 'Word' and translate_option == 'Word only' and translation_backend != 'OpenAI'):
            data[f'translated_{col.lower()}'] = translate(
                list(data[['Word language', col]].itertuples(index=False, name=None)), lang
            )

    data['sentence_with_highlight'] = data.apply(lambda x: x.Sentence.replace(x.Word, '_'), axis=1)
    data['sentence_with_cloze'] = data.apply(
        lambda x: x.Sentence.replace(x.Word, f'{{c1::{x.translated_word}}}'), axis=1
    )

    if add_furigana_col and openai_api_key:
        data['sentence_with_furigana'] = add_furigana(list(data['Sentence']), openai_api_key, openai_model)

    return data.reset_index(drop=True)


def estimate_openai_cost(n_words: int, model: str) -> str:
    """Estimate approximate OpenAI API cost for translation."""
    # Rough estimates: ~100 input tokens + ~30 output tokens per word
    costs_per_1m = {
        'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
        'gpt-4o': {'input': 2.50, 'output': 10.00},
        'gpt-5.2': {'input': 2.50, 'output': 10.00},
    }
    cost_info = costs_per_1m.get(model, costs_per_1m['gpt-4o-mini'])
    # With batching (10 words per call), tokens per word decrease
    input_tokens = n_words * 80
    output_tokens = n_words * 20
    cost = (input_tokens / 1_000_000) * cost_info['input'] + (output_tokens / 1_000_000) * cost_info['output']
    return f'~${cost:.4f}'


def show_vocabulary_stats(df: pd.DataFrame) -> None:
    """
    Show various statistics based on the data.

    Args:
        df: dataframe with data

    Returns:
        Nothing
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['Timestamp']).dt.date
    df['Year-month'] = pd.to_datetime(df['Timestamp']).dt.strftime('%Y-%m')

    # Metrics row 1
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label='Word count', value=df.shape[0], help='Total word count in the vocabulary')
    col2.metric(label='Book count', value=df['Book title'].nunique(), help='Book count in the vocabulary')
    col3.metric(
        label='Language count',
        value=df['Word language'].nunique(),
        help='Language count in the vocabulary',
    )
    col4.metric(label='Days with lookups', value=df['date'].nunique(), help='Days with at least one word looked up')

    # Metrics row 2
    active_days = df['date'].nunique()
    total_words = df.shape[0]
    avg_per_day = round(total_words / active_days, 1) if active_days > 0 else 0

    dates_sorted = sorted(df['date'].unique())
    longest_streak = 1
    current_streak = 1
    for i in range(1, len(dates_sorted)):
        if (dates_sorted[i] - dates_sorted[i - 1]).days == 1:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 1

    most_active_book = df['Book title'].value_counts().index[0] if len(df) > 0 else 'N/A'
    date_range = f'{min(dates_sorted)} → {max(dates_sorted)}' if dates_sorted else 'N/A'

    col5, col6, col7, col8 = st.columns(4)
    col5.metric(label='Avg words/day', value=avg_per_day, help='Average words per active day')
    col6.metric(label='Longest streak', value=f'{longest_streak} days', help='Consecutive days with lookups')
    col7.metric(label='Most active book', value=most_active_book[:20], help=most_active_book)
    col8.metric(label='Date range', value=date_range, help='First and last lookup dates')

    # Cumulative word count over time
    d = df.groupby('Year-month')['Sentence'].count().sort_index().reset_index()
    d['count'] = d['Sentence'].cumsum()

    chart = (
        alt.Chart(d)
        .mark_line(point=True, strokeWidth=3)
        .encode(x=alt.X('Year-month:T', timeUnit='yearmonth'), y='count:Q')
        .configure_point(size=20)
        .properties(title='Cumulative word count over time')
        .configure_point(size=50)
        .interactive()
    )
    st.altair_chart(chart, width='stretch')

    # Words per month bar chart
    monthly = df.groupby('Year-month')['Sentence'].count().sort_index().reset_index()
    monthly.columns = ['Year-month', 'count']
    monthly_chart = (
        alt.Chart(monthly)
        .mark_bar()
        .encode(
            x=alt.X('Year-month:T', timeUnit='yearmonth', title='Month'),
            y=alt.Y('count:Q', title='Words'),
            tooltip=[
                alt.Tooltip('Year-month:T', timeUnit='yearmonth', title='Month'),
                alt.Tooltip('count:Q', title='Words'),
            ],
        )
        .properties(title='Words per month')
        .interactive()
    )
    st.altair_chart(monthly_chart, width='stretch')

    # Language distribution
    lang_df = df['Word language'].value_counts().reset_index()
    lang_df.columns = ['Language', 'count']
    lang_chart = (
        alt.Chart(lang_df)
        .mark_bar()
        .encode(
            x=alt.X('count:Q', title='Words'),
            y=alt.Y('Language:N', sort='-x', title='Language'),
            tooltip=['Language', 'count'],
        )
        .properties(title='Words per language')
        .interactive()
    )
    st.altair_chart(lang_chart, width='stretch')

    # Words per book (all books)
    book_df = df['Book title'].value_counts().reset_index()
    book_df.columns = ['Book title', 'count']
    book_chart = (
        alt.Chart(book_df)
        .mark_bar()
        .encode(
            x=alt.X('count:Q', title='Words'),
            y=alt.Y('Book title:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300)),
            tooltip=['Book title', 'count'],
        )
        .properties(title='Words per book', height=max(200, len(book_df) * 20))
        .interactive()
    )
    st.altair_chart(book_chart, width='stretch')

    # Daily activity heatmap
    daily = df.groupby('date').size().reset_index(name='count')
    daily['date'] = pd.to_datetime(daily['date'])
    daily['weekday'] = daily['date'].dt.dayofweek
    daily['week'] = daily['date'].dt.isocalendar().week.astype(int)
    daily['year'] = daily['date'].dt.year
    daily['year_week'] = daily['year'].astype(str) + '-W' + daily['week'].astype(str).str.zfill(2)

    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    daily['day_name'] = daily['weekday'].map(lambda x: day_names[x])

    heatmap = (
        alt.Chart(daily)
        .mark_rect()
        .encode(
            x=alt.X('year_week:O', title='Week', axis=alt.Axis(labels=False)),
            y=alt.Y('day_name:O', title='Day', sort=day_names),
            color=alt.Color('count:Q', scale=alt.Scale(scheme='greens'), title='Words'),
            tooltip=[alt.Tooltip('date:T', title='Date'), alt.Tooltip('count:Q', title='Words')],
        )
        .properties(title='Daily activity heatmap', height=150)
    )
    st.altair_chart(heatmap, width='stretch')
