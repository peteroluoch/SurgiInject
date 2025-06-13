"""
Tests for diff preview functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from engine.diff_engine import (
    preview_injection,
    generate_unified_diff,
    apply_injection,
    batch_preview_injection,
    get_diff_stats,
    format_diff_for_display
)


class TestDiffPreview:
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.py"
        self.prompt_file = Path(self.temp_dir) / "prompt.txt"
        
        # Create test files
        with open(self.test_file, 'w') as f:
            f.write("def hello():\n    print('Hello, World!')\n")
        
        with open(self.prompt_file, 'w') as f:
            f.write("Add error handling to this function")
    
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_preview_injection_success(self):
        """Test successful injection preview"""
        with patch('engine.diff_engine.inject_with_context') as mock_inject:
            mock_inject.return_value = "def hello():\n    try:\n        print('Hello, World!')\n    except Exception as e:\n        print(f'Error: {e}')\n"
            
            result = preview_injection(
                file_path=str(self.test_file),
                prompt_path=str(self.prompt_file),
                with_context=True
            )
            
            assert result["filename"] == "test.py"
            assert result["filepath"] == str(self.test_file)
            assert result["has_changes"] is True
            assert result["with_context"] is True
            assert "diff" in result
            assert "before" in result
            assert "after" in result
    
    def test_preview_injection_no_changes(self):
        """Test preview when no changes are made"""
        with patch('engine.diff_engine.inject_with_context') as mock_inject:
            # Return same content as original
            with open(self.test_file, 'r') as f:
                original_content = f.read()
            mock_inject.return_value = original_content
            
            result = preview_injection(
                file_path=str(self.test_file),
                prompt_path=str(self.prompt_file),
                with_context=True
            )
            
            assert result["has_changes"] is False
            assert result["before"] == result["after"]
    
    def test_preview_injection_file_not_found(self):
        """Test preview with non-existent file"""
        result = preview_injection(
            file_path="nonexistent.py",
            prompt_path=str(self.prompt_file),
            with_context=True
        )
        
        assert "error" in result
        assert "Could not read file" in result["error"]
    
    def test_preview_injection_prompt_not_found(self):
        """Test preview with non-existent prompt"""
        result = preview_injection(
            file_path=str(self.test_file),
            prompt_path="nonexistent.txt",
            with_context=True
        )
        
        assert "error" in result
        assert "Prompt read error" in result["error"]
    
    def test_preview_injection_injection_failure(self):
        """Test preview when injection fails"""
        with patch('engine.diff_engine.inject_with_context') as mock_inject:
            mock_inject.side_effect = Exception("Injection failed")
            
            result = preview_injection(
                file_path=str(self.test_file),
                prompt_path=str(self.prompt_file),
                with_context=True
            )
            
            assert "error" in result
            assert "Injection failed" in result["error"]
    
    def test_generate_unified_diff(self):
        """Test unified diff generation"""
        before = "line1\nline2\nline3\n"
        after = "line1\nmodified line2\nline3\n"
        
        diff = generate_unified_diff(before, after, "test.py")
        
        assert "--- a/test.py" in diff
        assert "+++ b/test.py" in diff
        assert "-line2" in diff
        assert "+modified line2" in diff
    
    def test_generate_unified_diff_no_changes(self):
        """Test diff generation with no changes"""
        content = "line1\nline2\nline3\n"
        diff = generate_unified_diff(content, content, "test.py")
        
        # Should be empty or minimal
        assert len(diff.split('\n')) <= 3  # Just headers
    
    def test_apply_injection_success(self):
        """Test successful injection application"""
        backup_file = self.test_file.with_suffix('.py.backup')
        
        result = apply_injection(
            file_path=str(self.test_file),
            injected_content="def hello():\n    print('Modified!')\n"
        )
        
        assert result["success"] is True
        assert result["filename"] == "test.py"
        assert result["backup_created"] is True
        assert backup_file.exists()
        
        # Check that file was modified
        with open(self.test_file, 'r') as f:
            content = f.read()
        assert "Modified!" in content
    
    def test_apply_injection_backup_creation(self):
        """Test backup creation during application"""
        backup_file = self.test_file.with_suffix('.py.backup')
        
        # Read original content
        with open(self.test_file, 'r') as f:
            original_content = f.read()
        
        apply_injection(
            file_path=str(self.test_file),
            injected_content="new content"
        )
        
        # Check backup contains original content
        assert backup_file.exists()
        with open(backup_file, 'r') as f:
            backup_content = f.read()
        assert backup_content == original_content
    
    def test_apply_injection_failure(self):
        """Test injection application failure"""
        # Try to write to a read-only directory
        read_only_file = Path("/nonexistent/directory/test.py")
        
        result = apply_injection(
            file_path=str(read_only_file),
            injected_content="content"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_batch_preview_injection(self):
        """Test batch preview functionality"""
        # Create additional test files
        test_file2 = Path(self.temp_dir) / "test2.py"
        with open(test_file2, 'w') as f:
            f.write("def world():\n    pass\n")
        
        with patch('engine.diff_engine.preview_injection') as mock_preview:
            mock_preview.side_effect = [
                {"filename": "test.py", "has_changes": True, "diff": "diff1"},
                {"filename": "test2.py", "has_changes": False, "diff": ""}
            ]
            
            result = batch_preview_injection(
                files=[str(self.test_file), str(test_file2)],
                prompt_path=str(self.prompt_file),
                with_context=True
            )
            
            assert result["total_files"] == 2
            assert result["files_with_changes"] == 1
            assert result["with_context"] is True
            assert len(result["previews"]) == 2
    
    def test_get_diff_stats(self):
        """Test diff statistics calculation"""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def hello():
-    print('old')
+    print('new')
+    print('extra')
"""
        
        stats = get_diff_stats(diff)
        
        assert stats["additions"] == 2
        assert stats["deletions"] == 1
        assert stats["total_changes"] == 3
    
    def test_get_diff_stats_empty(self):
        """Test stats calculation with empty diff"""
        stats = get_diff_stats("")
        assert stats["additions"] == 0
        assert stats["deletions"] == 0
        assert stats["total_changes"] == 0
    
    def test_format_diff_for_display(self):
        """Test diff formatting for display"""
        diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def hello():
