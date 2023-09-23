import streamlit as st

st.set_page_config(
    page_title='Kindle Vocabulary to Anki converter',
    # page_icon='👋',
)
st.title('Kindle Vocabulary to Anki converter')

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
    Project link: https://github.com/Erlemar/KindleVocabToAnki
"""
st.markdown(text, unsafe_allow_html=True)
