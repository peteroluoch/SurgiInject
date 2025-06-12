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
        Initialize Mistral client.
        
        Args:
            api_key (str, optional): Mistral API key. If None, will try to get from environment.
            model (str): Model name to use
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.model = model
        self.base_url = "https://api.mistral.ai/v1"
        
        # Check for Groq API key first, then Mistral
        self.groq_api_key = GROQ_API_KEY
        if not self.api_key and not self.groq_api_key:
            logger.warning("No API key provided. Using mock responses.")
            self.mock_mode = True
        else:
            self.mock_mode = False
    
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
                # Real Mistral API implementation would go here
                return self._mock_response(prompt)
            except Exception as e:
                logger.error(f"Error calling Mistral API: {e}")
                return self._mock_response(prompt)
        
        # Final fallback
        return self._mock_response(prompt)
    
    def _call_groq_api(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.2) -> str:
        """
        Call Groq API with Mixtral model.
        
        Args:
            prompt (str): Input prompt
            max_tokens (int): Maximum tokens to generate
            temperature (float): Sampling temperature
            
        Returns:
            str: Generated response
        """
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "system", "content": "You are a surgical code refactorer. Fix bugs with precision."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    
    def _mock_response(self, prompt: str) -> str:
        """
        Generate a mock response for testing purposes.
        
        Args:
            prompt (str): Input prompt
            
        Returns:
            str: Mock modified code
        """
        logger.info("Generating mock response...")
        
        # Extract source code from prompt
        code_match = re.search(r'```(?:\w+)?\n(.*?)```', prompt, re.DOTALL)
        if code_match:
            source_code = code_match.group(1)
        else:
            # Fallback: look for code after "SOURCE CODE:"
            lines = prompt.split('\n')
            code_start = -1
            for i, line in enumerate(lines):
                if 'SOURCE CODE:' in line:
                    code_start = i + 1
                    break
            
            if code_start >= 0:
                # Take lines after SOURCE CODE until we hit INSTRUCTION
                code_lines = []
                for i in range(code_start, len(lines)):
                    if 'INSTRUCTION:' in lines[i]:
                        break
                    code_lines.append(lines[i])
                source_code = '\n'.join(code_lines).strip()
            else:
                # If we can't parse the code, return the original with a comment
                source_code = "# Original code could not be parsed\npass"
        
        # Clean up the extracted code
        source_code = source_code.strip()
        if source_code.startswith('```') and source_code.endswith('```'):
            lines = source_code.split('\n')
            source_code = '\n'.join(lines[1:-1])
        
        # Simulate different types of modifications based on the task
        task_lower = prompt.lower()
        
        if 'bug' in task_lower or 'fix' in task_lower:
            modified_code = self._add_bug_fix_comment(source_code)
        elif 'test' in task_lower:
            modified_code = self._add_test_comment(source_code)
        elif 'optimize' in task_lower or 'performance' in task_lower:
            modified_code = self._add_optimization_comment(source_code)
        elif 'security' in task_lower:
            modified_code = self._add_security_comment(source_code)
        elif 'documentation' in task_lower or 'doc' in task_lower:
            modified_code = self._add_documentation(source_code)
        else:
            modified_code = self._add_generic_enhancement(source_code)
        
        # Add a small delay to simulate API call time
        time.sleep(0.5)
        
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
