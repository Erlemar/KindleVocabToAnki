import streamlit as st
from st_pages import Page, show_pages, add_page_title

st.set_page_config(
    page_title='Kindle Vocabulary to Anki converter',
    # page_icon='👋',
)

st.title('Kindle Vocabulary to Anki converter')

text = """
    This is an app that converts Kindle vocabulary files into a table format that can be imported into Anki.

    You can adjust the app width or enable dark mode in the Settings using the button located in the top right corner.

    To get started, you will need to have the `vocab.db` file from your Kindle device. If you're unsure how to obtain it, follow these steps:

    - Connect your Kindle device to your PC/laptop using a cable.
    - Copy the vocabulary file `Kindle/system/vocabulary/vocab.db` to your PC/laptop.

    Please note that this app does not store your data permanently. It is only saved in cache and will be cleared after your session ends.

    Project link: https://github.com/Erlemar/KindleVocabToAnki
"""
st.markdown(text, unsafe_allow_html=True)

show_pages(
    [
        Page('pages/home.py', 'General information', '🏠'),
        Page('pages/step_1_data_upload.py', 'Upload the data', ':eyes:'),
        Page('pages/step_2_data_translate.py', 'Translate the data', ':book:'),
        Page('pages/step_3_data_download.py', 'Download the data', '⬇️'),
    ]
)
