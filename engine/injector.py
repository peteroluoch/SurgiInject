"""
Core injection engine for SurgiInject

Handles the main injection workflow:
1. Format prompt using prompty module
2. Send to AI model
3. Return modified code
"""

import logging
import os
import json
import hashlib
from dotenv import load_dotenv, find_dotenv
import requests
load_dotenv(find_dotenv())

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("logs/injection.log"),
    logging.StreamHandler()
])
logger = logging.getLogger(__name__)

# Check for environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Ensure API keys are included in the logic
if not ANTHROPIC_API_KEY:
    logger.warning(" Anthropic API key not found. Anthropic provider will be skipped.")

if not GROQ_API_KEY:
    logger.warning(" Groq API key not found. Groq provider will be skipped.")

from typing import Optional, Dict, Any
from .prompty import build_prompt
from .quality import is_response_weak, should_escalate, get_escalation_prompt
from models.mistral_client import run_model
from inject_logger import injection_logger

# Load cache from file if exists
CACHE_FILE = "surgi_cache.json"
try:
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        cache = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cache = {}

# Function to compute fingerprint for duplicate detection
def compute_fingerprint(file_content: str, prompt_content: str) -> str:
    """Compute a unique fingerprint for file + prompt combination to detect duplicates."""
    combined = file_content + prompt_content
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

# Function to normalize prompt for caching
def normalize_prompt(prompt):
    return ''.join(e for e in prompt.lower().strip() if e.isalnum())

def run_injection_from_files(source_path: str, prompt_path: str) -> str:
    """
    Run injection workflow using file paths directly.
    
    Args:
        source_path (str): Path to the source file
        prompt_path (str): Path to the prompt file
        
    Returns:
        str: Modified source code
    """
    with open(source_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_text = f.read()

    prompt = build_prompt(source_path, source_code, prompt_text)
    modified_code = run_model(prompt)
    return modified_code

def run_injection(source_code: str, prompt_template: str, file_path: Optional[str] = None, provider: str = 'auto', force: bool = False) -> str:
    """
    Run the injection process with enhanced error handling and escalation.
    
    Args:
        source_code (str): The source code to modify
        prompt_template (str): The prompt template content
        file_path (str, optional): Path to the source file for context
        provider (str, optional): Specify the provider to use
        force (bool, optional): Force injection even if duplicate prompt is detected
        
    Returns:
        str: Modified source code
        
    Raises:
        Exception: If any step in the injection process fails
    """
    try:
        logger.info("Starting injection process...")
        
        # Emit start event
        injection_logger.emit_start(
            prompt_file=prompt_template[:50] + "..." if len(prompt_template) > 50 else prompt_template,
            target_file=file_path or "unknown_file",
            provider=provider,
            cached=False
        )
        
        # Check for duplicate prompt using fingerprint
        fingerprint = compute_fingerprint(source_code, prompt_template)
        if not force and fingerprint in cache:
            logger.warning("Duplicate prompt detected - using cached result")
            cached_result = cache[fingerprint]
            if isinstance(cached_result, dict):
                result = cached_result.get("text", source_code)
                # Emit cache hit event
                injection_logger.emit_cache_hit(
                    target_file=file_path or "unknown_file",
                    provider=provider
                )
                return result
            return cached_result
        
        # Step 1: Build formatted prompt
        logger.info("Building formatted prompt...")
        if file_path is None:
            file_path = "unknown_file"
            
        formatted_prompt = build_prompt(
            file_path=file_path,
            code=source_code,
            task=prompt_template
        )
        
        logger.info(f"Prompt built successfully (length: {len(formatted_prompt)} chars)")
        
        # Handle provider selection
        if provider == 'auto':
            provider = auto_select_provider()
        logger.info(f"Selected provider: {provider}")
        
        # Step 2: Send to AI model with enhanced error handling
        logger.info("Sending to AI model...")
        modified_code = handle_injection(formatted_prompt, source_code)
        
        logger.info("AI model processing completed")
        
        # Step 3: Quality assessment and escalation with safe handling
        if is_response_weak(modified_code):
            logger.warning("Weak response detected, attempting escalation...")
            escalation_prompt = get_escalation_prompt(formatted_prompt, modified_code)
            try:
                escalated_response = run_model(escalation_prompt)
                if escalated_response and escalated_response.strip():
                    modified_code = escalated_response
                    logger.info("Escalation completed successfully")
                    # Emit escalation event
                    injection_logger.emit_escalation(
                        target_file=file_path or "unknown_file",
                        provider=provider,
                        escalation_provider="escalation_model"
                    )
                else:
                    logger.warning("Escalation returned empty response, keeping original")
            except Exception as e:
                logger.error(f"Escalation failed: {e}")
                logger.warning("Keeping original response due to escalation failure")
        
        # Step 4: Final validation
        if not modified_code or not modified_code.strip():
            logger.warning("AI model returned empty response, returning original code")
            return source_code
            
        logger.info("Injection process completed successfully")
        
        # Emit success event
        injection_logger.emit_success(
            target_file=file_path or "unknown_file",
            provider=provider,
            tokens=len(modified_code.split()),  # Approximate token count
            result_preview=modified_code[:100] + "..." if len(modified_code) > 100 else modified_code
        )
        
        return modified_code
        
    except Exception as e:
        logger.error(f"Injection process failed: {e}")
        
        # Emit error event
        injection_logger.emit_error(
            target_file=file_path or "unknown_file",
            provider=provider,
            error=str(e)
        )
        
        return f"[Injection failed: {str(e)}. Please try again later.]"

def validate_code_structure(original: str, modified: str) -> bool:
    """
    Basic validation to ensure the modified code maintains reasonable structure.
    
    Args:
        original (str): Original source code
        modified (str): Modified source code
        
    Returns:
        bool: True if structure seems reasonable, False otherwise
    """
    try:
        # Basic checks
        if len(modified) == 0:
            return False
            
        # Check if modification is too drastic (more than 300% size change)
        size_ratio = len(modified) / len(original) if len(original) > 0 else float('inf')
        if size_ratio > 3.0 or size_ratio < 0.1:
            logger.warning(f"Significant size change detected: {size_ratio:.2f}x")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Code validation failed: {e}")
        return False

def backup_file(file_path: str) -> str:
    """
    Create a backup of the original file before modification.
    
    Args:
        file_path (str): Path to the file to backup
        
    Returns:
        str: Path to the backup file
    """
    import shutil
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise

# Function to check for duplicate prompts
def is_duplicate(prompt_hash):
    # Use SQLite or JSON to track hashes
    return False

# Function to auto-select provider
def auto_select_provider():
    # Implement provider selection logic
    return 'anthropic'

# Function to get completion from provider with standardized response format
def get_completion(provider: str, prompt: str) -> Optional[Dict[str, Any]]:
    """
    Get completion from provider with standardized response format.
    
    Returns:
        Dict with keys: 'text' (str), 'tokens' (int), or None if failed
    """
    if provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            logger.error("Anthropic API key missing")
            return None
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024
                },
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            return {
                "text": result["content"][0]["text"],
                "tokens": result.get("usage", {}).get("input_tokens", 0) + result.get("usage", {}).get("output_tokens", 0)
            }
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return None
    elif provider == "groq":
        if not GROQ_API_KEY:
            logger.error("Groq API key missing")
            return None
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-70b-8192",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024
                },
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            return {
                "text": result["choices"][0]["message"]["content"],
                "tokens": result.get("usage", {}).get("total_tokens", 0)
            }
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            return None
    else:
        logger.error(f"Unknown provider: {provider}")
        return None

