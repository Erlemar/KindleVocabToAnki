import datetime
import sqlite3
import tempfile
from unittest.mock import patch

import pandas as pd


def _create_test_db() -> bytes:
    """Create a minimal vocab.db in memory and return its bytes."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as fp:
        path = fp.name

    con = sqlite3.connect(path)
    cur = con.cursor()

    cur.execute("""CREATE TABLE WORDS (id TEXT, word TEXT, stem TEXT, lang TEXT)""")
    cur.execute("""CREATE TABLE BOOK_INFO (id TEXT, title TEXT, authors TEXT)""")
    cur.execute("""CREATE TABLE LOOKUPS (word_key TEXT, book_key TEXT, usage TEXT, timestamp INTEGER)""")

    # Insert test data
    ts1 = int(datetime.datetime(2023, 1, 15, 10, 0, 0).timestamp() * 1000)
    ts2 = int(datetime.datetime(2023, 2, 20, 14, 30, 0).timestamp() * 1000)

    cur.execute("INSERT INTO WORDS VALUES ('w1', 'hola', 'hola', 'es')")
    cur.execute("INSERT INTO WORDS VALUES ('w2', 'mundo', 'mundo', 'es')")
    cur.execute("INSERT INTO BOOK_INFO VALUES ('b1', 'Test Book', 'Test Author')")
    cur.execute(f"INSERT INTO LOOKUPS VALUES ('w1', 'b1', 'Hola amigo', {ts1})")
    cur.execute(f"INSERT INTO LOOKUPS VALUES ('w2', 'b1', 'El mundo es grande', {ts2})")

    con.commit()
    con.close()

    with open(path, 'rb') as f:
        db_bytes = f.read()

    import os

    os.unlink(path)

    return db_bytes


class FakeUploadedFile:
    """Mimics st.runtime.uploaded_file_manager.UploadedFile."""

    def __init__(self, data: bytes):
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


@patch('src.utils.st')
def test_get_data_from_vocab():
    """Test that get_data_from_vocab parses a SQLite DB correctly."""
    from src.utils import get_data_from_vocab

    db_bytes = _create_test_db()
    fake_file = FakeUploadedFile(db_bytes)

    result = get_data_from_vocab(fake_file)

    assert isinstance(result, pd.DataFrame)
    assert result.shape[0] == 2
    expected_cols = {'Word', 'Stem', 'Word language', 'Sentence', 'Book title', 'Authors', 'Timestamp'}
    assert expected_cols.issubset(set(result.columns))
    assert 'hola' in result['Word'].values
    assert 'mundo' in result['Word'].values
    assert result['Book title'].iloc[0] == 'Test Book'


@patch('src.utils.st')
def test_get_data_from_vocab_invalid_file(mock_st):
    """Test that invalid DB file returns empty DataFrame and shows error."""
    from src.utils import get_data_from_vocab

    fake_file = FakeUploadedFile(b'not a database')
    result = get_data_from_vocab(fake_file)

    assert isinstance(result, pd.DataFrame)
    assert result.shape[0] == 0
    mock_st.error.assert_called_once()


@patch('src.utils.st')
def test_get_data_from_vocab_sorted_by_timestamp():
    """Test that results are sorted by Timestamp."""
    from src.utils import get_data_from_vocab

    db_bytes = _create_test_db()
    fake_file = FakeUploadedFile(db_bytes)

    result = get_data_from_vocab(fake_file)
    timestamps = pd.to_datetime(result['Timestamp'])
    assert timestamps.is_monotonic_increasing


def _make_test_df():
    """Create a test DataFrame similar to what get_data_from_vocab returns."""
    return pd.DataFrame(
        {
            'Word': ['hola', 'mundo'],
            'Stem': ['hola', 'mundo'],
            'Word language': ['es', 'es'],
            'Sentence': ['Hola amigo', 'El mundo es grande'],
            'Book title': ['Test Book', 'Test Book'],
            'Authors': ['Test Author', 'Test Author'],
            'Timestamp': ['2023-01-15 10:00:00', '2023-02-20 14:30:00'],
        }
    )


@patch('src.utils.stqdm', side_effect=lambda x, **kwargs: x)
@patch('src.utils.st')
def test_make_more_columns_google_translate():
    """Test make_more_columns with Google Translate (mocked)."""
    from src.utils import make_more_columns

    df = _make_test_df()

    with (
        patch('src.utils.translate', return_value=['hello', 'world']) as mock_translate,
        patch('src.utils.translate_with_context', return_value=['hello', 'world']) as mock_ctx,
    ):

        # Clear any cache
        make_more_columns.clear()

        result = make_more_columns(
            data=df,
            lang='en',
            to_translate=['Word'],
            translate_option='Word only',
            translation_backend='Google Translate',
        )

        assert 'translated_word' in result.columns
        assert 'sentence_with_highlight' in result.columns
        assert 'sentence_with_cloze' in result.columns


@patch('src.utils.stqdm', side_effect=lambda x, **kwargs: x)
@patch('src.utils.st')
def test_make_more_columns_with_context():
    """Test make_more_columns with context translation."""
    from src.utils import make_more_columns

    df = _make_test_df()

    with (
        patch('src.utils.translate_with_context', return_value=['hello', 'world']),
        patch('src.utils.translate', return_value=['hello', 'world']),
    ):

        make_more_columns.clear()

        result = make_more_columns(
            data=df,
            lang='en',
            to_translate=['Word'],
            translate_option='Use context',
            translation_backend='Google Translate',
        )

        assert 'translated_word' in result.columns
        assert result.shape[0] == 2


@patch('src.utils.st')
def test_init_session_state(mock_st):
    """Test that init_session_state sets expected defaults."""
    from src.utils import init_session_state

    mock_st.session_state = {}
    init_session_state()

    assert 'load_state' in mock_st.session_state
    assert mock_st.session_state['load_state'] is False
    assert 'translated_df' in mock_st.session_state
    assert 'loaded_data' in mock_st.session_state


@patch('src.utils.st')
def test_estimate_openai_cost():
    """Test cost estimation function."""
    from src.utils import estimate_openai_cost

    cost = estimate_openai_cost(100, 'gpt-4o-mini')
    assert cost.startswith('~$')
    # Should be very cheap for gpt-4o-mini
    cost_val = float(cost.replace('~$', ''))
    assert cost_val < 1.0

    cost2 = estimate_openai_cost(100, 'gpt-4o')
    cost_val2 = float(cost2.replace('~$', ''))
    # gpt-4o should be more expensive
    assert cost_val2 > cost_val
