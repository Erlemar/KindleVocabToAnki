import time

import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator

from src.utils import make_more_columns


st.subheader('Define translation parameters')
my_expander2 = st.expander(label='Translation parameters', expanded=True)

if 'loaded_data' in st.session_state and st.session_state.loaded_data.shape[0] > 0:

    st.session_state.data = st.session_state.loaded_data.copy()
    with my_expander2:
        # limit the number of rows
        col1_, col2_ = st.columns(2)
        with col1_:
            top_n: int = int(
                st.number_input(
                    'Take last N rows',
                    min_value=1,
                    max_value=st.session_state.data.shape[0],
                    value=st.session_state.data.shape[0],
                )
            )
        with col2_:
            col_by = st.selectbox(
                'Sort data by', options=['Timestamp', 'Word'], help='Select the column to sort the data by'
            )

        st.session_state.data = st.session_state.data.sort_values(col_by)[-top_n:]
        d = st.date_input(
            label='Starting date',
            value=pd.to_datetime(st.session_state.data['Timestamp']).dt.date.min(),
            min_value=pd.to_datetime(st.session_state.data['Timestamp']).dt.date.min(),
            max_value=pd.to_datetime(st.session_state.data['Timestamp']).dt.date.max(),
            help='Change this value if you want to limit the st.session_state.data by the start date',
        )
        st.session_state.data = st.session_state.data.loc[
            pd.to_datetime(st.session_state.data['Timestamp']).dt.date >= d
        ]
        # select the target language
        langs_list = GoogleTranslator().get_supported_languages()

        col1__, col2__ = st.columns(2)
        with col1__:
            lang = st.selectbox('Lang to translate into', options=langs_list, index=langs_list.index('english'))
            lang = GoogleTranslator().get_supported_languages(as_dict=True)[lang]
        with col2__:
            translate_option = st.selectbox(
                'Word translation style',
                options=['Word only', 'Use context'],
                help='Translate the word by itself or use the whole phrase as a context',
            )

        to_translate = st.multiselect(
            label='What to translate (select one or multiple)',
            options=['Word', 'Stem', 'Sentence'],
            default=['Word'],
            help='Select the columns that will be translated',
        )

        books = st.multiselect(
            label='Filter by books',
            options=st.session_state.data['Book title'].unique(),
            default=st.session_state.data['Book title'].unique(),
            help='Select the books that will be translated',
        )
        if len(books) > 0:
            st.session_state.data = st.session_state.data.loc[st.session_state.data['Book title'].isin(books)]
        authors = st.multiselect(
            label='Filter by authors',
            options=st.session_state.data['Authors'].unique(),
            default=st.session_state.data['Authors'].unique(),
            help='Select the Authors that will be translated',
        )
        if len(authors) > 0:
            st.session_state.data = st.session_state.data.loc[st.session_state.data['Authors'].isin(authors)]

        langs_from = st.multiselect(
            label='Languages to translate',
            options=st.session_state.data['Word language'].unique(),
            default=st.session_state.data['Word language'].unique(),
            help='Select the languages that will be translated',
        )
        if len(langs_from) > 0:
            st.session_state.data = st.session_state.data.loc[st.session_state.data['Word language'].isin(langs_from)]

        st.write(f'{st.session_state.data.shape[0]} texts will be translated (using Google Translate)')
        st.session_state.loaded_data = st.session_state.data
        st.dataframe(
            st.session_state.data.reset_index(drop=True).drop(
                [col for col in st.session_state.data.columns if 'with' in col or 'translated' in col], axis=1
            )
        )
    if st.session_state.data is None:
        st.session_state.data = st.session_state.loaded_data

    st.session_state.translate = st.button(
        'Translate', on_click=make_more_columns, args=(st.session_state.data, lang, to_translate, translate_option)
    )

    if st.session_state.translate or st.session_state.load_state:
        time.sleep(1)

        st.session_state.load_state = True
        translated_data = st.session_state.translated_df
        st.success('Translation finished!', icon='✅')
        st.dataframe(translated_data.drop([col for col in translated_data.columns if 'with' in col], axis=1))

else:
    st.write('You need to upload some data in order to translate it.')
