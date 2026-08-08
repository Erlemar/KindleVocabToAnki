import datetime
import sqlite3
import tempfile
import textwrap
from typing import List, Tuple

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
def translate(data: List[Tuple[str, str]], lang: str) -> List[str]:
    """
    Translate text.

    Args:
        data: list of tuples (source_lang, text)
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
def translate_with_context(data: List[Tuple[str, str, str]], lang: str) -> List[str]:
    """
    Translate text with context.

    Args:
        data: list of tuples (source_lang, sentence, word)
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
def translate_openai(data: List[Tuple[str, str, str]], lang: str, api_key: str, model: str) -> List[str]:
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
        'gpt-4.1-nano': {'input': 0.10, 'output': 0.40},
        'gpt-4.1-mini': {'input': 0.40, 'output': 1.60},
        'gpt-4.1': {'input': 2.00, 'output': 8.00},
        'gpt-5-nano': {'input': 0.05, 'output': 0.40},
        'gpt-5-mini': {'input': 0.25, 'output': 2.00},
        'gpt-5': {'input': 1.25, 'output': 10.00},
    }
    cost_info = costs_per_1m.get(model, costs_per_1m['gpt-4o-mini'])
    # With batching (10 words per call), tokens per word decrease
    input_tokens = n_words * 80
    output_tokens = n_words * 20
    cost = (input_tokens / 1_000_000) * cost_info['input'] + (output_tokens / 1_000_000) * cost_info['output']
    return f'~${cost:.4f}'


LANGUAGE_NAMES = {
    'ar': 'Arabic',
    'ca': 'Catalan',
    'cs': 'Czech',
    'da': 'Danish',
    'de': 'German',
    'el': 'Greek',
    'en': 'English',
    'es': 'Spanish',
    'fi': 'Finnish',
    'fr': 'French',
    'he': 'Hebrew',
    'hi': 'Hindi',
    'hu': 'Hungarian',
    'it': 'Italian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'nl': 'Dutch',
    'no': 'Norwegian',
    'pl': 'Polish',
    'pt': 'Portuguese',
    'ro': 'Romanian',
    'ru': 'Russian',
    'sv': 'Swedish',
    'tr': 'Turkish',
    'uk': 'Ukrainian',
    'zh': 'Chinese',
}


def language_name(code: str) -> str:
    """Turn a Kindle language code like 'de' or 'en-GB' into a readable name."""
    base = str(code).split('-')[0].split('_')[0].strip().lower()
    if base in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[base]
    if base in ('', 'unknown', 'nan', 'none'):
        return 'Unknown'
    return str(code).upper()


def is_dark_theme() -> bool:
    """Best-effort detection of the active Streamlit theme (False outside a runtime)."""
    try:
        return st.context.theme.type == 'dark'
    except Exception:
        return False


