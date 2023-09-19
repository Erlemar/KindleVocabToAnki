import time

import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator

from src.utils import get_data_from_vocab, make_more_columns, show_vocabulary_stats

data = st.session_state.loaded_data

st.subheader('Define translation parameters')
my_expander2 = st.expander(label='Translation parameters', expanded=True)
with my_expander2:
    # limit the number of rows
    col1_, col2_ = st.columns(2)
    with col1_:
        top_n: int = int(
            st.number_input('Take last N rows', min_value=1, max_value=data.shape[0], value=data.shape[0])
        )
    with col2_:
        col_by = st.selectbox(
            'Sort data by', options=['Timestamp', 'Word'], help='Select the column to sort the data by'
        )

    data = data.sort_values(col_by)[-top_n:]
    d = st.date_input(
        label='Starting date',
        value=pd.to_datetime(data['Timestamp']).dt.date.min(),
        min_value=pd.to_datetime(data['Timestamp']).dt.date.min(),
        max_value=pd.to_datetime(data['Timestamp']).dt.date.max(),
        help='Change this value if you want to limit the data by the start date',
    )
    data = data.loc[pd.to_datetime(data['Timestamp']).dt.date >= d]
    # select the target language
    langs_list = GoogleTranslator().get_supported_languages()
    lang = st.selectbox('Lang to translate into', options=langs_list, index=langs_list.index('english'))
    lang = GoogleTranslator().get_supported_languages(as_dict=True)[lang]

    to_translate = st.multiselect(
        label='What to translate (select one or multiple)',
        options=['Word', 'Stem', 'Sentence'],
        default=['Word'],
        help='Select the columns that will be translated',
    )

    books = st.multiselect(
        label='Filter by books',
        options=data['Book title'].unique(),
        default=data['Book title'].unique(),
        help='Select the books that will be translated',
    )
    data = data.loc[data['Book title'].isin(books)]
    authors = st.multiselect(
        label='Filter by authors',
        options=data['Authors'].unique(),
        default=data['Authors'].unique(),
        help='Select the Authors that will be translated',
    )
    data = data.loc[data['Authors'].isin(authors)]

    langs_from = st.multiselect(
        label='languages to translate',
        options=data['Word language'].unique(),
        default=data['Word language'].unique(),
        help='Select the languages that will be translated',
    )
    data = data.loc[data['Word language'].isin(langs_from)]

    st.write(f'{data.shape[0]} texts will be translated (using Google Translate)')
    st.session_state.loaded_data = data
    st.dataframe(data.reset_index(drop=True))
if data is None:
    data = st.session_state.loaded_data
# TODO: save all the options
st.session_state.translate = st.button('Translate', on_click=make_more_columns, args=(data, lang, to_translate))
# todo add buttons to move between the pages

if st.session_state.translate or st.session_state.load_state:
    # print(f'{translate=} {st.session_state.load_state=}')
    time.sleep(1)

    st.session_state.load_state = True
    # print(f'1{translate=} {st.session_state.load_state=}')
    # print(st.session_state.translated_df)
    translated_data = st.session_state.translated_df
    st.success('Translation finished!', icon='✅')
    st.dataframe(translated_data)
    st.subheader('Customize translated data')
