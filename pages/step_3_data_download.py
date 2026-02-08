from datetime import datetime

import streamlit as st

st.subheader('Customize translated data')

if 'translated_df' in st.session_state and st.session_state.translated_df.shape[0] > 0:
    translated_data = st.session_state.translated_df
    options = st.multiselect(
        label='Columns to use',
        options=list(translated_data.columns),
        default=['Word', 'Stem', 'Sentence'] + [col for col in translated_data.columns if 'translated' in col],
        help='Select the columns you want to keep',
    )

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
            'Cloze deletion',
        ),
        index=0,
        help='separator',
    )
    if highlight == 'None':
        pass
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
            lambda x: x.Sentence.replace(x.Word, f'<b>{x.Word}</b>'), axis=1
        )
    elif highlight == 'Cloze deletion':
        new_data['sentence_with_highlight'] = new_data.apply(
            lambda x: x.Sentence.replace(x.Word, '{{c1::' + x.translated_word + '::' + x.Word + '}}'), axis=1
        )

    # Preview toggle
    preview_rows = st.slider(
        'Preview rows',
        min_value=5,
        max_value=new_data.shape[0],
        value=min(50, new_data.shape[0]),
        help='Number of rows to display in the preview',
    )
    st.dataframe(new_data.head(preview_rows))

    st.subheader('Download options')
    keep_header = st.checkbox('Keep header', value=False)
    sep = st.selectbox(label='Select separator', options=(';', 'Tab'), help='separator')
    sep = sep if sep == ';' else '\t'
    date = str(datetime.today().date()).replace('-', '_')

    file_name = st.text_input('File name (without extension)', f'anki_table_{date}')

    csv_data = new_data.to_csv(index=False, sep=sep, header=keep_header)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label='Press to Download',
            data=csv_data,
            file_name=f'{file_name}_{date}.csv',
            mime='text/csv',
            key='download-csv',
            help='Download as CSV file',
        )
    with col2:
        if new_data.shape[0] <= 200:
            tsv_data = new_data.to_csv(index=False, sep='\t', header=keep_header)
            st.code(tsv_data, language=None)
            st.caption('Copy the text above for quick Anki import')

else:
    st.write('You need to translate some data in order to download it.')
