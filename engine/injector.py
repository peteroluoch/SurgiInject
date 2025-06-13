"""
Core injection engine for SurgiInject

Handles the main injection workflow:
1. Format prompt using prompty module
2. Send to AI model
3. Return modified code
"""

import logging
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Check for environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("logs/injection.log"),
    logging.StreamHandler()
])
logger = logging.getLogger(__name__)

from typing import Optional
from .prompty import build_prompt
from .quality import is_response_weak, should_escalate, get_escalation_prompt
from models.mistral_client import run_model

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
    Run the complete injection workflow.
    
    Args:
        source_code (str): The original source code to modify
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
        
        # Check for duplicate prompt
        prompt_hash = hash(prompt_template)
        if not force and is_duplicate(prompt_hash):
            logger.warning("⚠️ Duplicate prompt detected. Skipping.")
            return source_code
        
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
        
        # Step 2: Send to AI model
        logger.info("Sending to AI model...")
        modified_code = handle_injection(formatted_prompt)
        
        logger.info("AI model processing completed")
        
        # Step 3: Quality assessment and escalation
        if is_response_weak(modified_code):
            logger.warning("Weak response detected, attempting escalation...")
            escalation_prompt = get_escalation_prompt(formatted_prompt, modified_code)
            try:
                modified_code = run_model(escalation_prompt)
                logger.info("Escalation completed")
            except Exception as e:
                logger.error(f"Escalation failed: {e}")
        
        # Step 4: Final validation
        if not modified_code or not modified_code.strip():
            logger.warning("AI model returned empty response, returning original code")
            return source_code
            
        logger.info("Injection process completed successfully")
        logger.info(f"🔥 Injected: {provider} | ⏱ {len(source_code)} tokens | ✅ success")
        return modified_code
        
    except Exception as e:
        logger.error(f"Injection process failed: {e}")
        raise Exception(f"Injection failed: {e}")

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

# Function to get completion from provider
def get_completion(provider, prompt):
    if provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            logger.warning("🔑 Anthropic key missing — skipping to Groq")
            raise Exception("Anthropic key missing")
        # Implement Anthropic API call
    elif provider == "groq-mixtral":
        if not GROQ_API_KEY:
            logger.warning("🔑 Groq Mixtral key missing — skipping to next")
            raise Exception("Groq Mixtral key missing")
        # Implement Groq Mixtral API call
    elif provider == "groq-gemma":
        # Implement Groq Gemma API call
        pass
    elif provider == "groq-llama":
        # Implement Groq LLaMA API call
        pass
    else:
        # Mock fallback
        return "Mock response"

# Function to handle injection with fallback
def handle_injection(prompt):
    providers = ["anthropic", "groq-mixtral", "groq-gemma", "groq-llama", "mock"]
    for provider in providers:
        try:
            return get_completion(provider, prompt)
        except Exception as e:
            logger.warning(f"⚠️ {provider} failed, trying next provider...")
    return ""