# Function to handle injection with cache, duplicate detection, and real providers only
def handle_injection(prompt: str, file_content: str = "", no_cache: bool = False, force_refresh: bool = False) -> str:
    """
    Handle injection with cache, duplicate detection, and real providers only.
    
    Args:
        prompt: The prompt to send to AI
        file_content: Content of the file being modified (for duplicate detection)
        no_cache: Whether to skip cache
        force_refresh: Whether to force refresh even if cached
        
    Returns:
        str: AI response or friendly error message
    """
    # Compute fingerprint for duplicate detection
    fingerprint = compute_fingerprint(file_content, prompt)
    
    # Check cache first (unless disabled)
    if not force_refresh and not no_cache and fingerprint in cache:
        logger.info("Cache hit - skipping AI call")
        cached_result = cache[fingerprint]
        if isinstance(cached_result, dict):
            return cached_result.get("text", "[Cached response]")
        return cached_result

    # Try real providers only (no mocks)
    providers = []
    if ANTHROPIC_API_KEY:
        providers.append("anthropic")
    if GROQ_API_KEY:
        providers.append("groq")
    
    if not providers:
        logger.error("No valid AI providers available")
        return "[No AI providers configured. Please check your API keys.]"
    
    total_tokens = 0
    
    for provider in providers:
        try:
            logger.info(f"Trying provider: {provider}")
            response = get_completion(provider, prompt)
            
            if response and response.get("text"):
                result_text = response["text"]
                total_tokens = response.get("tokens", 0)
                
                # Cache the result
                if not no_cache:
                    cache[fingerprint] = response
                    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(cache, f)
                
                logger.info(f"{provider} success - Tokens used: {total_tokens}")
                return result_text
            else:
                logger.warning(f"{provider} returned empty response")
                
        except Exception as e:
            logger.warning(f"{provider} failed: {e}")
            # Emit fallback event if this wasn't the last provider
            if provider != providers[-1]:
                next_provider = providers[providers.index(provider) + 1]
                injection_logger.emit_fallback(
                    target_file="unknown_file",
                    failed_provider=provider,
                    fallback_provider=next_provider
                )
    
    logger.error("All providers failed")
    return "[All AI providers failed. Please try again later or check your configuration.]"