def show_vocabulary_stats(df: pd.DataFrame) -> None:
    """
    Show various statistics based on the data.

    Args:
        df: dataframe with data

    Returns:
        Nothing
    """
    dark = is_dark_theme()
    accent = '#7C7CEB' if dark else '#5B5BD6'
    trend_color = '#F2A33C' if dark else '#D97706'
    text_color = '#FAFAFA' if dark else '#31333F'
    surface_color = '#0E1117' if dark else '#FFFFFF'
    empty_cell_color = '#262B36' if dark else '#EBEDF0'
    # Single-hue indigo ramp for the calendar, anchored to the surface of each theme
    calendar_ramp = (
        ['#3E4283', '#575CB5', '#7A7EE0', '#A3A6F7'] if dark else ['#D9DAF8', '#ADAFF1', '#8285E5', '#5153C8']
    )
    # CVD-validated categorical palette (slot 1 is the app accent)
    category_palette = (
        [accent, '#D95926', '#199E70', '#C98500', '#D55181']
        if dark
        else [accent, '#EB6834', '#1BAF7A', '#EDA100', '#E87BA4']
    )
    other_color = '#6B7280' if dark else '#9CA3AF'

    def style_chart(chart):
        """Apply the same quiet, editorial styling to every statistics chart."""
        return (
            chart.configure_view(strokeWidth=0)
            .configure_axis(
                domain=False,
                gridOpacity=0.25,
                labelFontSize=12,
                labelPadding=8,
                tickSize=0,
                titleFontSize=12,
                titlePadding=12,
            )
            .configure_legend(
                direction='horizontal',
                labelFontSize=12,
                orient='bottom',
                symbolType='square',
                titleFontSize=12,
            )
        )

    def format_days(days: int) -> str:
        return f'{days:,} day' if days == 1 else f'{days:,} days'

    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    if df.empty:
        st.info('No dated vocabulary lookups are available for statistics.')
        return

    df['date'] = df['timestamp'].dt.normalize()
    df['month'] = df['timestamp'].dt.to_period('M').dt.to_timestamp()

    total_words = len(df)
    unique_words = df['Word'].nunique()
    active_days = df['date'].nunique()
    avg_per_active_day = total_words / active_days
    df['Book title'] = df['Book title'].fillna('Unknown book')
    book_df = (
        df.groupby('Book title')
        .agg(count=('Book title', 'size'), author=('Authors', 'first'))
        .sort_values('count', ascending=False)
        .reset_index()
    )
    book_df['author'] = book_df['author'].fillna('Unknown author')
    language_counts = df['Word language'].map(language_name).value_counts()
    first_date = df['date'].min()
    latest_date = df['date'].max()

    dates_sorted = sorted(df['date'].unique())
    longest_streak = 1
    latest_streak = 1
    for previous_date, current_date in zip(dates_sorted, dates_sorted[1:]):
        if (current_date - previous_date).days == 1:
            latest_streak += 1
            longest_streak = max(longest_streak, latest_streak)
        else:
            latest_streak = 1

    recent_period_start = latest_date - pd.Timedelta(days=29)
    recent_words = int(df['date'].between(recent_period_start, latest_date).sum())

    month_index = pd.date_range(df['month'].min(), df['month'].max(), freq='MS')
    monthly = df.groupby('month').size().reindex(month_index, fill_value=0).rename('words').reset_index()
    monthly = monthly.rename(columns={'index': 'month'})
    monthly['rolling_average'] = monthly['words'].rolling(3, min_periods=1).mean()
    month_tick_stride = max(1, (len(monthly) + 6) // 7)
    month_tick_values = monthly['month'].iloc[::month_tick_stride].tolist()
    if month_tick_values[-1] != monthly['month'].iloc[-1]:
        month_tick_values.append(monthly['month'].iloc[-1])

    metric_columns = st.columns(4, gap='small')
    metric_columns[0].metric(
        label='Lookups',
        value=f'{total_words:,}',
        help='Total vocabulary lookups',
        border=True,
    )
    metric_columns[1].metric(
        label='Unique words',
        value=f'{unique_words:,}',
        help='Distinct words looked up',
        border=True,
    )
    metric_columns[2].metric(
        label='Active days',
        value=f'{active_days:,}',
        help='Days with at least one lookup',
        border=True,
    )
    metric_columns[3].metric(
        label='Best streak',
        value=format_days(longest_streak),
        help='Longest run of consecutive active days',
        border=True,
    )
    st.caption(
        f'{len(book_df):,} books  ·  {len(language_counts):,} languages  ·  '
        f'{first_date:%d %b %Y} – {latest_date:%d %b %Y}'
    )
    st.caption(
        f'{recent_words:,} lookups in the latest 30 days  ·  {avg_per_active_day:.1f} avg per active day  ·  '
        f'Latest streak: {format_days(latest_streak)}'
    )

    hover = alt.selection_point(fields=['month'], nearest=True, on='pointerover', empty=False)
    activity_domain = [
        monthly['month'].min() - pd.Timedelta(days=15),
        monthly['month'].max() + pd.Timedelta(days=15),
    ]
    # Bars on a continuous time scale default to 5px; scale the width to the month count instead
    bar_size = max(2, min(28, 620 // len(monthly) - 4))
    activity_base = alt.Chart(monthly).encode(
        x=alt.X(
            'month:T',
            axis=alt.Axis(
                format='%b %Y',
                grid=False,
                labelAngle=0,
                title=None,
                values=month_tick_values,
            ),
            scale=alt.Scale(domain=activity_domain),
        )
    )
    activity_bars = activity_base.mark_bar(
        color=accent,
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4,
        opacity=0.82,
        size=bar_size,
    ).encode(
        y=alt.Y('words:Q', axis=alt.Axis(format=',d', tickCount=5, title=None), scale=alt.Scale(zero=True)),
        tooltip=[
            alt.Tooltip('month:T', format='%B %Y', title='Month'),
            alt.Tooltip('words:Q', format=',d', title='Lookups'),
        ],
    )
    # An explicit axis=None on any layer would suppress the shared y-axis, so only hide titles here
    rolling_line = activity_base.mark_line(color=trend_color, strokeWidth=2.5).encode(
        y=alt.Y('rolling_average:Q', title=None)
    )
    rolling_points = activity_base.mark_point(color=trend_color, filled=True, size=65).encode(
        y=alt.Y('rolling_average:Q', title=None),
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
    )
    hover_rule = activity_base.mark_rule(color=accent).encode(
        opacity=alt.condition(hover, alt.value(0.28), alt.value(0)),
        tooltip=[
            alt.Tooltip('month:T', format='%B %Y', title='Month'),
            alt.Tooltip('words:Q', format=',d', title='Lookups'),
            alt.Tooltip('rolling_average:Q', format='.1f', title='3-month average'),
        ],
    )
    hover_target = (
        activity_base.mark_point(opacity=0, size=400).encode(y=alt.Y('words:Q', title=None)).add_params(hover)
    )
    latest_month_label = (
        alt.Chart(monthly.tail(1))
        .mark_text(align='right', color=accent, dx=-4, dy=-9, fontWeight=600)
        .encode(x='month:T', y=alt.Y('words:Q', title=None), text=alt.Text('words:Q', format=','))
    )
    activity_chart = style_chart(
        (activity_bars + rolling_line + rolling_points + hover_rule + hover_target + latest_month_label).properties(
            height=300
        )
    )

    activity_caption = 'Bars show lookups; the line shows the three-month average.'
    if latest_date < latest_date + pd.offsets.MonthEnd(0):
        activity_caption += f' The last month is partial (data through {latest_date:%d %b}).'
    st.markdown('#### Monthly activity')
    st.caption(activity_caption)
    st.altair_chart(activity_chart, width='stretch')

    window_start = max(latest_date - pd.Timedelta(days=364), first_date)
    window_start -= pd.Timedelta(days=window_start.weekday())
    calendar_dates = pd.date_range(window_start, latest_date, freq='D')
    daily_counts = df.groupby('date').size()
    calendar = pd.DataFrame({'date': calendar_dates})
    calendar['count'] = calendar['date'].map(daily_counts).fillna(0).astype(int)
    calendar['week_start'] = calendar['date'] - pd.to_timedelta(calendar['date'].dt.dayofweek, unit='D')
    calendar['week_end'] = calendar['week_start'] + pd.Timedelta(days=6)
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    calendar['day_name'] = calendar['date'].dt.dayofweek.map(dict(enumerate(day_names)))

    calendar_chart = (
        alt.Chart(calendar)
        .mark_rect(cornerRadius=2)
        .encode(
            x=alt.X(
                'week_start:T',
                axis=alt.Axis(
                    format='%b',
                    grid=False,
                    labelAngle=0,
                    tickCount='month',
                    title=None,
                ),
            ),
            x2='week_end:T',
            y=alt.Y(
                'day_name:O',
                axis=alt.Axis(grid=False, title=None),
                scale=alt.Scale(paddingInner=0.16, paddingOuter=0.04),
                sort=day_names,
            ),
            # Days with zero lookups get a neutral cell so they never blend into the activity ramp
            color=alt.condition(
                'datum.count === 0',
                alt.value(empty_cell_color),
                alt.Color(
                    'count:Q',
                    legend=None,
                    scale=alt.Scale(
                        domain=[1, max(2, int(calendar['count'].max()))],
                        range=calendar_ramp,
                        type='quantize',
                    ),
                ),
            ),
            tooltip=[
                alt.Tooltip('date:T', format='%A, %d %B %Y', title='Date'),
                alt.Tooltip('count:Q', format=',d', title='Lookups'),
            ],
        )
    )
    # Keep the cells roughly square: height follows the number of weeks in the window
    n_weeks = max(1, round(len(calendar_dates) / 7))
    cell_width = 620 / n_weeks * (6 / 7)
    calendar_height = int(min(170, max(92, cell_width * 7 / 0.84)))
    calendar_chart = style_chart(calendar_chart.properties(height=calendar_height))
    st.markdown('#### Activity calendar')
    st.caption(f'{window_start:%d %b %Y} – {latest_date:%d %b %Y}  ·  Darker cells mean more lookups.')
    st.altair_chart(calendar_chart, width='stretch')

    hours = (
        df['timestamp']
        .dt.hour.value_counts()
        .reindex(range(24), fill_value=0)
        .rename_axis('hour')
        .reset_index(name='count')
    )
    hours['hour_label'] = hours['hour'].map(lambda hour: f'{hour:02d}:00')
    peak_hour = int(hours.loc[hours['count'].idxmax(), 'hour'])
    hour_chart = (
        alt.Chart(hours)
        .mark_bar(color=accent, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(
                'hour_label:O',
                axis=alt.Axis(
                    grid=False,
                    labelAngle=0,
                    title=None,
                    values=[f'{hour:02d}:00' for hour in range(0, 24, 3)],
                ),
                scale=alt.Scale(paddingInner=0.25),
                sort=hours['hour_label'].tolist(),
            ),
            y=alt.Y('count:Q', axis=alt.Axis(format=',d', tickCount=4, title=None)),
            opacity=alt.condition(f'datum.hour === {peak_hour}', alt.value(1), alt.value(0.55)),
            tooltip=[
                alt.Tooltip('hour_label:N', title='Hour'),
                alt.Tooltip('count:Q', format=',d', title='Lookups'),
            ],
        )
    )
    hour_chart = style_chart(hour_chart.properties(height=220))
    st.markdown('#### When you read')
    st.caption(f'Lookups by hour of day (device time)  ·  Most lookups happen around {peak_hour:02d}:00.')
    st.altair_chart(hour_chart, width='stretch')

    top_books = book_df.head(8).copy()
    top_books['display_title'] = top_books['Book title'].map(
        lambda title: '|'.join(
            textwrap.wrap(
                title,
                width=52,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    )
    max_book_label_lines = top_books['display_title'].str.count(r'\|').max() + 1
    book_domain_max = max(top_books['count'].max() * 1.18, 1)
    book_base = alt.Chart(top_books).encode(
        y=alt.Y(
            'display_title:N',
            axis=alt.Axis(
                grid=False,
                labelExpr="split(datum.label, '|')",
                labelLimit=520,
                labelLineHeight=14,
                title=None,
            ),
            sort=alt.EncodingSortField(field='count', order='descending'),
        ),
        tooltip=[
            alt.Tooltip('Book title:N', title='Book'),
            alt.Tooltip('author:N', title='Author'),
            alt.Tooltip('count:Q', format=',d', title='Lookups'),
        ],
    )
    book_bars = book_base.mark_bar(
        color=accent,
        cornerRadiusBottomRight=4,
        cornerRadiusTopRight=4,
        size=20,
    ).encode(
        x=alt.X(
            'count:Q',
            axis=alt.Axis(format=',d', tickCount=4, title=None),
            scale=alt.Scale(domain=[0, book_domain_max]),
        )
    )
    book_labels = book_base.mark_text(align='left', color=text_color, dx=7).encode(
        x=alt.X('count:Q', scale=alt.Scale(domain=[0, book_domain_max])),
        text=alt.Text('count:Q', format=','),
    )
    book_chart = style_chart(
        (book_bars + book_labels).properties(
            height=max(240, len(top_books) * max(36, max_book_label_lines * 14 + 12)),
        )
    )

    st.markdown('#### Top books')
    st.caption(f'The {len(top_books)} books with the most lookups.')
    st.altair_chart(book_chart, width='stretch')
    if len(book_df) > len(top_books):
        with st.expander(f'All {len(book_df):,} books'):
            st.dataframe(
                book_df.rename(columns={'count': 'Lookups', 'author': 'Author'})[['Book title', 'Author', 'Lookups']],
                column_config={'Lookups': st.column_config.NumberColumn(format='%d')},
                hide_index=True,
                width='stretch',
            )

    language_df = language_counts.rename_axis('Language').reset_index(name='count')
    language_df['share'] = language_df['count'] / language_df['count'].sum()
    # The chart shows at most 5 languages plus an "Other" bucket so colors stay distinguishable
    chart_languages = language_df.head(5).copy()
    if len(language_df) > 5:
        chart_languages.loc[len(chart_languages)] = {
            'Language': 'Other',
            'count': int(language_df['count'].iloc[5:].sum()),
            'share': float(language_df['share'].iloc[5:].sum()),
        }
    chart_languages['rank'] = range(len(chart_languages))
    chart_languages['group'] = 'Vocabulary'
    palette = category_palette[: len(chart_languages)]
    if len(language_df) > 5:
        palette = category_palette[:5] + [other_color]
    language_chart = (
        alt.Chart(chart_languages)
        .mark_bar(cornerRadius=4, size=28, stroke=surface_color, strokeWidth=2)
        .encode(
            x=alt.X('share:Q', axis=None, scale=alt.Scale(domain=[0, 1]), stack='zero'),
            y=alt.Y('group:N', axis=None),
            color=alt.Color(
                'Language:N',
                legend=alt.Legend(columns=min(len(chart_languages), 4), labelLimit=180, title=None),
                scale=alt.Scale(domain=chart_languages['Language'].tolist(), range=palette),
            ),
            order=alt.Order('rank:O'),
            tooltip=[
                alt.Tooltip('Language:N', title='Language'),
                alt.Tooltip('count:Q', format=',d', title='Lookups'),
                alt.Tooltip('share:Q', format='.1%', title='Share'),
            ],
        )
    )
    language_chart = style_chart(language_chart.properties(height=90))

    st.markdown('#### Languages')
    st.caption('Share of vocabulary lookups.')
    st.altair_chart(language_chart, width='stretch')
    language_summary = '  ·  '.join(
        f'{row.Language} {row.count:,} ({row.share:.0%})' for row in language_df.itertuples(index=False)
    )
    st.caption(language_summary)
