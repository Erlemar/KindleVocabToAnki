import time

import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator

from src.utils import get_data_from_vocab, make_more_columns, show_vocabulary_stats

st.set_page_config(page_title='Kindle Vocabulary to Anki converter')

st.title('Kindle Vocabulary to Anki converter')
if 'load_state' not in st.session_state:
    st.session_state.load_state = False
if 'translated_df' not in st.session_state:
    st.session_state.translated_df = pd.DataFrame()
if 'loaded_data' not in st.session_state:
    st.session_state.loaded_data = pd.DataFrame()
use_sample = None
holder1 = st.empty()
holder2 = st.empty()
holder3 = st.empty()
holder4 = st.empty()
holder5 = st.empty()
holder6 = st.empty()
holder7 = st.empty()
holder8 = st.empty()
holder9 = st.empty()
holder10 = st.empty()
holder11 = st.empty()
holder12 = st.empty()
holder13 = st.empty()

text = """
    This is an app for converting kindle vocab file into a table that can be imported into anki.\n
    You can change the app width or turn on the dark mode in the Settings using the button in the top right corner.\n
    To get started, you need to have `vocab.db` file from your Kindle device at hand. If you don't know how to get it,
    here are the steps to do it:
    * connect your Kindle device to your PC/laptop by cable;
    * copy vocabulary file `Kindle/system/vocabulary/vocab.db` to your PC/laptop;
    \n
    This app doesn't keep your data - it is saved only in cache and is cleared after the end of your session.\n
    If you want to know more, you can read this blogpost [not written yet].
"""
holder1.markdown(text, unsafe_allow_html=True)

holder3.subheader('Upload your kindle vocabulary file here')
if 'data_exists' not in st.session_state:
    st.session_state.data_exists = False
db = holder4.file_uploader('vocab.db', type='db', help='Upload the vocabulary file here')

use_sample = holder5.button('Press the button to use a sample data')

data = pd.DataFrame

if use_sample:
    data = pd.read_csv('data_example/example_data.csv')
    st.session_state.data_exists = True
    st.session_state.loaded_data = data

if db or use_sample or st.session_state.data_exists:
    time.sleep(1)
    # use sample data or the uploaded data
    if not use_sample and not st.session_state.data_exists:
        data = get_data_from_vocab(db)
        st.session_state.loaded_data = data
    elif not use_sample:
        data = st.session_state.loaded_data

    st.session_state.extracted = True
    holder1.empty()
    holder2.empty()
    holder3.empty()
    holder4.empty()
    holder5.empty()
    holder6.subheader('Extracted data')
    text3 = """
        This is the data extracted from the Kindle vocabulary file. You can sort it by clicking on any column name.
    """
    holder7.markdown(text3, unsafe_allow_html=True)
    holder8.dataframe(data)

    my_expander1 = holder9.expander(label='Show vocabulary statistics')
    with my_expander1:
        show_vocabulary_stats(data)

    holder10.subheader('Define translation parameters')
    my_expander2 = holder11.expander(label='Translation parameters', expanded=True)
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
    translate = holder13.button('Translate', on_click=make_more_columns, args=(data, lang, to_translate))

    if translate or st.session_state.load_state:
        # time.sleep(1)

        holder6.empty()
        holder7.empty()
        holder8.empty()
        holder9.empty()
        holder10.empty()
        holder11.empty()
        holder12.empty()
        holder13.empty()
        st.session_state.load_state = True

        translated_data = st.session_state.translated_df
        st.success('Translation finished!', icon='✅')
        st.dataframe(translated_data)
        st.subheader('Customize translated data')
        options = st.multiselect(
            label='Columns to use',
            options=list(translated_data.columns),
            default=['Stem', 'Word', 'Sentence'] + [col for col in translated_data.columns if 'translated' in col],
            help='Select the columns you want to keep',
        )
        # TODO process the case when the original sentence isn't selected

        my_expander1 = st.expander(label='Rename columns')
        with my_expander1:
            # possibility to rename the columns
            new_col_names = {}
            for col in options:
                new_name = st.text_input(f'{col} name', f'{col}', help=f'Write a new {col} name')
                new_col_names[col] = new_name
        # downloading
        new_data = translated_data[options].rename(columns=new_col_names)
        highlight = st.selectbox(
            label='Select highlight options',
            options=(
                'None',
                'Replace with underscore',
                'Surround with [] brackets',
                'Surround with {} brackets',
                'Bold',
            ),
            index=0,
            help='separator',
        )
        if highlight is None:
            new_data['sentence_with_highlight'] = new_data['Sentence']
        elif highlight == 'Replace with underscore':
            new_data['sentence_with_highlight'] = new_data.apply(lambda x: x.Sentence.replace(x.Word, '_'), axis=1)
        elif highlight == 'Surround with [] brackets':
            new_data['sentence_with_highlight'] = new_data.apply(
                lambda x: x.Sentence.replace(x.Word, f'[{x.Word}]'), axis=1
            )
        elif highlight == 'Surround with {} brackets':
            new_data['sentence_with_highlight'] = new_data.apply(
                lambda x: x.Sentence.replace(x.Word, f'{{{x.Word}}}'), axis=1
            )
        elif highlight == 'Bold':
            new_data['sentence_with_highlight'] = new_data.apply(
                lambda x: x.Sentence.replace(x.Word, f'<b>{x.Word}</b>'),
                axis=1
                # lambda x: x.Sentence.replace(x.Word, f'\033[1m{x.Word}\033[1m'), axis=1
            )
        st.dataframe(new_data)

        st.subheader('Download options')
        keep_header = st.checkbox('Keep header', value=False)
        sep = st.selectbox(label='Select separator', options=(';', 'Tab'), help='separator')
        sep = sep if sep == ';' else '\t'

        file_name = st.text_input('File name (without extension)', 'anki_table')
        # TODO check file name, maybe it doesn't work. IT WORKS, but need to confirm the choice
        # TODO check that remove header works

        st.download_button(
            label='Press to Download',
            data=new_data.to_csv(index=False, sep=';', header=keep_header),
            file_name=f'{file_name}.csv',
            mime='text/csv',
            key='download-csv',
            help='press m!',
        )
