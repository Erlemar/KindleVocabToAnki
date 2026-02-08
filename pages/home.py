import streamlit as st

st.title('Kindle Vocabulary to Anki converter')

text = """
This app converts Kindle vocabulary files into a table format that can be imported into Anki.

### How it works

1. **Upload** your `vocab.db` file (or use sample data)
2. **Translate** words with Google Translate or OpenAI
3. **Download** the result as a CSV ready for Anki import

### Getting your vocabulary file

- Connect your Kindle device to your PC/laptop using a cable
- Copy the file from `Kindle/system/vocabulary/vocab.db`

### Features

- **Multiple translation backends**: Free Google Translate or higher-quality OpenAI
- **Context-aware translation**: Uses the sentence context for more accurate translations
- **Furigana support**: Automatically adds reading annotations for Japanese kanji (OpenAI)
- **Flexible export**: Choose columns, rename them, add highlight/cloze formatting
- **Filtering**: Filter by date, book, author, or language before translating
- **Statistics**: View word count trends, activity heatmaps, and reading stats

### Privacy

This app does not store your data permanently. It is only saved in cache and will be cleared after your session ends.

Project link: https://github.com/Erlemar/KindleVocabToAnki
"""
st.markdown(text)
