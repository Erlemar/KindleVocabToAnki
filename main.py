import streamlit as st

from src.utils import init_session_state

st.set_page_config(
    page_title='Kindle Vocabulary to Anki converter',
)

init_session_state()

pages = [
    st.Page('pages/home.py', title='General information', icon='🏠'),
    st.Page('pages/step_1_data_upload.py', title='Step 1: Upload the data', icon='👀'),
    st.Page('pages/step_2_data_translate.py', title='Step 2: Translate the data', icon='📖'),
    st.Page('pages/step_3_data_download.py', title='Step 3: Download the data', icon='⬇️'),
]

pg = st.navigation(pages)
pg.run()
