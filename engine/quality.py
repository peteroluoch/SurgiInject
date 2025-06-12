"""
Quality assessment module for SurgiInject

Evaluates AI model responses and determines if escalation is needed.
"""

import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

def is_response_weak(response: str) -> bool:
    """
    Determine if an AI response is weak and needs escalation.
    
    Args:
        response (str): AI model response to evaluate
        
    Returns:
        bool: True if response is weak, False if acceptable
    """
    if not response or not response.strip():
        return True
    
    response_lower = response.lower()
    
    # Check for explicit no-change indicators
    weak_indicators = [
        "no change",
        "no changes needed",
        "already correct",
        "looks good",
        "no issues found",
        "cannot be improved",
        "nothing to fix"
    ]
    
    for indicator in weak_indicators:
        if indicator in response_lower:
            logger.warning(f"Weak response detected: contains '{indicator}'")
            return True
    
    # Check for minimal content (too short)
    if len(response.strip()) < 50:
        logger.warning(f"Weak response detected: too short ({len(response.strip())} chars)")
        return True
    
    # Check for error messages or API failures
    error_indicators = [
        "error:",
        "failed to",
        "unable to",
        "cannot process",
        "api error",
        "timeout",
        "invalid request"
    ]
    
    for error in error_indicators:
        if error in response_lower:
            logger.warning(f"Weak response detected: contains error '{error}'")
            return True
    
    return False

def assess_code_quality(original: str, modified: str) -> Dict[str, any]:
    """
    Assess the quality of code modifications.
    
    Args:
        original (str): Original source code
        modified (str): Modified source code
        
    Returns:
        Dict: Quality assessment metrics
    """
    assessment = {
        'length_change_ratio': 0.0,
        'has_meaningful_changes': False,
        'syntax_indicators': [],
        'improvement_indicators': [],
        'quality_score': 0.0
    }
    
    if not original or not modified:
        return assessment
    
    # Calculate length change ratio
    assessment['length_change_ratio'] = len(modified) / len(original) if len(original) > 0 else 0
    
    # Check for meaningful changes
    original_lines = set(original.strip().split('\n'))
    modified_lines = set(modified.strip().split('\n'))
    
    if original_lines != modified_lines:
        assessment['has_meaningful_changes'] = True
    
    # Look for improvement indicators
    improvement_patterns = [
        r'try\s*:',  # Error handling
        r'except\s+\w+',  # Exception handling
        r'if\s+.*\s+is\s+None',  # Null checks
        r'assert\s+',  # Assertions
        r'logging\.',  # Logging
        r'validate\w*\(',  # Validation functions
        r'# TODO|# FIXME|# NOTE',  # Documentation improvements
        r'def\s+test_',  # Test functions
        r'@\w+',  # Decorators
        r'async\s+def',  # Async improvements
    ]
    
    for pattern in improvement_patterns:
        if re.search(pattern, modified, re.IGNORECASE) and not re.search(pattern, original, re.IGNORECASE):
            assessment['improvement_indicators'].append(pattern)
    
    # Calculate quality score
    base_score = 0.5
    
    if assessment['has_meaningful_changes']:
        base_score += 0.2
    
    if assessment['improvement_indicators']:
        base_score += 0.2 * min(len(assessment['improvement_indicators']), 2)
    
    if 0.8 <= assessment['length_change_ratio'] <= 1.5:
        base_score += 0.1  # Reasonable size change
    
    assessment['quality_score'] = min(base_score, 1.0)
    
    return assessment

def should_escalate(response: str, original_code: str = "", modified_code: str = "") -> bool:
    """
    Determine if response should be escalated to a higher-tier model.
    
    Args:
        response (str): AI model response
        original_code (str): Original source code
        modified_code (str): Modified source code
        
    Returns:
        bool: True if escalation is recommended
    """
    if is_response_weak(response):
        return True
    
    if original_code and modified_code:
        quality = assess_code_quality(original_code, modified_code)
        if quality['quality_score'] < 0.6:
            logger.info(f"Low quality score: {quality['quality_score']:.2f}, recommending escalation")
            return True
    
    return False

def get_escalation_prompt(original_prompt: str, weak_response: str) -> str:
    """
    Generate an enhanced prompt for escalation to a higher-tier model.
    
    Args:
        original_prompt (str): The original prompt that produced weak results
        weak_response (str): The weak response that triggered escalation
        
    Returns:
        str: Enhanced prompt for escalation
    """
    escalation_prompt = f"""
ESCALATION REQUEST - Previous response was insufficient

ORIGINAL PROMPT:
{original_prompt}

WEAK RESPONSE RECEIVED:
{weak_response[:500]}...

ENHANCED REQUIREMENTS:
- Provide comprehensive code modifications
- Include detailed explanations for changes
- Add error handling and edge cases
- Ensure production-ready quality
- Include comments explaining improvements

Please provide a significantly improved response that addresses the original requirements with higher quality and more thorough implementation.
"""
    
    return escalation_prompt