"""
Test suite for recursive injection functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from engine.recursive import inject_dir, file_contains_marker
from engine.file_utils import (
    file_contains_marker as file_utils_contains_marker,
    add_marker_to_content,
    is_meaningful_response,
    get_marker_for_file
)


class TestMarkerLogic:
    """Test marker detection and injection logic"""
    
    def test_get_marker_for_file_python(self):
        """Test marker selection for Python files"""
        file_path = Path("test.py")
        marker = get_marker_for_file(file_path)
        assert marker == "# Injected by SurgiInject"
    
    def test_get_marker_for_file_html(self):
        """Test marker selection for HTML files"""
        file_path = Path("test.html")
        marker = get_marker_for_file(file_path)
        assert marker == "<!-- Injected by SurgiInject -->"
    
    def test_get_marker_for_file_js(self):
        """Test marker selection for JavaScript files"""
        file_path = Path("test.js")
        marker = get_marker_for_file(file_path)
        assert marker == "// Injected by SurgiInject"
    
    def test_file_contains_marker_python(self):
        """Test marker detection in Python files"""
        content = "# Injected by SurgiInject\nprint('hello')"
        with patch('builtins.open', mock_open(read_data=content)):
            with patch('engine.file_utils.get_file_encoding', return_value='utf-8'):
                result = file_utils_contains_marker(Path("test.py"))
                assert result is True
    
    def test_file_contains_marker_html(self):
        """Test marker detection in HTML files"""
        content = "<!-- Injected by SurgiInject -->\n<html>"
        with patch('builtins.open', mock_open(read_data=content)):
            with patch('engine.file_utils.get_file_encoding', return_value='utf-8'):
                result = file_utils_contains_marker(Path("test.html"))
                assert result is True
    
    def test_file_does_not_contain_marker(self):
        """Test marker detection when marker is not present"""
        content = "print('hello')\nprint('world')"
        with patch('builtins.open', mock_open(read_data=content)):
            with patch('engine.file_utils.get_file_encoding', return_value='utf-8'):
                result = file_utils_contains_marker(Path("test.py"))
                assert result is False
    
    def test_add_marker_to_content_python(self):
        """Test adding marker to Python content"""
        content = "print('hello')"
        file_path = Path("test.py")
        result = add_marker_to_content(content, file_path)
        expected = "# Injected by SurgiInject\nprint('hello')"
        assert result == expected
    
    def test_add_marker_to_content_html(self):
        """Test adding marker to HTML content"""
        content = "<html><body>Hello</body></html>"
        file_path = Path("test.html")
        result = add_marker_to_content(content, file_path)
        expected = "<!-- Injected by SurgiInject -->\n<html><body>Hello</body></html>"
        assert result == expected
    
    def test_add_marker_to_content_already_has_marker(self):
        """Test adding marker when content already has marker"""
        content = "# Injected by SurgiInject\nprint('hello')"
        file_path = Path("test.py")
        result = add_marker_to_content(content, file_path)
        assert result == content  # Should not add duplicate marker


class TestMeaningfulResponse:
    """Test meaningful response detection"""
    
    def test_meaningful_response_valid(self):
        """Test that valid responses are considered meaningful"""
        valid_responses = [
            "print('hello world')",
            "def my_function():\n    return True",
            "<html><body>Content</body></html>"
        ]
        for response in valid_responses:
            assert is_meaningful_response(response) is True
    
    def test_meaningful_response_empty(self):
        """Test that empty responses are not meaningful"""
        empty_responses = [
            "",
            "   ",
            "\n\n",
            None
        ]
        for response in empty_responses:
            assert is_meaningful_response(response) is False
    
    def test_meaningful_response_error_indicators(self):
        """Test that responses with error indicators are not meaningful"""
        error_responses = [
            "Error: Something went wrong",
            "Failed: API call failed",
            "Exception: Invalid input",
            "[Injection failed: API error]"
        ]
        for response in error_responses:
            assert is_meaningful_response(response) is False


class TestInjectDir:
    """Test the main inject_dir function"""
    
    @patch('engine.recursive.run_injection_from_files')
    @patch('engine.recursive.file_contains_marker')
    @patch('engine.recursive.safe_write_file')
    def test_inject_skips_already_injected_files(self, mock_write, mock_contains_marker, mock_inject):
        """Test that already injected files are skipped"""
        # Setup
        mock_contains_marker.return_value = True
        mock_inject.return_value = "modified content"
        mock_write.return_value = True
        
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("print('hello')")
            
            # Run injection
            result = inject_dir(
                path=temp_dir,
                prompt_path="prompts/test.txt",
                extensions=[".py"],
                recursive=False
            )
            
            # Verify
            assert len(result["skipped"]) == 1
            assert len(result["injected"]) == 0
            assert len(result["failed"]) == 0
            assert str(test_file) in result["skipped"]
            mock_inject.assert_not_called()  # Should not call injection
    
    @patch('engine.recursive.run_injection_from_files')
    @patch('engine.recursive.file_contains_marker')
    @patch('engine.recursive.safe_write_file')
    def test_inject_handles_multiple_file_types(self, mock_write, mock_contains_marker, mock_inject):
        """Test injection with multiple file types"""
        # Setup
        mock_contains_marker.return_value = False
        mock_inject.return_value = "modified content"
        mock_write.return_value = True
        
        # Create temporary directory with multiple file types
        with tempfile.TemporaryDirectory() as temp_dir:
            files = {
                "test.py": "print('hello')",
                "test.html": "<html><body>Hello</body></html>",
                "test.js": "console.log('hello')",
                "test.txt": "plain text"
            }
            
            for filename, content in files.items():
                file_path = Path(temp_dir) / filename
                file_path.write_text(content)
            
            # Run injection
            result = inject_dir(
                path=temp_dir,
                prompt_path="prompts/test.txt",
                extensions=[".py", ".html", ".js"],
                recursive=False
            )
            
            # Verify
            assert len(result["injected"]) == 3  # .py, .html, .js
            assert len(result["skipped"]) == 0
            assert len(result["failed"]) == 0
            assert mock_inject.call_count == 3
    
    @patch('engine.recursive.run_injection_from_files')
    @patch('engine.recursive.file_contains_marker')
    @patch('engine.recursive.safe_write_file')
    def test_inject_fails_gracefully_on_invalid_files(self, mock_write, mock_contains_marker, mock_inject):
        """Test graceful handling of invalid files"""
        # Setup
        mock_contains_marker.return_value = False
        mock_inject.side_effect = Exception("Injection failed")
        mock_write.return_value = True
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("print('hello')")
            
            # Run injection
            result = inject_dir(
                path=temp_dir,
                prompt_path="prompts/test.txt",
                extensions=[".py"],
                recursive=False
            )
            
            # Verify
            assert len(result["failed"]) == 1
            assert len(result["injected"]) == 0
            assert len(result["skipped"]) == 0
            assert str(test_file) in result["failed"]
    
    @patch('engine.recursive.run_injection_from_files')
    @patch('engine.recursive.file_contains_marker')
    @patch('engine.recursive.safe_write_file')
    def test_inject_adds_marker_after_success(self, mock_write, mock_contains_marker, mock_inject):
        """Test that marker is added after successful injection"""
        # Setup
        mock_contains_marker.return_value = False
        mock_inject.return_value = "modified content"
        mock_write.return_value = True
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("print('hello')")
            
            # Run injection
            result = inject_dir(
                path=temp_dir,
                prompt_path="prompts/test.txt",
                extensions=[".py"],
                recursive=False
            )
            
            # Verify
            assert len(result["injected"]) == 1
            assert len(result["failed"]) == 0
            
            # Check that safe_write_file was called with marked content
            mock_write.assert_called_once()
            call_args = mock_write.call_args
            written_content = call_args[0][1]  # Second argument is content
            assert "# Injected by SurgiInject" in written_content
    
    @patch('engine.recursive.run_injection_from_files')
    @patch('engine.recursive.file_contains_marker')
    @patch('engine.recursive.safe_write_file')
    def test_inject_skips_empty_files(self, mock_write, mock_contains_marker, mock_inject):
        """Test that empty files are skipped"""
        # Setup
        mock_contains_marker.return_value = False
        mock_inject.return_value = "modified content"
        mock_write.return_value = True
        
        # Create temporary directory with empty file
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "empty.py"
            test_file.write_text("")  # Empty file
            
            # Run injection
            result = inject_dir(
                path=temp_dir,
                prompt_path="prompts/test.txt",
                extensions=[".py"],
                recursive=False
            )
            
            # Verify
            assert len(result["injected"]) == 0
            assert len(result["failed"]) == 0
            assert len(result["skipped"]) == 0
            mock_inject.assert_not_called()  # Should not call injection
    
    @patch('engine.recursive.run_injection_from_files')
    @patch('engine.recursive.file_contains_marker')
    @patch('engine.recursive.safe_write_file')
    def test_inject_handles_meaningless_responses(self, mock_write, mock_contains_marker, mock_inject):
        """Test handling of meaningless AI responses"""
        # Setup
        mock_contains_marker.return_value = False
        mock_inject.return_value = ""  # Empty response
        mock_write.return_value = True
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("print('hello')")
            
            # Run injection
            result = inject_dir(
                path=temp_dir,
                prompt_path="prompts/test.txt",
                extensions=[".py"],
                recursive=False
            )
            
            # Verify
            assert len(result["failed"]) == 1
            assert len(result["injected"]) == 0
            assert str(test_file) in result["failed"]
            mock_write.assert_not_called()  # Should not write meaningless content


class TestRecursiveBehavior:
    """Test recursive directory traversal"""
    
    @patch('engine.recursive.run_injection_from_files')
    @patch('engine.recursive.file_contains_marker')
    @patch('engine.recursive.safe_write_file')
    def test_recursive_traversal(self, mock_write, mock_contains_marker, mock_inject):
        """Test recursive directory traversal"""
        # Setup
        mock_contains_marker.return_value = False
        mock_inject.return_value = "modified content"
        mock_write.return_value = True
        
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create subdirectories and files
            subdir1 = Path(temp_dir) / "subdir1"
            subdir1.mkdir()
            subdir2 = Path(temp_dir) / "subdir2"
            subdir2.mkdir()
            
            files = {
                Path(temp_dir) / "root.py": "print('root')",
                subdir1 / "file1.py": "print('subdir1')",
                subdir2 / "file2.py": "print('subdir2')",
                subdir2 / "file3.html": "<html>Content</html>"
            }
            
            for file_path, content in files.items():
                file_path.write_text(content)
            
            # Run injection with recursive=True
            result = inject_dir(
                path=temp_dir,
                prompt_path="prompts/test.txt",
                extensions=[".py", ".html"],
                recursive=True
            )
            
            # Verify all files were processed
            assert len(result["injected"]) == 4
            assert mock_inject.call_count == 4
    
    @patch('engine.recursive.run_injection_from_files')
    @patch('engine.recursive.file_contains_marker')
    @patch('engine.recursive.safe_write_file')
    def test_non_recursive_traversal(self, mock_write, mock_contains_marker, mock_inject):
        """Test non-recursive directory traversal"""
        # Setup
        mock_contains_marker.return_value = False
        mock_inject.return_value = "modified content"
        mock_write.return_value = True
        
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create subdirectories and files
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            
            files = {
                Path(temp_dir) / "root.py": "print('root')",
                subdir / "subfile.py": "print('subdir')"
            }
            
            for file_path, content in files.items():
                file_path.write_text(content)
            
            # Run injection with recursive=False
            result = inject_dir(
                path=temp_dir,
                prompt_path="prompts/test.txt",
                extensions=[".py"],
                recursive=False
            )
            
            # Verify only root file was processed
            assert len(result["injected"]) == 1
            assert mock_inject.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__]) 