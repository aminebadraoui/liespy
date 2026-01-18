import pytest
import json
from services.ai_pipeline import extract_json

def test_clean_json():
    text = '{"key": "value"}'
    assert extract_json(text) == {"key": "value"}

def test_markdown_json():
    text = '```json\n{"key": "value"}\n```'
    assert extract_json(text) == {"key": "value"}

def test_markdown_no_lang():
    text = '```\n{"key": "value"}\n```'
    assert extract_json(text) == {"key": "value"}

def test_preamble_postamble():
    text = 'Here is the JSON:\n{"key": "value"}\nThanks!'
    assert extract_json(text) == {"key": "value"}

def test_nested_brackets():
    text = 'Some text {"outer": {"inner": "value"}} more text'
    assert extract_json(text) == {"outer": {"inner": "value"}}

def test_list_root():
    text = '[{"item": 1}, {"item": 2}]'
    assert extract_json(text) == [{"item": 1}, {"item": 2}]

def test_invalid_json():
    text = 'This is valid text but invalid json: {key: value}'
    with pytest.raises(ValueError):
        extract_json(text)

def test_no_json_at_all():
    text = 'Just some random text.'
    with pytest.raises(ValueError):
        extract_json(text)
