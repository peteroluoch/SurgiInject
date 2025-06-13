"""
Test suite for batch injection and coordination
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from engine.batch_engine import batch_inject

class DummyFile:
    def __init__(self, path, content):
        self.path = Path(path)
        self.content = content
        self.written = None
    def write_text(self, data):
        self.written = data
    def read_text(self):
        return self.content
    def exists(self):
        return True
    def is_file(self):
        return True

@patch('engine.batch_engine.file_contains_marker')
@patch('engine.batch_engine.safe_write_file')
@patch('engine.batch_engine.inject_with_context')
def test_batch_injection_skips_injected_files(mock_inject, mock_write, mock_marker):
    mock_marker.side_effect = [True, False]
    mock_inject.return_value = 'new content'
    mock_write.return_value = True
    files = [Path('file1.py'), Path('file2.py')]
    with patch('builtins.open', new_callable=MagicMock):
        result = batch_inject(files, 'prompt.txt', with_context=True)
    statuses = [r['status'] for r in result['results']]
    assert 'skipped' in statuses
    assert 'injected' in statuses

@patch('engine.batch_engine.file_contains_marker', return_value=False)
@patch('engine.batch_engine.safe_write_file', return_value=True)
@patch('engine.batch_engine.inject_with_context')
def test_batch_injection_coordinated_changes(mock_inject, mock_write, mock_marker):
    mock_inject.side_effect = [
        'def helper():\n    pass\n',
        'def helper():\n    pass\ndef another():\n    pass\n'
    ]
    files = [Path('file1.py'), Path('file2.py')]
    with patch('builtins.open', new_callable=MagicMock):
        result = batch_inject(files, 'prompt.txt', with_context=True, coordinated=True)
    assert all(r['status'] == 'injected' for r in result['results'])
    # Should deduplicate 'helper' definition
    # (Check that only one file has 'def helper()' twice)
    injected_files = [r['file'] for r in result['results'] if r['status'] == 'injected']
    assert len(injected_files) == 2

@patch('engine.batch_engine.file_contains_marker', return_value=False)
@patch('engine.batch_engine.safe_write_file', return_value=True)
@patch('engine.batch_engine.inject_with_context', return_value='')
def test_batch_injection_handles_failures_gracefully(mock_inject, mock_write, mock_marker):
    files = [Path('file1.py'), Path('file2.py')]
    with patch('builtins.open', new_callable=MagicMock):
        result = batch_inject(files, 'prompt.txt', with_context=True)
    statuses = [r['status'] for r in result['results']]
    assert statuses.count('failed') == 2 