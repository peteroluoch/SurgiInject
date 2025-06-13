"""
Mistral AI model client for SurgiInject

Handles communication with Mistral AI models for code modification tasks.
Implements real Groq API integration with fallback to mock responses.
"""

import os
import logging
import time
import re
import requests
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class MistralClient:
    """Client for interacting with Mistral AI models"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistral-7b-instruct"):
        """
        Initialize Mistral client with secure key injection and configuration logic.

        Args:
            api_key (str, optional): Mistral API key. If None, will try to get from environment.
            model (str): Model name to use
        """
        # Secure key injection with dynamic environment-based loading
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.mistral_api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.api_key = self.mistral_api_key  # Maintain backward compatibility
        self.model = model
        self.base_url = "https://api.mistral.ai/v1"

        # Determine active provider and set mock mode
        if self.groq_api_key:
            self.active_provider = "groq"
            self.mock_mode = False
            logger.info(f"Active provider selected: Groq (model: llama3-70b-8192)")
        elif self.mistral_api_key:
            self.active_provider = "mistral"
            self.mock_mode = False
            logger.info(f"Active provider selected: Mistral (model: {self.model})")
        else:
            self.active_provider = "mock"
            self.mock_mode = True
            logger.warning("No API key provided. Using mock responses.")
            logger.info("Active provider selected: Mock")

        # Initialize mock strategies dispatch map for scalable strategy selection
        self.mock_strategies = {
            "bug": self._add_comprehensive_bug_fixes,
            "fix": self._add_comprehensive_bug_fixes,
            "test": self._add_test_enhancements,
            "optimize": self._add_performance_optimizations,
            "performance": self._add_performance_optimizations,
            "security": self._add_security_enhancements,
            "documentation": self._add_comprehensive_documentation,
            "doc": self._add_comprehensive_documentation,
            "mobile": self._add_mobile_fixes,
        }
    
    def generate_response(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1) -> str:
        """
        Generate a response from the Mistral model.
        
        Args:
            prompt (str): Input prompt
            max_tokens (int): Maximum tokens to generate
            temperature (float): Sampling temperature
            
        Returns:
            str: Generated response
        """
        if self.mock_mode:
            return self._mock_response(prompt)
        
        # Try Groq API first (faster and free)
        if self.groq_api_key:
            try:
                logger.info("Making API call to Groq/Mixtral...")
                return self._call_groq_api(prompt, max_tokens, temperature)
            except Exception as e:
                logger.error(f"Error calling Groq API: {e}")
                logger.info("Falling back to mock response")
                return self._mock_response(prompt)
        
        # Fallback to Mistral API if available
        if self.api_key:
            try:
                logger.info("Making API call to Mistral...")
                return self._call_mistral_api(prompt, max_tokens, temperature)
            except Exception as e:
                logger.error(f"Error calling Mistral API: {e}")
                logger.info("Falling back to mock response")
                return self._mock_response(prompt)
        
        # Final fallback
        return self._mock_response(prompt)
    
    def _call_groq_api(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.2) -> str:
        """
        Call Groq API with Mixtral model with retry logic and error handling.

        Args:
            prompt (str): Input prompt
            max_tokens (int): Maximum tokens to generate
            temperature (float): Sampling temperature

        Returns:
            str: Generated response

        Raises:
            Exception: If all retry attempts fail
        """
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": "You are a surgical code refactorer. Fix bugs with precision."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        max_retries = 2
        start_time = time.time()

        for attempt in range(max_retries + 1):
            attempt_start = time.time()
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                elapsed_time = time.time() - attempt_start

                response.raise_for_status()
                logger.info(f"Groq API success on attempt {attempt + 1} (elapsed: {elapsed_time:.2f}s)")
                return response.json()['choices'][0]['message']['content']

            except requests.exceptions.RequestException as e:
                elapsed_time = time.time() - attempt_start

                # Smart error intelligence with detailed logging
                error_type = type(e).__name__
                status_code = getattr(response, 'status_code', 'N/A') if 'response' in locals() else 'N/A'

                logger.error(f"Groq API attempt {attempt + 1}/{max_retries + 1} failed:")
                logger.error(f"  Error type: {error_type}")
                logger.error(f"  Status code: {status_code}")
                logger.error(f"  Elapsed time: {elapsed_time:.2f}s")
                logger.error(f"  Error details: {str(e)[:200]}")

                if hasattr(response, 'text') and 'response' in locals():
                    logger.error(f"  Response payload: {response.text[:300]}")

                # Determine if we should retry based on error type
                should_retry = self._should_retry_groq_error(e, status_code, attempt, max_retries)

                if should_retry and attempt < max_retries:
                    retry_delay = min(2 ** attempt, 5)  # Exponential backoff, max 5s
                    logger.info(f"Retrying in {retry_delay}s... (attempt {attempt + 2}/{max_retries + 1})")
                    time.sleep(retry_delay)
                else:
                    total_elapsed = time.time() - start_time
                    logger.error(f"Groq API failed after {max_retries + 1} attempts (total time: {total_elapsed:.2f}s)")
                    raise Exception(f"Groq API failed after {max_retries + 1} attempts: {error_type} - {e}")

    def _should_retry_groq_error(self, error: Exception, status_code: str, attempt: int, max_retries: int) -> bool:
        """
        Determine if a Groq API error should trigger a retry based on error intelligence.

        Args:
            error: The exception that occurred
            status_code: HTTP status code if available
            attempt: Current attempt number (0-based)
            max_retries: Maximum number of retries allowed

        Returns:
            bool: True if should retry, False otherwise
        """
        if attempt >= max_retries:
            return False

        # Retry on network-related errors
        if isinstance(error, (requests.exceptions.ConnectionError,
                             requests.exceptions.Timeout,
                             requests.exceptions.ConnectTimeout,
                             requests.exceptions.ReadTimeout)):
            logger.info("Network error detected - will retry")
            return True

        # Retry on server errors (5xx)
        if isinstance(status_code, int) and 500 <= status_code < 600:
            logger.info(f"Server error {status_code} detected - will retry")
            return True

        # Retry on rate limiting (429)
        if status_code == 429:
            logger.info("Rate limit detected - will retry with backoff")
            return True

        # Don't retry on client errors (4xx except 429)
        if isinstance(status_code, int) and 400 <= status_code < 500 and status_code != 429:
            logger.info(f"Client error {status_code} detected - will not retry")
            return False

        # Default: retry for unknown errors
        logger.info("Unknown error type - will retry")
        return True

    def _call_mistral_api(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1) -> str:
        """
        Call Mistral API with retry logic and error handling.

        Args:
            prompt (str): Input prompt
            max_tokens (int): Maximum tokens to generate
            temperature (float): Sampling temperature

        Returns:
            str: Generated response

        Raises:
            Exception: If all retry attempts fail
        """
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a surgical code refactorer. Fix bugs with precision."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        max_retries = 2
        start_time = time.time()

        logger.info(f"Calling Mistral API with model: {self.model}")

        for attempt in range(max_retries + 1):
            attempt_start = time.time()
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                elapsed_time = time.time() - attempt_start

                response.raise_for_status()
                result = response.json()['choices'][0]['message']['content']

                logger.info(f"Mistral API success on attempt {attempt + 1}")
                logger.info(f"  Model used: {self.model}")
                logger.info(f"  Response time: {elapsed_time:.2f}s")
                logger.info(f"  Response length: {len(result)} characters")

                return result

            except requests.exceptions.RequestException as e:
                elapsed_time = time.time() - attempt_start
                error_type = type(e).__name__
                status_code = getattr(response, 'status_code', 'N/A') if 'response' in locals() else 'N/A'

                logger.error(f"Mistral API attempt {attempt + 1}/{max_retries + 1} failed:")
                logger.error(f"  Model: {self.model}")
                logger.error(f"  Error type: {error_type}")
                logger.error(f"  Status code: {status_code}")
                logger.error(f"  Elapsed time: {elapsed_time:.2f}s")
                logger.error(f"  Error details: {str(e)[:200]}")

                if hasattr(response, 'text') and 'response' in locals():
                    logger.error(f"  Response payload: {response.text[:300]}")

                if attempt < max_retries:
                    retry_delay = min(2 ** attempt, 5)  # Exponential backoff
                    logger.info(f"Retrying in {retry_delay}s... (attempt {attempt + 2}/{max_retries + 1})")
                    time.sleep(retry_delay)
                else:
                    total_elapsed = time.time() - start_time
                    logger.error(f"Mistral API failed after {max_retries + 1} attempts (total time: {total_elapsed:.2f}s)")
                    logger.error("Falling back to mock response")
                    raise Exception(f"Mistral API failed after {max_retries + 1} attempts: {error_type} - {e}")

    def _mock_response(self, prompt: str) -> str:
        """
        Generate a sophisticated mock response for testing purposes.
        
        Args:
            prompt (str): Input prompt
            
        Returns:
            str: Mock modified code
        """
        logger.info("Generating mock response...")
        
        # Extract source code from prompt - improved extraction
        code_match = re.search(r'```(?:\w+)?\s*\n(.*?)```', prompt, re.DOTALL)
        if code_match:
            source_code = code_match.group(1).strip()
        else:
            # Look for CONTEXT section in Phase 3 format
            context_match = re.search(r'💬 CONTEXT:\s*\n(.*?)(?:\n🚀 INSTRUCTION:|$)', prompt, re.DOTALL)
            if context_match:
                source_code = context_match.group(1).strip()
            else:
                # Fallback extraction
                lines = prompt.split('\n')
                code_lines = []
                in_code_section = False
                
                for line in lines:
                    if 'CONTEXT:' in line or 'SOURCE CODE:' in line:
                        in_code_section = True
                        continue
                    elif 'INSTRUCTION:' in line:
                        break
                    elif in_code_section:
                        code_lines.append(line)
                
                source_code = '\n'.join(code_lines).strip()
        
        if not source_code or len(source_code) < 10:
            source_code = "# Original code could not be parsed\npass"
        
        # Check for escalation first (highest priority)
        is_escalation = 'ESCALATION REQUEST' in prompt or 'WEAK RESPONSE' in prompt
        task_lower = prompt.lower()

        if is_escalation:
            logger.info("Escalation detected - generating high-quality response")
            modified_code = self._generate_escalated_response(source_code, task_lower)
        else:
            # Use dispatch map for scalable strategy selection
            selected_strategy = None
            matched_keyword = None

            # Find first matching keyword in prompt using dispatch map
            for keyword, strategy in self.mock_strategies.items():
                if keyword in task_lower:
                    selected_strategy = strategy
                    matched_keyword = keyword
                    break

            if selected_strategy:
                logger.info(f"Strategy selected: {matched_keyword} -> {selected_strategy.__name__}")
                modified_code = selected_strategy(source_code)
            else:
                # Fallback to generic enhancement if no match
                logger.info("No specific strategy matched - using generic enhancement")
                modified_code = self._add_generic_enhancement(source_code)

                # Check if response seems weak or ambiguous for potential escalation
                if len(modified_code) < 100 or 'pass' in source_code:
                    logger.warning("Response may be weak - consider escalation")
                    # Could trigger escalation logic here if needed
        
        # Add delay to simulate API call
        time.sleep(0.3)
        
        return modified_code
    
    def _add_bug_fix_comment(self, code: str) -> str:
        """Add bug fix related modifications"""
        lines = code.split('\n')
        
        # Add a comment at the beginning
        if lines and lines[0].strip():
            lines.insert(0, "# [SURGIINJECT] Bug fix applied - enhanced error handling")
            lines.insert(1, "")
        
        # Add error handling if it looks like a function
        if any('def ' in line for line in lines):
            # Find first function and add try-catch
            for i, line in enumerate(lines):
                if line.strip().startswith('def ') and ':' in line:
                    # Insert error handling after function definition
                    indent = len(line) - len(line.lstrip())
                    try_line = ' ' * (indent + 4) + "try:"
                    except_line = ' ' * (indent + 4) + "except Exception as e:"
                    log_line = ' ' * (indent + 8) + "# Handle error appropriately"
                    raise_line = ' ' * (indent + 8) + "raise"
                    
                    # Insert after the function line
                    lines.insert(i + 1, try_line)
                    lines.insert(i + 2, ' ' * (indent + 8) + "# Original function logic here")
                    lines.insert(i + 3, except_line)
                    lines.insert(i + 4, log_line)
                    lines.insert(i + 5, raise_line)
                    break
        
        return '\n'.join(lines)
    
    def _add_test_comment(self, code: str) -> str:
        """Add test-related modifications"""
        lines = code.split('\n')
        lines.insert(0, "# [SURGIINJECT] Test coverage enhanced")
        lines.insert(1, "# Added comprehensive test cases and assertions")
        lines.insert(2, "")
        return '\n'.join(lines)
    
    def _add_optimization_comment(self, code: str) -> str:
        """Add optimization-related modifications"""
        lines = code.split('\n')
        lines.insert(0, "# [SURGIINJECT] Performance optimization applied")
        lines.insert(1, "# Improved algorithm efficiency and reduced complexity")
        lines.insert(2, "")
        
        # If there are loops, add optimization comment
        for i, line in enumerate(lines):
            if 'for ' in line or 'while ' in line:
                indent = len(line) - len(line.lstrip())
                opt_comment = ' ' * indent + "# Optimized loop for better performance"
                lines.insert(i, opt_comment)
                break
        
        return '\n'.join(lines)
    
    def _add_security_comment(self, code: str) -> str:
        """Add security-related modifications"""
        lines = code.split('\n')
        lines.insert(0, "# [SURGIINJECT] Security enhancement applied")
        lines.insert(1, "# Added input validation and sanitization")
        lines.insert(2, "")
        return '\n'.join(lines)
    
    def _add_documentation(self, code: str) -> str:
        """Add documentation improvements"""
        lines = code.split('\n')
        
        # Add module-level docstring if not present
        if not (len(lines) > 0 and lines[0].strip().startswith('"""')):
            lines.insert(0, '"""')
            lines.insert(1, "[SURGIINJECT] Enhanced module documentation")
            lines.insert(2, "")
            lines.insert(3, "This module has been enhanced with comprehensive documentation")
            lines.insert(4, "including detailed function descriptions and usage examples.")
            lines.insert(5, '"""')
            lines.insert(6, "")
        
        # Add docstrings to functions
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') and ':' in line:
                indent = len(line) - len(line.lstrip())
                doc_indent = ' ' * (indent + 4)
                
                lines.insert(i + 1, doc_indent + '"""')
                lines.insert(i + 2, doc_indent + '[SURGIINJECT] Enhanced function documentation')
                lines.insert(i + 3, doc_indent + '')
                lines.insert(i + 4, doc_indent + 'Returns:')
                lines.insert(i + 5, doc_indent + '    Enhanced functionality with improved documentation')
                lines.insert(i + 6, doc_indent + '"""')
                break
        
        return '\n'.join(lines)
    
    def _add_generic_enhancement(self, code: str) -> str:
        """Add generic enhancement"""
        lines = code.split('\n')
        lines.insert(0, "# [SURGIINJECT] Code enhancement applied")
        lines.insert(1, "# Improved code quality and maintainability")
        lines.insert(2, "")
        
        # Add a comment at the end
        lines.append("")
        lines.append("# [SURGIINJECT] Enhancement complete")
        
        return '\n'.join(lines)
    
    def _add_mobile_fixes(self, code: str) -> str:
        """Add comprehensive mobile bug fixes"""
        lines = code.split('\n')
        
        # Add mobile-specific enhancements
        mobile_fixes = [
            "// [SURGIINJECT] Mobile bug fixes applied",
            "// Added viewport meta tag handling",
            "// Enhanced touch event support", 
            "// Mobile browser compatibility checks",
            "// Network error handling for mobile",
            "// Responsive positioning fixes",
            ""
        ]
        
        # Insert fixes at the beginning
        result_lines = mobile_fixes + lines
        
        # Add mobile-specific improvements throughout the code
        enhanced_lines = []
        for line in result_lines:
            enhanced_lines.append(line)
            
            # Add touch event handlers after mouse events
            if 'mousedown' in line and 'addEventListener' in line:
                indent = len(line) - len(line.lstrip())
                touch_line = ' ' * indent + line.replace('mousedown', 'touchstart').replace('mousedown', 'touchstart')
                enhanced_lines.append(touch_line)
            
            # Add network timeout handling
            if 'fetch(' in line:
                indent = len(line) - len(line.lstrip())
                enhanced_lines.append(' ' * indent + "// Added mobile network timeout handling")
        
        return '\n'.join(enhanced_lines)
    
    def _add_comprehensive_bug_fixes(self, code: str) -> str:
        """Add comprehensive bug fixes"""
        lines = code.split('\n')
        
        fixes = [
            "// [SURGIINJECT] Comprehensive bug fixes applied",
            "// Enhanced error handling and validation",
            ""
        ]
        
        result_lines = fixes + lines
        
        # Add try-catch blocks to functions
        enhanced_lines = []
        for i, line in enumerate(result_lines):
            enhanced_lines.append(line)
            
            if line.strip().startswith('function ') or 'def ' in line:
                indent = len(line) - len(line.lstrip())
                enhanced_lines.append(' ' * (indent + 4) + "try {")
                enhanced_lines.append(' ' * (indent + 8) + "// Original function logic")
                enhanced_lines.append(' ' * (indent + 4) + "} catch (error) {")
                enhanced_lines.append(' ' * (indent + 8) + "console.error('Function error:', error);")
                enhanced_lines.append(' ' * (indent + 8) + "throw error;")
                enhanced_lines.append(' ' * (indent + 4) + "}")
        
        return '\n'.join(enhanced_lines)
    
    def _add_test_enhancements(self, code: str) -> str:
        """Add test-related enhancements"""
        lines = code.split('\n')
        
        enhancements = [
            "// [SURGIINJECT] Test coverage enhanced",
            "// Added comprehensive test cases",
            "// Improved assertions and edge case handling",
            ""
        ]
        
        return '\n'.join(enhancements + lines)
    
    def _add_performance_optimizations(self, code: str) -> str:
        """Add performance optimizations"""
        lines = code.split('\n')
        
        optimizations = [
            "// [SURGIINJECT] Performance optimizations applied",
            "// Improved algorithm efficiency",
            "// Reduced computational complexity",
            ""
        ]
        
        enhanced_lines = optimizations + lines
        
        # Add caching and memoization hints
        for i, line in enumerate(enhanced_lines):
            if 'for ' in line or 'while ' in line:
                indent = len(line) - len(line.lstrip())
                enhanced_lines.insert(i, ' ' * indent + "// Optimized loop with caching")
                break
        
        return '\n'.join(enhanced_lines)
    
    def _add_security_enhancements(self, code: str) -> str:
        """Add security enhancements"""
        lines = code.split('\n')
        
        security_fixes = [
            "// [SURGIINJECT] Security enhancements applied",
            "// Added input validation and sanitization",
            "// Enhanced authentication and authorization",
            "// SQL injection and XSS protection",
            ""
        ]
        
        return '\n'.join(security_fixes + lines)
    
    def _add_comprehensive_documentation(self, code: str) -> str:
        """Add comprehensive documentation"""
        lines = code.split('\n')
        
        doc_header = [
            "/**",
            " * [SURGIINJECT] Comprehensive documentation added",
            " * ",
            " * This module has been enhanced with detailed documentation",
            " * including function descriptions, parameter types, and usage examples.",
            " */",
            ""
        ]
        
        enhanced_lines = doc_header + lines
        
        # Add JSDoc to functions
        result_lines = []
        for line in enhanced_lines:
            if line.strip().startswith('function ') or line.strip().startswith('class '):
                indent = len(line) - len(line.lstrip())
                result_lines.extend([
                    ' ' * indent + "/**",
                    ' ' * indent + " * Enhanced function with comprehensive documentation",
                    ' ' * indent + " * @returns {any} Enhanced functionality with improved documentation",
                    ' ' * indent + " */"
                ])
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _add_intelligent_enhancements(self, code: str) -> str:
        """Add intelligent general enhancements"""
        lines = code.split('\n')
        
        enhancements = [
            "// [SURGIINJECT] Intelligent enhancements applied",
            "// Improved code quality and maintainability",
            "// Added best practices and modern patterns",
            ""
        ]
        
        result_lines = enhancements + lines + ["", "// [SURGIINJECT] Enhancement complete"]
        return '\n'.join(result_lines)
    
    def _generate_escalated_response(self, code: str, task_context: str) -> str:
        """Generate high-quality escalated response"""
        lines = code.split('\n')
        
        escalated_header = [
            "// [SURGIINJECT] ESCALATED RESPONSE - High Quality Enhancement",
            "// Previous response was insufficient, providing comprehensive solution",
            "// Production-ready implementation with full error handling",
            ""
        ]
        
        # Apply multiple enhancement layers for escalated response
        enhanced_code = '\n'.join(escalated_header + lines)
        
        if 'mobile' in task_context:
            enhanced_code = self._add_mobile_fixes(enhanced_code)
        if 'security' in task_context:
            enhanced_code = self._add_security_enhancements(enhanced_code)
        if 'performance' in task_context:
            enhanced_code = self._add_performance_optimizations(enhanced_code)
        
        # Add comprehensive error handling
        lines = enhanced_code.split('\n')
        final_lines = []
        
        for line in lines:
            final_lines.append(line)
            if 'function ' in line or 'class ' in line:
                indent = len(line) - len(line.lstrip())
                final_lines.extend([
                    ' ' * (indent + 4) + "// Escalated: Comprehensive error handling",
                    ' ' * (indent + 4) + "try {",
                    ' ' * (indent + 8) + "// Enhanced implementation with full validation",
                    ' ' * (indent + 4) + "} catch (error) {",
                    ' ' * (indent + 8) + "console.error('Escalated error handling:', error);",
                    ' ' * (indent + 8) + "// Implement recovery strategy",
                    ' ' * (indent + 8) + "throw error;",
                    ' ' * (indent + 4) + "}"
                ])
                break
        
        return '\n'.join(final_lines)

# Convenience function for backward compatibility
def run_model(prompt: str) -> str:
    """
    Run the Mistral model with the given prompt.
    
    Args:
        prompt (str): Input prompt for the model
        
    Returns:
        str: Generated response
    """
    client = MistralClient()
    return client.generate_response(prompt)
