import os
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

        # Drop duplicate words
        drop_dupes = st.checkbox('Drop duplicate words (keep last occurrence)', value=False)
        if drop_dupes:
            st.session_state.data = st.session_state.data.drop_duplicates('Word', keep='last')

        # select the target language
        langs_list = GoogleTranslator().get_supported_languages()

        col1__, col2__ = st.columns(2)
        with col1__:
            lang = st.selectbox('Lang to translate into', options=langs_list, index=langs_list.index('english'))
            lang = GoogleTranslator().get_supported_languages(as_dict=True)[lang]

        with col2__:
            translation_backend = st.selectbox(
                'Translation backend',
                options=['Google Translate', 'OpenAI'],
                help='Google Translate is free. OpenAI provides higher-quality context-aware translations.',
            )

        # Word translation style — only for Google Translate
        translate_options = ['Word only', 'Use context']
        if translation_backend == 'Google Translate':
            translate_option = st.selectbox(
                'Word translation style',
                options=translate_options,
                help='Translate the word by itself or use the whole phrase as a context',
            )
        else:
            translate_option = 'Use context'
            st.info('OpenAI always uses sentence context for word translation.')

        # OpenAI-specific controls
        openai_api_key = ''
        openai_model = 'gpt-4o-mini'
        add_furigana_col = False

        if translation_backend == 'OpenAI':
            # API key: check environment / secrets first
            env_key = os.environ.get('OPENAI_API_KEY', '')
            secrets_key = ''
            try:
                secrets_key = st.secrets.get('OPENAI_API_KEY', '')
            except Exception:
                pass

            if env_key:
                openai_api_key = env_key
                st.success('OpenAI API key found in environment variables.')
            elif secrets_key:
                openai_api_key = secrets_key
                st.success('OpenAI API key found in Streamlit secrets.')
            else:
                openai_api_key = st.text_input(
                    'OpenAI API key',
                    type='password',
                    help='Enter your OpenAI API key. It will not be stored.',
                )

            openai_model = st.selectbox(
                'OpenAI model',
                options=['gpt-4o-mini', 'gpt-4o', 'gpt-5.2'],
                help='gpt-4o-mini is cheapest, gpt-5.2 is highest quality.',
            )

            # Furigana option — only if Japanese data is present
            if 'ja' in st.session_state.data['Word language'].values:
                add_furigana_col = st.checkbox(
                    'Add furigana to Japanese sentences',
                    value=False,
                    help='Uses OpenAI to add reading annotations (furigana) to kanji in sentences.',
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

        st.write(f'{st.session_state.data.shape[0]} texts will be translated (using {translation_backend})')
        st.session_state.loaded_data = st.session_state.data
        st.dataframe(
            st.session_state.data.reset_index(drop=True).drop(
                [col for col in st.session_state.data.columns if 'with' in col or 'translated' in col], axis=1
            )
        )
    if st.session_state.data is None:
        st.session_state.data = st.session_state.loaded_data

    # Disable button if OpenAI selected but no API key
    translate_disabled = translation_backend == 'OpenAI' and not openai_api_key

    st.session_state.translate = st.button(
        'Translate',
        on_click=make_more_columns,
        args=(
            st.session_state.data,
            lang,
            to_translate,
            translate_option,
            translation_backend,
            openai_api_key,
            openai_model,
            add_furigana_col,
        ),
        disabled=translate_disabled,
    )

    if translate_disabled:
        st.warning('Please provide an OpenAI API key to translate.')

    if st.session_state.translate or st.session_state.load_state:
        time.sleep(1)

        st.session_state.load_state = True
        translated_data = st.session_state.translated_df
        st.success('Translation finished!', icon='✅')
        cols_to_hide = [col for col in translated_data.columns if 'with' in col and col != 'sentence_with_furigana']
        st.dataframe(translated_data.drop(cols_to_hide, axis=1))

else:
    st.write('You need to upload some data in order to translate it.')
