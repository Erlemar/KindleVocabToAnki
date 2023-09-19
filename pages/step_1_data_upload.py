import pandas as pd
import streamlit as st

from src.utils import get_data_from_vocab, show_vocabulary_stats

st.title('Kindle Vocabulary to Anki converter')

if 'load_state' not in st.session_state:
    st.session_state.load_state = False
if 'translated_df' not in st.session_state:
    st.session_state.translated_df = pd.DataFrame()
if 'loaded_data' not in st.session_state:
    st.session_state.loaded_data = pd.DataFrame()
use_sample = None

if 'data_exists' not in st.session_state:
    st.session_state.data_exists = False

st.subheader('Upload your kindle vocabulary file here')
if st.session_state.loaded_data.shape[0] > 0:
    st.write('Data is already uploaded. You can reupload the data, if you want')
st.session_state.db = st.file_uploader('vocab.db', type='db', help='Upload the vocabulary file here')

st.session_state.use_sample = st.button('Press the button to use a sample data')
if not st.session_state.db and not use_sample:
    st.cache_data.clear()

st.write(f'{st.session_state.data_exists=}')


if st.session_state.use_sample:
    data = pd.read_csv('data_example/example_data.csv')
    if not st.session_state.loaded_data.shape[0] > 0:
        st.session_state.data_exists = True
        st.session_state.loaded_data = data

if (
    st.session_state.db
    or st.session_state.use_sample
    or st.session_state.data_exists
    or st.session_state.loaded_data.shape[0] > 0
):
    # time.sleep(1)
    # use sample data or the uploaded data
    if not st.session_state.loaded_data.shape[0] > 0:
        if not st.session_state.use_sample and not st.session_state.data_exists:
            data = get_data_from_vocab(st.session_state.db)
            st.session_state.loaded_data = data
        elif not st.session_state.use_sample:
            data = st.session_state.loaded_data
    else:
        data = st.session_state.loaded_data
    # st.write(f'2{use_sample=}')
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
