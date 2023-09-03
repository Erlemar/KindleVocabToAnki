import datetime
import sqlite3
import tempfile
from typing import List

import altair as alt
import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
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
def make_more_columns(data: pd.DataFrame, lang: str, to_translate: List[str]) -> pd.DataFrame:
    """
    Create additional columns.

    Args:
        data: pandas DataFrame with the data
        lang: target language for translation
        to_translate: columns to translate

    Returns:
        processed data.

    """
    for col in to_translate:
        data[f'translated_{col.lower()}'] = translate(
            list(data[['Word language', col]].itertuples(index=False, name=None)), lang
        )

    data['sentence_with_highlight'] = data.apply(lambda x: x.Sentence.replace(x.Word, '_'), axis=1)
    data['sentence_with_cloze'] = data.apply(
        lambda x: x.Sentence.replace(x.Word, f'{{c1::{x.translated_word}}}'), axis=1
    )
    # print(f'{data.shape = } in make_more_columns')
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
    df['Year-month'] = (
        pd.to_datetime(df['Timestamp']).dt.year.astype(str)
        + '-'
        + pd.to_datetime(df['Timestamp']).dt.month.astype(str)
    )
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

    d = (
        df['Book title']
        .value_counts()
        .reset_index()
        # .rename(columns={'index': 'Book title', 'Book title': 'Count'})
        .head(5)
    )

    chart_ = (
        alt.Chart(d)
        .mark_bar()
        .encode(y=alt.Y('Book title:N').sort('-x'), x=alt.X('count:Q'), tooltip=['Book title', 'count'])
        .properties(title='Number of words in top 5 books')
        .interactive()
    )

    chart1 = (
        alt.Chart(d)
        .mark_arc()
        .encode(color=alt.Y('Book title:N'), theta=alt.X('count:Q'), tooltip=['Book title', 'count'])
        .properties(title='Number of words in top 5 books')
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)
    st.altair_chart(chart1, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label='Number of words', value=df.shape[0], help='Number of unique words in the vocabulary')
    col2.metric(
        label='Number of books', value=df['Book title'].nunique(), help='Number of unique books in the vocabulary'
    )
    col3.metric(
        label='Number of Languages',
        value=df['Word language'].nunique(),
        help='Number of unique languages in the vocabulary',
    )
    col4.metric(
        label='Number of reading days', value=df['date'].nunique(), help='Number of days with at least one word marked'
    )
