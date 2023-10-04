from st_pages import Page, show_pages, add_page_title
import streamlit as st

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

    If you would like more information, you can refer to this blogpost [not written yet]. Project link: https://github.com/Erlemar/KindleVocabToAnki
"""
st.markdown(text, unsafe_allow_html=True)
