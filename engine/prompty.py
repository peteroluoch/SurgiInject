"""
Prompt template builder for SurgiInject

Formats prompts for AI models with consistent structure and context.
"""

import os
from typing import Dict, Optional
from .parser import parse_file_structure

def build_prompt(file_path: str, code: str, task: str) -> str:
    """
    Build a formatted prompt for AI model consumption.
    
    Args:
        file_path (str): Path to the source file
        code (str): Source code content
        task (str): Task description/prompt template
        
    Returns:
        str: Formatted prompt string
    """
    
    # Get file analysis for additional context
    try:
        analysis = parse_file_structure(file_path, code)
        language = analysis.get('language', 'unknown')
        stats = analysis.get('stats', {})
        functions = analysis.get('functions', [])
        classes = analysis.get('classes', [])
    except Exception:
        # Fallback if parsing fails
        language = 'unknown'
        stats = {}
        functions = []
        classes = []
    
    # Build context section
    context_lines = []
    
    if language != 'unknown':
        context_lines.append(f"Language: {language}")
    
    if stats:
        context_lines.append(f"File size: {stats.get('total_lines', 0)} lines, {stats.get('character_count', 0)} characters")
    
    if functions:
        func_names = [f['name'] for f in functions[:5]]  # Show first 5 functions
        context_lines.append(f"Functions: {', '.join(func_names)}" + ("..." if len(functions) > 5 else ""))
    
    if classes:
        class_names = [c['name'] for c in classes[:3]]  # Show first 3 classes
        context_lines.append(f"Classes: {', '.join(class_names)}" + ("..." if len(classes) > 3 else ""))
    
    context_info = "\n".join(context_lines) if context_lines else "No additional context available"
    
    # Format the complete prompt
    prompt = f"""📄 FILE: {file_path}
🧠 TASK: Code modification and enhancement
💬 CONTEXT:
{context_info}

📋 SOURCE CODE:
```{language}
{code}
