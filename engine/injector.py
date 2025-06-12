"""
Core injection engine for SurgiInject

Handles the main injection workflow:
1. Format prompt using prompty module
2. Send to AI model
3. Return modified code
"""

import logging
from typing import Optional
from .prompty import build_prompt
from models.mistral_client import run_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_injection(source_code: str, prompt_template: str, file_path: Optional[str] = None) -> str:
    """
    Run the complete injection workflow.
    
    Args:
        source_code (str): The original source code to modify
        prompt_template (str): The prompt template content
        file_path (str, optional): Path to the source file for context
        
    Returns:
        str: Modified source code
        
    Raises:
        Exception: If any step in the injection process fails
    """
    try:
        logger.info("Starting injection process...")
        
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
        
        # Step 2: Send to AI model
        logger.info("Sending to AI model...")
        modified_code = run_model(formatted_prompt)
        
        logger.info("AI model processing completed")
        
        # Step 3: Validate output
        if not modified_code:
            logger.warning("AI model returned empty response, returning original code")
            return source_code
            
        logger.info("Injection process completed successfully")
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
