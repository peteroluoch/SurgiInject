"""
Mistral AI model client for SurgiInject

Handles communication with Mistral AI models for code modification tasks.
Implements real Groq API integration with no mock fallbacks.
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
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

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
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.mistral_api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.api_key = self.mistral_api_key  # Maintain backward compatibility
        self.model = model
        self.base_url = "https://api.mistral.ai/v1"

        # Determine active provider (no mock mode)
        if self.groq_api_key:
            self.active_provider = "groq"
            logger.info(f"Active provider selected: Groq (model: llama3-70b-8192)")
        elif self.anthropic_api_key:
            self.active_provider = "anthropic"
            logger.info(f"Active provider selected: Anthropic (model: claude-3-haiku-20240307)")
        elif self.mistral_api_key:
            self.active_provider = "mistral"
            logger.info(f"Active provider selected: Mistral (model: {self.model})")
        else:
            self.active_provider = None
            logger.error("No API keys provided. No AI providers available.")
    
    def generate_response(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1) -> Optional[Dict[str, Any]]:
        """
        Generate a response from the AI model with standardized format.
        
        Args:
            prompt (str): Input prompt
            max_tokens (int): Maximum tokens to generate
            temperature (float): Sampling temperature
            
        Returns:
            Dict with keys: 'text' (str), 'tokens' (int), or None if failed
        """
        # Try Groq API first (faster and free)
        if self.groq_api_key:
            try:
                logger.info("Making API call to Groq...")
                return self._call_groq_api(prompt, max_tokens, temperature)
            except Exception as e:
                logger.error(f"Error calling Groq API: {e}")
        
        # Try Anthropic API
        if self.anthropic_api_key:
            try:
                logger.info("Making API call to Anthropic...")
                return self._call_anthropic_api(prompt, max_tokens, temperature)
            except Exception as e:
                logger.error(f"Error calling Anthropic API: {e}")
        
        # Fallback to Mistral API if available
        if self.api_key:
            try:
                logger.info("Making API call to Mistral...")
                return self._call_mistral_api(prompt, max_tokens, temperature)
            except Exception as e:
                logger.error(f"Error calling Mistral API: {e}")
        
        # No providers available
        logger.error("No AI providers available")
        return None
    
    def _call_groq_api(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.2) -> Dict[str, Any]:
        """
        Call Groq API with standardized response format.

        Args:
            prompt (str): Input prompt
            max_tokens (int): Maximum tokens to generate
            temperature (float): Sampling temperature

        Returns:
            Dict with keys: 'text' (str), 'tokens' (int)

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
                result = response.json()
                logger.info(f"Groq API success on attempt {attempt + 1} (elapsed: {elapsed_time:.2f}s)")
                
                return {
                    "text": result['choices'][0]['message']['content'],
                    "tokens": result.get("usage", {}).get("total_tokens", 0)
                }

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

    def _call_anthropic_api(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Call Anthropic API with standardized response format.

        Args:
            prompt (str): Input prompt
            max_tokens (int): Maximum tokens to generate
            temperature (float): Sampling temperature

        Returns:
            Dict with keys: 'text' (str), 'tokens' (int)

        Raises:
            Exception: If API call fails
        """
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "claude-3-haiku-20240307",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            
            return {
                "text": result["content"][0]["text"],
                "tokens": result.get("usage", {}).get("input_tokens", 0) + result.get("usage", {}).get("output_tokens", 0)
            }
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise

    def _call_mistral_api(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Call Mistral API with retry logic and error handling.

        Args:
            prompt (str): Input prompt
            max_tokens (int): Maximum tokens to generate
            temperature (float): Sampling temperature

        Returns:
            Dict with keys: 'text' (str), 'tokens' (int)

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

                return {
                    "text": result,
                    "tokens": response.json().get("usage", {}).get("total_tokens", 0)
                }

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
                    raise Exception(f"Mistral API failed after {max_retries + 1} attempts: {error_type} - {e}")

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

# Updated run_model function to return standardized format
def run_model(prompt: str) -> Optional[str]:
    """
    Run the model with the given prompt.
    
    Args:
        prompt (str): The prompt to send to the model
        
    Returns:
        str: The model's response, or None if failed
    """
    try:
        client = MistralClient()
        response = client.generate_response(prompt)
        
        if response and response.get("text"):
            return response["text"]
        else:
            logger.error("No valid response from AI model")
            return None
            
    except Exception as e:
        logger.error(f"Error running model: {e}")
        return None
