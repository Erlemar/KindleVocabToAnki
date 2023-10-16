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
    # TODO: add cloze deletion
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
            lambda x: x.Sentence.replace(x.Word, f'<b>{x.Word}</b>'), axis=1
        )
    elif highlight == 'Cloze deletion':
        new_data['sentence_with_highlight'] = new_data.apply(
            lambda x: x.Sentence.replace(x.Word, '{{c1::' + x.translated_word + '::' + x.Word + '}}'), axis=1
        )
    st.dataframe(new_data)

    st.subheader('Download options')
    keep_header = st.checkbox('Keep header', value=False)
    sep = st.selectbox(label='Select separator', options=(';', 'Tab'), help='separator')
    sep = sep if sep == ';' else '\t'

    file_name = st.text_input('File name (without extension)', 'anki_table')
    st.download_button(
        label='Press to Download',
        data=new_data.to_csv(index=False, sep=';', header=keep_header),
        # TODO add date to the file name
        file_name=f'{file_name}.csv',
        mime='text/csv',
        key='download-csv',
        help='press m!',
    )

else:
    st.write('You need to translate some data in order to download it.')
