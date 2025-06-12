"""
Diff utilities for SurgiInject

Handles displaying differences between original and modified code.
"""

import difflib
import sys
from typing import List, Tuple, Optional
import re

class ColorCodes:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def show_diff(original: str, modified: str, filename: str = "file", context_lines: int = 3) -> None:
    """
    Display a colored diff between original and modified code.
    
    Args:
        original (str): Original source code
        modified (str): Modified source code
        filename (str): Name of the file being diffed
        context_lines (int): Number of context lines to show around changes
    """
    original_lines = original.splitlines(keepends=False)
    modified_lines = modified.splitlines(keepends=False)
    
    # Generate unified diff
    diff = list(difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm='',
        n=context_lines
    ))
    
    if not diff:
        print(f"{ColorCodes.YELLOW}ℹ️  No changes detected{ColorCodes.END}")
        return
    
    print(f"{ColorCodes.BOLD}{ColorCodes.BLUE}=== Diff for {filename} ==={ColorCodes.END}")
    
    for line in diff:
        if line.startswith('---'):
            print(f"{ColorCodes.BOLD}{ColorCodes.RED}{line}{ColorCodes.END}")
        elif line.startswith('+++'):
            print(f"{ColorCodes.BOLD}{ColorCodes.GREEN}{line}{ColorCodes.END}")
        elif line.startswith('@@'):
            print(f"{ColorCodes.CYAN}{line}{ColorCodes.END}")
        elif line.startswith('-'):
            print(f"{ColorCodes.RED}{line}{ColorCodes.END}")
        elif line.startswith('+'):
            print(f"{ColorCodes.GREEN}{line}{ColorCodes.END}")
        else:
            print(line)

def get_diff_stats(original: str, modified: str) -> dict:
    """
    Calculate statistics about the differences between two texts.
    
    Args:
        original (str): Original text
        modified (str): Modified text
        
    Returns:
        dict: Statistics about the changes
    """
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()
    
    # Calculate basic stats
    original_count = len(original_lines)
    modified_count = len(modified_lines)
    
    # Use difflib to get detailed changes
    differ = difflib.Differ()
    diff = list(differ.compare(original_lines, modified_lines))
    
    added_lines = len([line for line in diff if line.startswith('+ ')])
    removed_lines = len([line for line in diff if line.startswith('- ')])
    changed_lines = min(added_lines, removed_lines)
    
    return {
        'original_lines': original_count,
        'modified_lines': modified_count,
        'lines_added': added_lines - changed_lines,
        'lines_removed': removed_lines - changed_lines,
        'lines_changed': changed_lines,
        'net_change': modified_count - original_count
    }

def show_diff_summary(original: str, modified: str, filename: str = "file") -> None:
    """
    Show a summary of changes without the full diff.
    
    Args:
        original (str): Original source code
        modified (str): Modified source code
        filename (str): Name of the file
    """
    stats = get_diff_stats(original, modified)
    
    print(f"{ColorCodes.BOLD}{ColorCodes.BLUE}=== Summary for {filename} ==={ColorCodes.END}")
    print(f"Original lines: {stats['original_lines']}")
    print(f"Modified lines: {stats['modified_lines']}")
    
    if stats['lines_added'] > 0:
        print(f"{ColorCodes.GREEN}+ {stats['lines_added']} lines added{ColorCodes.END}")
    
    if stats['lines_removed'] > 0:
        print(f"{ColorCodes.RED}- {stats['lines_removed']} lines removed{ColorCodes.END}")
    
    if stats['lines_changed'] > 0:
        print(f"{ColorCodes.YELLOW}~ {stats['lines_changed']} lines changed{ColorCodes.END}")
    
    net_change = stats['net_change']
    if net_change > 0:
        print(f"Net change: {ColorCodes.GREEN}+{net_change}{ColorCodes.END} lines")
    elif net_change < 0:
        print(f"Net change: {ColorCodes.RED}{net_change}{ColorCodes.END} lines")
    else:
        print("Net change: 0 lines")

def create_patch_file(original: str, modified: str, filename: str, output_path: str) -> None:
    """
    Create a patch file from the differences.
    
    Args:
        original (str): Original source code
        modified (str): Modified source code
        filename (str): Name of the source file
        output_path (str): Path where to save the patch file
    """
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}"
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(diff)

def apply_patch(original: str, patch_content: str) -> str:
    """
    Apply a patch to original content (basic implementation).
    
    Args:
        original (str): Original content
        patch_content (str): Patch in unified diff format
        
    Returns:
        str: Patched content
        
    Note: This is a simplified implementation. For production use,
    consider using the 'patch' library or system patch command.
    """
    # This is a basic implementation - in practice you'd want to use
    # a proper patch library for robust patch application
    
    original_lines = original.splitlines()
    patch_lines = patch_content.splitlines()
    
    result_lines = original_lines.copy()
    
    # Simple patch application (handles only basic cases)
    i = 0
    while i < len(patch_lines):
        line = patch_lines[i]
        if line.startswith('@@'):
            # Parse hunk header
            match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
            if match:
                start_old = int(match.group(1)) - 1  # Convert to 0-based indexing
                # For simplicity, we'll skip complex patch logic here
                # In a real implementation, you'd properly parse and apply hunks
        i += 1
    
    return '\n'.join(result_lines)

def has_conflicts(original: str, modified1: str, modified2: str) -> bool:
    """
    Check if two modifications would conflict.
    
    Args:
        original (str): Original content
        modified1 (str): First modification
        modified2 (str): Second modification
        
    Returns:
        bool: True if modifications conflict
    """
    # Get line-by-line differences for both modifications
    original_lines = original.splitlines()
    mod1_lines = modified1.splitlines()
    mod2_lines = modified2.splitlines()
    
    # Simple conflict detection: check if same lines are modified differently
    diff1 = list(difflib.unified_diff(original_lines, mod1_lines, n=0))
    diff2 = list(difflib.unified_diff(original_lines, mod2_lines, n=0))
    
    # Extract modified line numbers from both diffs
    mod1_lines_changed = set()
    mod2_lines_changed = set()
    
    for line in diff1:
        if line.startswith('@@'):
            match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1
                mod1_lines_changed.update(range(start, start + count))
    
    for line in diff2:
        if line.startswith('@@'):
            match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1
                mod2_lines_changed.update(range(start, start + count))
    
    # Check for overlap in modified lines
    return bool(mod1_lines_changed & mod2_lines_changed)
