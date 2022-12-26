import sqlite3
import tempfile
from typing import List

import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator
from stqdm import stqdm


@st.cache(suppress_st_warning=True)
def translate_words(data: pd.DataFrame) -> List[str]:
    """
    Translate the words.

    # TODO write a generic function for translation and let user decide what to translate (word or/and stem)

    Args:
        data: pandas dataframe with the data

    Returns:
        the list of the translated words
    """
    translated_words = []
    for _, row in stqdm(data.iterrows(), total=data.shape[0], desc='Translating...'):
        translated = GoogleTranslator(source=row.word_lang, target='en').translate(row.word)
        translated_words.append(translated)
    return translated_words


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
        SELECT WORDS.stem, WORDS.word, WORDS.lang, LOOKUPS.usage, BOOK_INFO.title, BOOK_INFO.authors, LOOKUPS.timestamp
          FROM LOOKUPS
          LEFT JOIN WORDS
            ON WORDS.id = LOOKUPS.word_key
          LEFT JOIN BOOK_INFO
            ON BOOK_INFO.id = LOOKUPS.book_key
         ORDER BY WORDS.stem, LOOKUPS.timestamp
    """

    cur.execute(sql)
    data = cur.fetchall()
    data = pd.DataFrame(
        data, columns=['stem', 'word', 'word_lang', 'example', 'book_title', 'book_authors', 'timestamp']
    )
    return data


def make_more_columns(data: pd.DataFrame) -> pd.DataFrame:
    """
    Create additional columns.

    Args:
        data: pandas DataFrame with the data

    Returns:
        processed data.

    """
    translated_words = translate_words(data)

    data['definition'] = translated_words

    data['sentence_with_brackets'] = data.apply(lambda x: x.example.replace(x.word, f'{{{x.word}}}'), axis=1)
    data['sentence_with_different_brackets'] = data.apply(lambda x: x.example.replace(x.word, f'[{x.word}]'), axis=1)
    data['sentence_with_cloze'] = data.apply(lambda x: x.example.replace(x.word, f'{{c1::{x.definition}}}'), axis=1)
    return data
