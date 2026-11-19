from backend.ingestion.text_cleaner import clean_text

def test_clean_text_trims_and_normalizes_whitespace():
    assert clean_text("  Hello   world  ") == "Hello world"
