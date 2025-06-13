"""
Diff Engine for SurgiInject
Provides injection previews and diff visualization
"""

import difflib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .injector import run_injection
from .context_builder import inject_with_context
from .file_utils import safe_read_file

logger = logging.getLogger(__name__)


def preview_injection(
    file_path: str, 
    prompt_path: str, 
    with_context: bool = True,
    project_root: Optional[str] = None
) -> Dict[str, Any]:
    """
    Preview injection results without applying changes.
    
    Args:
        file_path: Path to the file to preview injection for
        prompt_path: Path to the prompt template
        with_context: Whether to use context-aware injection
        project_root: Root directory for context analysis
        
    Returns:
        Dict containing before/after content and diff
    """
    file_path = Path(file_path)
    
    # Read original content
    try:
        original_content = safe_read_file(file_path)
        if not original_content:
            return {
                "error": "Could not read file",
                "filename": file_path.name
            }
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return {
            "error": f"File read error: {str(e)}",
            "filename": file_path.name
        }
    
    # Read prompt
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
    except Exception as e:
        logger.error(f"Failed to read prompt {prompt_path}: {e}")
        return {
            "error": f"Prompt read error: {str(e)}",
            "filename": file_path.name
        }
    
    # Generate injection preview
    try:
        if with_context:
            injected_content = inject_with_context(
                file_path=file_path,
                prompt_template=prompt_template,
                project_root=Path(project_root) if project_root else file_path.parent,
                max_context_files=5
            )
        else:
            injected_content = run_injection(
                source_code=original_content,
                prompt_template=prompt_template,
                file_path=str(file_path),
                provider='auto',
                force=False
            )
    except Exception as e:
        logger.error(f"Injection preview failed for {file_path}: {e}")
        return {
            "error": f"Injection failed: {str(e)}",
            "filename": file_path.name
        }
    
    # Generate diff
    diff = generate_unified_diff(original_content, injected_content, file_path.name)
    
    return {
        "filename": file_path.name,
        "filepath": str(file_path),
        "before": original_content,
        "after": injected_content,
        "diff": diff,
        "has_changes": original_content != injected_content,
        "with_context": with_context
    }


def generate_unified_diff(before: str, after: str, filename: str) -> str:
    """
    Generate a unified diff between two strings.
    
    Args:
        before: Original content
        after: Modified content
        filename: Name of the file for diff header
        
    Returns:
        Unified diff string
    """
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=''
    )
    
    return '\n'.join(diff)


def apply_injection(file_path: str, injected_content: str) -> Dict[str, Any]:
    """
    Apply injected content to a file.
    
    Args:
        file_path: Path to the file to modify
        injected_content: Content to write to the file
        
    Returns:
        Dict with success status and details
    """
    file_path = Path(file_path)
    
    try:
        # Create backup
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
        
        # Write new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(injected_content)
        
        return {
            "success": True,
            "filename": file_path.name,
            "backup_created": backup_path.exists(),
            "backup_path": str(backup_path) if backup_path.exists() else None
        }
        
    except Exception as e:
        logger.error(f"Failed to apply injection to {file_path}: {e}")
        return {
            "success": False,
            "error": str(e),
            "filename": file_path.name
        }


def batch_preview_injection(
    files: list, 
    prompt_path: str, 
    with_context: bool = True,
    project_root: Optional[str] = None
) -> Dict[str, Any]:
    """
    Preview injection for multiple files.
    
    Args:
        files: List of file paths
        prompt_path: Path to prompt template
        with_context: Whether to use context
        project_root: Root directory for context
        
    Returns:
        Dict with preview results for each file
    """
    results = []
    
    for file_path in files:
        preview = preview_injection(
            file_path=str(file_path),
            prompt_path=prompt_path,
            with_context=with_context,
            project_root=project_root
        )
        results.append(preview)
    
    return {
        "previews": results,
        "total_files": len(files),
        "files_with_changes": len([r for r in results if r.get('has_changes', False)]),
        "with_context": with_context
    }


def get_diff_stats(diff: str) -> Dict[str, int]:
    """
    Get statistics about a diff.
    
    Args:
        diff: Unified diff string
        
    Returns:
        Dict with line addition/deletion counts
    """
    lines = diff.split('\n')
    additions = 0
    deletions = 0
    
    for line in lines:
        if line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1
    
    return {
        "additions": additions,
        "deletions": deletions,
        "total_changes": additions + deletions
    }


def format_diff_for_display(diff: str) -> str:
    """
    Format diff for HTML/display with syntax highlighting.
    
    Args:
        diff: Raw unified diff
        
    Returns:
        Formatted diff with HTML-like markers
    """
    lines = diff.split('\n')
    formatted_lines = []
    
    for line in lines:
        if line.startswith('+') and not line.startswith('+++'):
            formatted_lines.append(f"<span class='addition'>{line}</span>")
        elif line.startswith('-') and not line.startswith('---'):
            formatted_lines.append(f"<span class='deletion'>{line}</span>")
        elif line.startswith('@@'):
            formatted_lines.append(f"<span class='hunk'>{line}</span>")
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines) 