-    print('old')
+    print('new')
+    print('extra')
"""
        
        formatted = format_diff_for_display(diff)
        
        assert "<span class='addition'>+    print('new')</span>" in formatted
        assert "<span class='deletion'>-    print('old')</span>" in formatted
        assert "<span class='hunk'>@@ -1,3 +1,4 @@" in formatted
    
    def test_preview_injection_without_context(self):
        """Test preview without context awareness"""
        with patch('engine.diff_engine.run_injection') as mock_inject:
            mock_inject.return_value = "def hello():\n    print('Modified!')\n"
            
            result = preview_injection(
                file_path=str(self.test_file),
                prompt_path=str(self.prompt_file),
                with_context=False
            )
            
            assert result["with_context"] is False
            assert result["has_changes"] is True
    
    def test_preview_injection_with_project_root(self):
        """Test preview with custom project root"""
        project_root = Path(self.temp_dir) / "subdir"
        project_root.mkdir()
        
        with patch('engine.diff_engine.inject_with_context') as mock_inject:
            mock_inject.return_value = "modified content"
            
            result = preview_injection(
                file_path=str(self.test_file),
                prompt_path=str(self.prompt_file),
                with_context=True,
                project_root=str(project_root)
            )
            
            assert result["has_changes"] is True
            # Verify project root was passed to inject_with_context
            mock_inject.assert_called_once()
            call_args = mock_inject.call_args[1]
            assert call_args["project_root"] == project_root


class TestDiffPreviewIntegration:
    """Integration tests for diff preview functionality"""
    
    def test_end_to_end_preview_and_apply(self):
        """Test complete preview and apply workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            prompt_file = Path(temp_dir) / "prompt.txt"
            
            # Create test files
            with open(test_file, 'w') as f:
                f.write("def hello():\n    print('Hello')\n")
            
            with open(prompt_file, 'w') as f:
                f.write("Add a return statement")
            
            # Mock the injection to return modified content
            with patch('engine.diff_engine.inject_with_context') as mock_inject:
                mock_inject.return_value = "def hello():\n    print('Hello')\n    return True\n"
                
                # Preview the injection
                preview_result = preview_injection(
                    file_path=str(test_file),
                    prompt_path=str(prompt_file),
                    with_context=True
                )
                
                assert preview_result["has_changes"] is True
                assert "return True" in preview_result["after"]
                
                # Apply the injection
                apply_result = apply_injection(
                    file_path=str(test_file),
                    injected_content=preview_result["after"]
                )
                
                assert apply_result["success"] is True
                
                # Verify the file was actually modified
                with open(test_file, 'r') as f:
                    final_content = f.read()
                assert "return True" in final_content 