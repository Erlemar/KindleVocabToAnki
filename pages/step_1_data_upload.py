import pandas as pd
import streamlit as st

from src.utils import get_data_from_vocab, show_vocabulary_stats

st.subheader('Upload your kindle vocabulary file here')
if st.session_state.loaded_data.shape[0] > 0:
    st.write('The data is already uploaded. You can upload a new file, if necessary.')


def get_vocab_data():
    st.session_state.data_type = 'db'
    if st.session_state.db:
        st.session_state.use_sample = None
        st.session_state.data_exists = False
        with st.spinner('Parsing vocabulary database...'):
            data = get_data_from_vocab(st.session_state.db)
        if data.shape[0] == 0:
            st.session_state.loaded_data = pd.DataFrame()
            return
        expected_cols = {'Word', 'Stem', 'Word language', 'Sentence', 'Book title', 'Authors', 'Timestamp'}
        if not expected_cols.issubset(set(data.columns)):
            st.error(f'Invalid database format. Expected columns: {expected_cols}')
            st.session_state.loaded_data = pd.DataFrame()
            return
        st.session_state.loaded_data = data


st.session_state.db = st.file_uploader(
    'vocab.db', type='db', help='Upload the vocabulary file here', on_change=get_vocab_data
)


def get_sample_data():
    st.session_state.data_type = 'sample'
    data = pd.read_csv('data_example/example_data.csv')
    st.session_state.data_exists = True
    st.session_state.loaded_data = data
    st.session_state.use_sample = True


st.session_state.use_sample = st.button('Press the button to use a sample data', on_click=get_sample_data)
if not st.session_state.db and not st.session_state.get('use_sample'):
    st.cache_data.clear()


def reset_data():
    st.session_state.loaded_data = pd.DataFrame()
    st.session_state.translated_df = pd.DataFrame()
    st.session_state.load_state = False
    st.session_state.data_exists = False
    st.session_state.data_type = None
    st.cache_data.clear()


if st.session_state.loaded_data.shape[0] > 0:
    st.button('Reset data', on_click=reset_data, type='secondary')

if (
    st.session_state.db
    or st.session_state.use_sample
    or st.session_state.data_exists
    or st.session_state.loaded_data.shape[0] > 0
):
    if st.session_state.loaded_data.shape[0] > 0:
        data = st.session_state.loaded_data
    elif not st.session_state.use_sample and not st.session_state.data_exists:
        with st.spinner('Parsing vocabulary database...'):
            data = get_data_from_vocab(st.session_state.db)
        st.session_state.loaded_data = data
    else:
        data = st.session_state.loaded_data

    if data.shape[0] > 0:
        st.session_state.extracted = True
        st.subheader('Extracted data')
        st.markdown(
            'This is the data extracted from the Kindle vocabulary file. You can sort it by clicking on any column name.'
        )
        cols_to_show = ['Word', 'Stem', 'Word language', 'Sentence', 'Book title', 'Authors', 'Timestamp']
        st.dataframe(data[cols_to_show])

        my_expander1 = st.expander(label='Show vocabulary statistics')
        with my_expander1:
            show_vocabulary_stats(data)
