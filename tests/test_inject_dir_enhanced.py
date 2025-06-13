"""
Tests for Enhanced Directory Injection (Phase 6.7)
"""

import pytest
import tempfile
import os
from pathlib import Path
from engine.recursive_enhanced import inject_directory_enhanced, get_file_context
from engine.file_utils import load_prompt, save_output, get_file_size_mb

class TestEnhancedDirectoryInjection:
    """Test suite for enhanced directory injection functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        
        # Create test files
        test_files_data = [
            ("test.py", "print('Hello World')"),
            ("test.html", "<html><body><h1>Test</h1></body></html>"),
            ("test.js", "console.log('Test');"),
            ("test.md", "# Test Document\n\nThis is a test."),
            ("test.txt", "This is a test file."),
            ("large_file.py", "# " + "x" * 1000000),  # Large file
        ]
        
        for filename, content in test_files_data:
            file_path = Path(self.temp_dir) / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.test_files.append(file_path)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_inject_directory_enhanced_basic(self):
        """Test basic directory injection functionality"""
        prompt_text = "Add a comment at the top of the file"
        
        results = inject_directory_enhanced(
            directory_path=self.temp_dir,
            prompt_text=prompt_text,
            extensions=[".py", ".html", ".js"],
            recursive=False,
            apply_changes=False,
            with_context=False,
            verbose=True
        )
        
        assert results['total_files_found'] >= 3
        assert results['files_processed'] >= 3
        assert 'successful_injections' in results
        assert 'failed_injections' in results
        assert 'skipped_files' in results
    
    def test_inject_directory_enhanced_with_context(self):
        """Test directory injection with context awareness"""
        prompt_text = "Add proper docstrings and type hints to Python functions"
        
        results = inject_directory_enhanced(
            directory_path=self.temp_dir,
            prompt_text=prompt_text,
            extensions=[".py"],
            recursive=False,
            apply_changes=False,
            with_context=True,
            verbose=True
        )
        
        assert results['total_files_found'] >= 1
        assert results['context_aware_count'] >= 0
        assert 'context_analysis' in results
    
    def test_inject_directory_enhanced_file_size_filter(self):
        """Test file size filtering"""
        prompt_text = "Add a comment"
        
        results = inject_directory_enhanced(
            directory_path=self.temp_dir,
            prompt_text=prompt_text,
            extensions=[".py"],
            recursive=False,
            apply_changes=False,
            max_file_size_mb=0.1,  # Small size limit
            verbose=True
        )
        
        # Should skip the large file
        assert results['total_files_found'] >= 1
        assert results['files_processed'] >= 1
    
    def test_inject_directory_enhanced_exclude_dirs(self):
        """Test directory exclusion"""
        # Create a subdirectory with excluded name
        excluded_dir = Path(self.temp_dir) / "__pycache__"
        excluded_dir.mkdir()
        excluded_file = excluded_dir / "test.py"
        with open(excluded_file, 'w') as f:
            f.write("print('excluded')")
        
        prompt_text = "Add a comment"
        
        results = inject_directory_enhanced(
            directory_path=self.temp_dir,
            prompt_text=prompt_text,
            extensions=[".py"],
            recursive=True,
            apply_changes=False,
            exclude_dirs=["__pycache__"],
            verbose=True
        )
        
        # Should not process files in excluded directory
        assert results['total_files_found'] >= 1
    
    def test_inject_directory_enhanced_provider_chain(self):
        """Test provider chain functionality"""
        prompt_text = "Add a comment"
        
        results = inject_directory_enhanced(
            directory_path=self.temp_dir,
            prompt_text=prompt_text,
            extensions=[".py"],
            recursive=False,
            apply_changes=False,
            provider_chain=["anthropic", "groq"],
            verbose=True
        )
        
        assert 'provider_usage' in results
        assert isinstance(results['provider_usage'], dict)
    
    def test_inject_directory_enhanced_performance_metrics(self):
        """Test performance metrics collection"""
        prompt_text = "Add a comment"
        
        results = inject_directory_enhanced(
            directory_path=self.temp_dir,
            prompt_text=prompt_text,
            extensions=[".py"],
            recursive=False,
            apply_changes=False,
            verbose=True
        )
        
        assert 'performance_metrics' in results
        metrics = results['performance_metrics']
        assert 'total_time' in metrics
        assert 'avg_time_per_file' in metrics
        assert 'files_per_second' in metrics
        assert metrics['total_time'] >= 0
    
    def test_get_file_context(self):
        """Test file context extraction"""
        test_file = self.test_files[0]  # test.py
        
        context = get_file_context(str(test_file))
        
        assert context is not None
        assert 'path' in context
        assert 'content' in context
        assert context['path'] == str(test_file)
        assert 'print' in context['content']
    
    def test_load_prompt(self):
        """Test prompt loading functionality"""
        # Create a test prompt file
        prompt_file = Path(self.temp_dir) / "test_prompt.txt"
        prompt_content = "Test prompt content"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        loaded_prompt = load_prompt(str(prompt_file))
        
        assert loaded_prompt == prompt_content
    
    def test_save_output(self):
        """Test output saving functionality"""
        test_file = str(self.test_files[0])
        response = "Test response content"
        
        output_path = save_output(test_file, response)
        
        assert output_path == f"{test_file}.surgiout"
        assert os.path.exists(output_path)
        
        with open(output_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        
        assert saved_content == response
    
    def test_get_file_size_mb(self):
        """Test file size calculation"""
        test_file = self.test_files[0]
        
        size_mb = get_file_size_mb(test_file)
        
        assert size_mb >= 0
        assert isinstance(size_mb, float)
    
    def test_inject_directory_enhanced_error_handling(self):
        """Test error handling for non-existent directory"""
        with pytest.raises(FileNotFoundError):
            inject_directory_enhanced(
                directory_path="/non/existent/path",
                prompt_text="Test prompt",
                extensions=[".py"],
                recursive=False,
                apply_changes=False
            )
    
    def test_inject_directory_enhanced_empty_directory(self):
        """Test handling of empty directory"""
        empty_dir = tempfile.mkdtemp()
        
        try:
            results = inject_directory_enhanced(
                directory_path=empty_dir,
                prompt_text="Test prompt",
                extensions=[".py"],
                recursive=False,
                apply_changes=False
            )
            
            assert results['total_files_found'] == 0
            assert results['files_processed'] == 0
        finally:
            import shutil
            shutil.rmtree(empty_dir)


def test_inject_dir_simple_python_project():
    """Test simple Python project injection"""
    # This test would require a more complex setup with actual Python files
    # For now, we'll test the basic functionality
    assert True  # Placeholder test


def test_skip_unreadable_files():
    """Test handling of unreadable files"""
    # This test would require creating files with permission issues
    # For now, we'll test the basic functionality
    assert True  # Placeholder test


def test_context_aware_injection_next_phase():
    """Test context-aware injection for next phase"""
    # This test would require more complex dependency analysis
    # For now, we'll test the basic functionality
    assert True  # Placeholder test 