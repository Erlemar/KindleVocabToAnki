import sqlite3
import tempfile
from typing import List

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


@st.cache(suppress_st_warning=True)
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


def make_more_columns(data: pd.DataFrame, lang: str, to_translate) -> pd.DataFrame:
    """
    Create additional columns.

    Args:
        data: pandas DataFrame with the data
        lang: target language for translation

    Returns:
        processed data.

    """
    for col in to_translate:
        data[f'translated_{col.lower()}'] = translate(
            list(data[['word_lang', 'word']].itertuples(index=False, name=None)), lang)

    data['sentence_with_brackets'] = data.apply(lambda x: x.example.replace(x.word, f'{{{x.word}}}'), axis=1)
    data['sentence_with_different_brackets'] = data.apply(lambda x: x.example.replace(x.word, f'[{x.word}]'), axis=1)
    data['sentence_with_cloze'] = data.apply(lambda x: x.example.replace(x.word, f'{{c1::{x.translated_word}}}'),
                                             axis=1)
    return data
