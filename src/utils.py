import datetime
import sqlite3
import tempfile
from typing import List

import altair as alt
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from openai import OpenAI
from stqdm import stqdm


def get_data_from_vocab(db: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    """
    Extract the data from vocab.db and convert it into pandas DataFrame.

    Args:
        db: uploaded vocab.db

    Returns:
        extracted data.

    """
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


@st.cache_data()
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
        translated.append(GoogleTranslator(source=text_lang, target=lang).translate(text))

    return translated


@st.cache_data()
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
        # mark the word in the sentence
        translated_text = GoogleTranslator(source=text_lang, target=lang).translate(text.replace(word, f'||{word}|'))
        # extract the word from the marked sentence
        translated_word = translated_text.split('||')[1].split('|')[0]
        # in case the translation failed
        if translated_word == word:
            translated_word = GoogleTranslator(source=text_lang, target=lang).translate(text)
        translated.append(translated_word)

    return translated


@st.cache_data()
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
    client = OpenAI(api_key=api_key)
    translated = []
    for source_lang, sentence, word in stqdm(data, total=len(data), desc='Translating with OpenAI...'):
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
        result = client.responses.create(
            model=model,
            input=prompt,
        )
        translated_word = result.output_text.strip().replace('"', '').replace('\n', ', ')
        if translated_word == word:
            translated_word = GoogleTranslator(source=source_lang, target=lang).translate(word)
        translated.append(translated_word)

    return translated


@st.cache_data()
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
        result = client.responses.create(
            model=model,
            input=prompt,
        )
        results.append(result.output_text.strip().replace('"', ''))

    return results


@st.cache_data(show_spinner=False)
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

    st.session_state.translated_df = data.reset_index(drop=True)
    return data


def show_vocabulary_stats(df: pd.DataFrame) -> None:
    """
    Show various statistics based on the data.

    Args:
        df: dataframe with data

    Returns:
        Nothing
    """
    df['date'] = pd.to_datetime(df['Timestamp']).dt.date
    df['Year-month'] = pd.to_datetime(df['Timestamp']).dt.strftime('%Y-%m')
    d = df.groupby('Year-month')['Sentence'].count().sort_index().reset_index()
    d['count'] = d['Sentence'].cumsum()

    chart = (
        alt.Chart(d)
        .mark_line(point=True, strokeWidth=3)
        .encode(x=alt.X('Year-month:T', timeUnit='yearmonth'), y='count:Q')
        .configure_point(size=20)
        .properties(title='Number of word over time')
        .configure_point(size=50)
        .interactive()
    )

    pie_df = df['Book title'].value_counts().reset_index().head(5)

    base = alt.Chart(pie_df).encode(
        alt.Theta('count:Q').stack(True), alt.Color('Book title:N'), tooltip=['Book title', 'count']
    )
    pie = base.mark_arc(outerRadius=120).properties(title='Number of words in top 5 books').interactive()
    text = base.mark_text(radius=140, size=12).encode(text='count:Q')

    st.altair_chart(chart, use_container_width=True)
    st.altair_chart(pie + text, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label='Word count', value=df.shape[0], help='Unique word count in the vocabulary')
    col2.metric(label='Book count', value=df['Book title'].nunique(), help='Book count in the vocabulary')
    col3.metric(
        label='Language count',
        value=df['Word language'].nunique(),
        help='Language count in the vocabulary',
    )
    col4.metric(
        label='Days with looked up works', value=df['date'].nunique(), help='Days with at least one word looked up'
    )
