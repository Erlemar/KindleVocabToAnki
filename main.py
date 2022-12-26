import streamlit as st

from src.utils import get_data_from_vocab, make_more_columns

st.set_page_config(layout='wide')

st.title('Kindle Vocabulary to Anki converter')

db = st.file_uploader('vocab.db', type='db')
if db:
    # get data
    data = get_data_from_vocab(db)

    st.dataframe(data)
    st.subheader('Processed data')

    # limit the number of rows
    top_n = st.number_input('Take top N rows', min_value=1, max_value=data.shape[0], value=10)
    data = data[:top_n]
    # translate and create sentences
    data = make_more_columns(data)

    options = st.multiselect('Columns to use', list(data.columns), list(data.columns))

    # possibility to rename the columns
    new_col_names = {}
    for col in options:
        new_name = st.text_input(f'{col} name', f'{col}')
        new_col_names[col] = new_name

    # downloading
    new_data = data[options].rename(columns=new_col_names)
    st.dataframe(new_data)
    st.subheader('Download options')
    sep = st.selectbox('Select separator', (';', 'Tab'))
    sep = sep if sep == ';' else '\t'

    file_name = st.text_input('File name', 'anki_table')
    st.download_button(
        'Press to Download', new_data.to_csv(index=False, sep=';'), f'{file_name}.csv', 'text/csv', key='download-csv'
    )
