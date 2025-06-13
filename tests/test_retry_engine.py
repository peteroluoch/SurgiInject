"""
Tests for retry engine and response validator functionality
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

from engine.response_validator import ResponseValidator, is_weak_response, log_failure, auto_correct_prompt
from engine.retry_engine import RetryEngine, inject_with_retry, inject_with_fallback


class TestResponseValidator:
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = ResponseValidator()
        
        # Override paths to use temp directory
        self.validator.failure_log_path = Path(self.temp_dir) / "test_failures.json"
        self.validator.weak_cache_path = Path(self.temp_dir) / "test_weak_cache.json"
    
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_is_weak_response_empty(self):
        """Test detection of empty responses"""
        assert is_weak_response("") is True
        assert is_weak_response(None) is True
        assert is_weak_response("   ") is True
    
    def test_is_weak_response_short(self):
        """Test detection of short responses"""
        assert is_weak_response("Hello") is True
        assert is_weak_response("This is too short") is True
        assert is_weak_response("x" * 25) is True
        assert is_weak_response("x" * 35) is False
    
    def test_is_weak_response_patterns(self):
        """Test detection of weak response patterns"""
        weak_responses = [
            "none",
            "n/a",
            "null",
            "undefined",
            "i cannot help",
            "i'm unable to",
            "i don't know",
            "no changes needed",
            "cannot process",
            "invalid input"
        ]
        
        for response in weak_responses:
            assert is_weak_response(response) is True
    
    def test_is_weak_response_error_indicators(self):
        """Test detection of error indicators"""
        error_responses = [
            "exception occurred",
            "traceback error",
            "stack trace",
            "failed to process",
            "syntax error",
            "runtime error"
        ]
        
        for response in error_responses:
            assert is_weak_response(response) is True
    
    def test_is_weak_response_good_code(self):
        """Test that good code responses are not flagged as weak"""
        good_responses = [
            "def hello():\n    print('Hello, World!')",
            "class MyClass:\n    def __init__(self):\n        pass",
            "import os\n\ndef main():\n    return True",
            "function test() {\n    return 'test';\n}",
            "const x = 1;\nlet y = 2;"
        ]
        
        for response in good_responses:
            assert is_weak_response(response) is False
    
    def test_log_failure(self):
        """Test failure logging"""
        log_failure("test.py", "test prompt", "anthropic", "test reason")
        
        assert self.validator.failure_log_path.exists()
        
        with open(self.validator.failure_log_path, 'r') as f:
            failures = json.load(f)
        
        assert len(failures) == 1
        failure = failures[0]
        assert failure["file"] == "test.py"
        assert failure["prompt"] == "test prompt"
        assert failure["provider"] == "anthropic"
        assert failure["reason"] == "test reason"
        assert "timestamp" in failure
        assert "attempt_count" in failure
    
    def test_is_duplicate_failure(self):
        """Test duplicate failure detection"""
        # Log a failure
        log_failure("test.py", "test prompt", "anthropic", "test reason")
        
        # Check if it's detected as duplicate
        assert self.validator.is_duplicate_failure("test.py", "test prompt", "anthropic") is True
        assert self.validator.is_duplicate_failure("test.py", "different prompt", "anthropic") is False
    
    def test_auto_correct_prompt(self):
        """Test automatic prompt correction"""
        original = "Explain the code structure"
        corrected = auto_correct_prompt(original)
        
        assert "explain" not in corrected.lower()
        assert "rewrite with code" in corrected.lower()
    
    def test_auto_correct_prompt_retry_attempts(self):
        """Test prompt correction for retry attempts"""
        original = "Discuss the implementation"
        
        # First attempt
        corrected1 = auto_correct_prompt(original, 1)
        assert "discuss" not in corrected1.lower()
        
        # Second attempt
        corrected2 = auto_correct_prompt(original, 2)
        assert "URGENT" in corrected2
        
        # Third attempt
        corrected3 = auto_correct_prompt(original, 3)
        assert "URGENT" in corrected3
        assert "ONLY the modified code" in corrected3
    
    def test_get_optimal_provider_chain(self):
        """Test optimal provider chain generation"""
        # With no failures, should return default chain
        chain = self.validator.get_optimal_provider_chain("test.py", "test prompt")
        assert "anthropic" in chain
        assert "groq" in chain
        assert "fallback" in chain
    
    def test_get_failure_stats(self):
        """Test failure statistics"""
        # Log some failures
        log_failure("test1.py", "prompt1", "anthropic", "reason1")
        log_failure("test2.py", "prompt2", "groq", "reason2")
        log_failure("test1.py", "prompt3", "anthropic", "reason3")
        
        stats = self.validator.get_failure_stats()
        
        assert stats["total_failures"] == 3
        assert stats["providers"]["anthropic"] == 2
        assert stats["providers"]["groq"] == 1
        assert stats["files"]["test1.py"] == 2
        assert stats["files"]["test2.py"] == 1
        assert len(stats["recent_failures"]) == 3


class TestRetryEngine:
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.retry_engine = RetryEngine(max_attempts=2, max_providers=2)
        
        # Override failure log path
        from engine.response_validator import validator
        validator.failure_log_path = Path(self.temp_dir) / "test_failures.json"
    
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_inject_with_retry_success_first_try(self):
        """Test successful injection on first try"""
        def mock_query_model(prompt, provider, **kwargs):
            return "def success():\n    return True"
        
        result = inject_with_retry(
            file_path="test.py",
            prompt="test prompt",
            query_model_func=mock_query_model
        )
        
        assert "def success()" in result
        assert "return True" in result
    
    def test_inject_with_retry_weak_response_escalation(self):
        """Test retry when first response is weak"""
        call_count = 0
        
        def mock_query_model(prompt, provider, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                return "none"  # Weak response
            else:
                return "def success():\n    return True"
        
        result = inject_with_retry(
            file_path="test.py",
            prompt="test prompt",
            query_model_func=mock_query_model
        )
        
        assert call_count == 2  # Should have retried
        assert "def success()" in result
    
    def test_inject_with_retry_all_failures(self):
        """Test behavior when all attempts fail"""
        def mock_query_model(prompt, provider, **kwargs):
            return "none"  # Always weak response
        
        with pytest.raises(RuntimeError, match="All.*attempts failed"):
            inject_with_retry(
                file_path="test.py",
                prompt="test prompt",
                query_model_func=mock_query_model
            )
    
    def test_inject_with_fallback_success(self):
        """Test fallback injection with success"""
        def mock_query_model(prompt, provider, **kwargs):
            return "def success():\n    return True"
        
        result = inject_with_fallback(
            file_path="test.py",
            prompt="test prompt",
            query_model_func=mock_query_model
        )
        
        assert "def success()" in result
    
    def test_inject_with_fallback_all_failures(self):
        """Test fallback injection when all attempts fail"""
        def mock_query_model(prompt, provider, **kwargs):
            return "none"  # Always weak response
        
        result = inject_with_fallback(
            file_path="test.py",
            prompt="test prompt",
            query_model_func=mock_query_model,
            fallback_content="def fallback():\n    return 'fallback'"
        )
        
        assert "def fallback()" in result
        assert "return 'fallback'" in result
    
    def test_inject_with_fallback_default_fallback(self):
        """Test default fallback when no custom fallback provided"""
        def mock_query_model(prompt, provider, **kwargs):
            return "none"  # Always weak response
        
        result = inject_with_fallback(
            file_path="test.py",
            prompt="test prompt",
            query_model_func=mock_query_model
        )
        
        assert "AI injection failed" in result
        assert "test.py" in result
    
    def test_get_retry_stats(self):
        """Test retry statistics"""
        stats = self.retry_engine.get_retry_stats()
        
        assert stats["max_attempts"] == 2
        assert stats["max_providers"] == 2
        assert "failure_stats" in stats
        assert stats["total_failures"] == 0
    
    def test_clear_failure_log(self):
        """Test clearing failure log"""
        # Create a failure log
        log_failure("test.py", "test prompt", "anthropic", "test reason")
        assert self.retry_engine.validator.failure_log_path.exists()
        
        # Clear it
        self.retry_engine.clear_failure_log()
        assert not self.retry_engine.validator.failure_log_path.exists()


class TestRetryEngineIntegration:
    """Integration tests for retry engine"""
    
    def test_full_retry_workflow(self):
        """Test complete retry workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up validator with temp directory
            from engine.response_validator import validator
            validator.failure_log_path = Path(temp_dir) / "failures.json"
            
            # Mock query function that fails first, succeeds second
            call_count = 0
            
            def mock_query(prompt, provider, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count == 1:
                    return "i cannot help"  # Weak response
                else:
                    return "def success():\n    return True"
            
            # Run injection
            result = inject_with_retry(
                file_path="test.py",
                prompt="test prompt",
                query_model_func=mock_query
            )
            
            # Verify results
            assert call_count == 2
            assert "def success()" in result
            
            # Check that failure was logged
            assert validator.failure_log_path.exists()
            with open(validator.failure_log_path, 'r') as f:
                failures = json.load(f)
            assert len(failures) == 1
            assert failures[0]["reason"] == "Weak response"
    
    def test_provider_escalation(self):
        """Test provider escalation when one fails"""
        call_count = 0
        providers_used = []
        
        def mock_query(prompt, provider, **kwargs):
            nonlocal call_count, providers_used
            call_count += 1
            providers_used.append(provider)
            
            if provider == "anthropic":
                return "none"  # Weak response
            else:
                return "def success():\n    return True"
        
        result = inject_with_retry(
            file_path="test.py",
            prompt="test prompt",
            query_model_func=mock_query,
            provider_chain=["anthropic", "groq"]
        )
        
        assert call_count == 2
        assert "anthropic" in providers_used
        assert "groq" in providers_used
        assert "def success()" in result 