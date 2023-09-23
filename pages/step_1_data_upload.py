import pandas as pd
import streamlit as st

from src.utils import get_data_from_vocab, show_vocabulary_stats

if 'load_state' not in st.session_state:
    st.session_state.load_state = False
if 'translated_df' not in st.session_state:
    st.session_state.translated_df = pd.DataFrame()
if 'loaded_data' not in st.session_state:
    st.session_state.loaded_data = pd.DataFrame()
if 'data_type' not in st.session_state:
    st.session_state.data_type = None
use_sample = None

if 'data_exists' not in st.session_state:
    st.session_state.data_exists = False

st.subheader('Upload your kindle vocabulary file here')
if st.session_state.loaded_data.shape[0] > 0:
    st.write('Data is already uploaded. You can reupload the data, if you want')


def get_vocab_data():
    st.session_state.data_type = 'db'
    if st.session_state.db:
        st.session_state.use_sample = None
        st.session_state.data_exists = False
        data = get_data_from_vocab(st.session_state.db)
        st.session_state.loaded_data = data


st.session_state.db = st.file_uploader(
    'vocab.db', type='db', help='Upload the vocabulary file here', on_change=get_vocab_data
)

if st.session_state.db and st.session_state.data_type == 'db':
    st.session_state.use_sample = None
    st.session_state.data_exists = False
    data = get_data_from_vocab(st.session_state.db)
    st.session_state.loaded_data = data


def get_sample_data():
    st.session_state.data_type = 'sample'
    data = pd.read_csv('data_example/example_data.csv')
    st.session_state.data_exists = True
    st.session_state.loaded_data = data
    st.session_state.use_sample = True


st.session_state.use_sample = st.button('Press the button to use a sample data', on_click=get_sample_data)
if not st.session_state.db and not use_sample:
    st.cache_data.clear()

if (
    st.session_state.db
    or st.session_state.use_sample
    or st.session_state.data_exists
    or st.session_state.loaded_data.shape[0] > 0
):
    # use sample data or the uploaded data
    if not st.session_state.loaded_data.shape[0] > 0:
        if not st.session_state.use_sample and not st.session_state.data_exists:
            data = get_data_from_vocab(st.session_state.db)
            st.session_state.loaded_data = data
        elif not st.session_state.use_sample:
            data = st.session_state.loaded_data
    else:
        if st.session_state.data_type == 'db':
            data = st.session_state.loaded_data
        elif st.session_state.data_type == 'sample':
            data = st.session_state.loaded_data
    st.session_state.extracted = True
    st.subheader('Extracted data')
    text3 = """
        This is the data extracted from the Kindle vocabulary file. You can sort it by clicking on any column name.
    """
    st.markdown(text3, unsafe_allow_html=True)
    st.dataframe(data)

    my_expander1 = st.expander(label='Show vocabulary statistics')
    with my_expander1:
        show_vocabulary_stats(data)
