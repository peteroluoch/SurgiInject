"""
Response Validator for SurgiInject
Detects weak AI responses and provides smart retry logic
"""

import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Failure log file
FAILURE_LOG = ".surgi_failures.json"
WEAK_RESPONSES_CACHE = ".surgi_weak_cache.json"


class ResponseValidator:
    """Validates AI responses and manages retry logic"""
    
    def __init__(self):
        self.failure_log_path = Path(FAILURE_LOG)
        self.weak_cache_path = Path(WEAK_RESPONSES_CACHE)
        self._load_weak_cache()
    
    def is_weak_response(self, response: str) -> bool:
        """
        Detect if an AI response is weak or unusable.
        
        Args:
            response: The AI response to validate
            
        Returns:
            True if response is weak, False if usable
        """
        if not response:
            return True
        
        response_lower = response.strip().lower()
        
        # Check for empty or very short responses
        if len(response.strip()) < 30:
            logger.warning(f"Weak response: Too short ({len(response.strip())} chars)")
            return True
        
        # Check for common weak response patterns
        weak_patterns = [
            "none", "n/a", "null", "undefined", "error", "failed",
            "i cannot", "i'm unable", "i don't know", "i'm not sure",
            "no changes needed", "no modifications required",
            "the code is already", "the file is already",
            "please provide more", "need more context",
            "cannot process", "unable to process",
            "invalid input", "malformed request"
        ]
        
        for pattern in weak_patterns:
            if pattern in response_lower:
                logger.warning(f"Weak response: Contains '{pattern}'")
                return True
        
        # Check for error-like responses
        error_indicators = [
            "exception", "traceback", "stack trace", "error occurred",
            "failed to", "could not", "unable to", "invalid",
            "syntax error", "runtime error", "type error"
        ]
        
        for indicator in error_indicators:
            if indicator in response_lower:
                logger.warning(f"Weak response: Contains error indicator '{indicator}'")
                return True
        
        # Check for responses that don't contain code (but only if they're short)
        if len(response.strip()) < 100:
            code_indicators = [
                "def ", "class ", "import ", "from ", "return ",
                "if ", "for ", "while ", "try:", "except:",
                "function ", "const ", "let ", "var ",
                "<", ">", "=", "(", ")", "{", "}"
            ]
            
            has_code = any(indicator in response for indicator in code_indicators)
            if not has_code:
                logger.warning("Weak response: No code detected")
                return True
        
        return False
    
    def is_duplicate_failure(self, file_path: str, prompt: str, provider: str) -> bool:
        """
        Check if this exact failure has occurred before.
        
        Args:
            file_path: Path to the file being processed
            prompt: The prompt that was used
            provider: The AI provider that failed
            
        Returns:
            True if this is a duplicate failure
        """
        failures = self._load_failures()
        
        for failure in failures:
            if (failure.get("file") == file_path and 
                failure.get("prompt") == prompt and 
                failure.get("provider") == provider):
                return True
        
        return False
    
    def log_failure(self, file_path: str, prompt: str, provider: str, reason: str) -> None:
        """
        Log a failure for future reference.
        
        Args:
            file_path: Path to the file being processed
            prompt: The prompt that was used
            provider: The AI provider that failed
            reason: Reason for the failure
        """
        entry = {
            "file": file_path,
            "prompt": prompt,
            "provider": provider,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "attempt_count": self._get_attempt_count(file_path, prompt, provider)
        }
        
        failures = self._load_failures()
        failures.append(entry)
        
        # Ensure directory exists
        self.failure_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.failure_log_path, 'w') as f:
            json.dump(failures, f, indent=2)
        
        logger.info(f"Failure logged: {provider} failed for {file_path}")
    
    def get_failure_stats(self) -> Dict:
        """
        Get statistics about failures.
        
        Returns:
            Dictionary with failure statistics
        """
        failures = self._load_failures()
        
        if not failures:
            return {
                "total_failures": 0,
                "providers": {},
                "files": {},
                "recent_failures": []
            }
        
        # Count by provider
        providers = {}
        for failure in failures:
            provider = failure.get("provider", "unknown")
            providers[provider] = providers.get(provider, 0) + 1
        
        # Count by file
        files = {}
        for failure in failures:
            file_path = failure.get("file", "unknown")
            files[file_path] = files.get(file_path, 0) + 1
        
        # Recent failures (last 10)
        recent_failures = sorted(failures, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
        
        return {
            "total_failures": len(failures),
            "providers": providers,
            "files": files,
            "recent_failures": recent_failures
        }
    
    def auto_correct_prompt(self, prompt: str, attempt: int = 1) -> str:
        """
        Automatically correct weak prompts.
        
        Args:
            prompt: Original prompt
            attempt: Current attempt number
            
        Returns:
            Corrected prompt
        """
        corrected = prompt
        
        # Basic corrections
        fixes = [
            ("explain", "rewrite with code"),
            ("discuss", "generate implementation"),
            ("outline", "implement code for"),
            ("describe", "create code that"),
            ("analyze", "modify the code to"),
            ("review", "update the code to"),
            ("examine", "transform the code to"),
            ("consider", "implement the following"),
        ]
        
        for bad, good in fixes:
            if bad in corrected.lower():
                corrected = corrected.replace(bad, good)
                corrected = corrected.replace(bad.title(), good.title())
        
        # Add urgency for retry attempts
        if attempt > 1:
            urgency_phrases = [
                "IMPORTANT: ",
                "CRITICAL: ",
                "URGENT: ",
                "PLEASE: "
            ]
            
            if not any(phrase in corrected for phrase in urgency_phrases):
                corrected = f"URGENT: {corrected}"
        
        # Add specific instructions for higher attempts
        if attempt >= 3:
            corrected += "\n\nIMPORTANT: Provide ONLY the modified code without explanations. Focus on the actual implementation."
        
        return corrected
    
    def get_optimal_provider_chain(self, file_path: str, prompt: str) -> List[str]:
        """
        Get optimal provider chain based on failure history.
        
        Args:
            file_path: Path to the file being processed
            prompt: The prompt being used
            
        Returns:
            List of providers to try in order
        """
        failures = self._load_failures()
        
        # Count failures by provider for this file
        provider_failures = {}
        for failure in failures:
            if failure.get("file") == file_path:
                provider = failure.get("provider", "unknown")
                provider_failures[provider] = provider_failures.get(provider, 0) + 1
        
        # Default provider chain
        default_chain = ["anthropic", "groq", "fallback"]
        
        # Reorder based on failure history (least failed first)
        if provider_failures:
            # Sort providers by failure count (ascending)
            sorted_providers = sorted(provider_failures.items(), key=lambda x: x[1])
            
            # Build new chain with least failed providers first
            new_chain = []
            for provider, _ in sorted_providers:
                if provider in default_chain:
                    new_chain.append(provider)
            
            # Add any providers not in failure history
            for provider in default_chain:
                if provider not in new_chain:
                    new_chain.append(provider)
            
            return new_chain
        
        return default_chain
    
    def _load_failures(self) -> List[Dict]:
        """Load failure log from file."""
        if not self.failure_log_path.exists():
            return []
        
        try:
            with open(self.failure_log_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load failure log: {e}")
            return []
    
    def _load_weak_cache(self) -> None:
        """Load weak responses cache."""
        if not self.weak_cache_path.exists():
            self.weak_cache = {}
            return
        
        try:
            with open(self.weak_cache_path, 'r') as f:
                self.weak_cache = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load weak cache: {e}")
            self.weak_cache = {}
    
    def _save_weak_cache(self) -> None:
        """Save weak responses cache."""
        try:
            with open(self.weak_cache_path, 'w') as f:
                json.dump(self.weak_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save weak cache: {e}")
    
    def _get_attempt_count(self, file_path: str, prompt: str, provider: str) -> int:
        """Get attempt count for this specific failure."""
        failures = self._load_failures()
        count = 0
        
        for failure in failures:
            if (failure.get("file") == file_path and 
                failure.get("prompt") == prompt and 
                failure.get("provider") == provider):
                count += 1
        
        return count + 1


# Global validator instance
validator = ResponseValidator()


def is_weak_response(response: str) -> bool:
    """Convenience function to check if response is weak."""
    return validator.is_weak_response(response)


def log_failure(file_path: str, prompt: str, provider: str, reason: str) -> None:
    """Convenience function to log a failure."""
    validator.log_failure(file_path, prompt, provider, reason)


def auto_correct_prompt(prompt: str, attempt: int = 1) -> str:
    """Convenience function to auto-correct a prompt."""
    return validator.auto_correct_prompt(prompt, attempt)


def get_optimal_provider_chain(file_path: str, prompt: str) -> List[str]:
    """Convenience function to get optimal provider chain."""
    return validator.get_optimal_provider_chain(file_path, prompt) 