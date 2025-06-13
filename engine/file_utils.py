"""
File utilities for SurgiInject
Handles file scanning, extension filtering, and safe file operations
"""

import os
import chardet
from pathlib import Path
from typing import List, Optional

# Marker constants for different file types
PYTHON_MARKER = "# Injected by SurgiInject"
HTML_MARKER = "<!-- Injected by SurgiInject -->"
JS_MARKER = "// Injected by SurgiInject"

def get_marker_for_file(file_path: Path) -> str:
    """
    Get the appropriate marker for a file based on its extension
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Appropriate marker string for the file type
    """
    ext = file_path.suffix.lower()
    if ext == '.py':
        return PYTHON_MARKER
    elif ext in ['.html', '.htm']:
        return HTML_MARKER
    elif ext in ['.js', '.ts', '.jsx', '.tsx']:
        return JS_MARKER
    else:
        return PYTHON_MARKER  # Default fallback

def file_contains_marker(file_path: Path) -> bool:
    """
    Check if a file contains the appropriate injection marker
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        bool: True if file contains marker, False otherwise
    """
    try:
        marker = get_marker_for_file(file_path)
        with open(file_path, 'r', encoding=get_file_encoding(file_path)) as f:
            content = f.read()
            return marker in content
    except Exception as e:
        print(f"Warning: Could not check marker in {file_path}: {e}")
        return False

def add_marker_to_content(content: str, file_path: Path) -> str:
    """
    Add the appropriate marker to the beginning of file content
    
    Args:
        content: Original file content
        file_path: Path to the file (for determining marker type)
        
    Returns:
        str: Content with marker prepended
    """
    marker = get_marker_for_file(file_path)
    if marker not in content:
        return marker + "\n" + content
    return content

def is_meaningful_response(response: str) -> bool:
    """
    Check if AI response is meaningful and should be applied
    
    Args:
        response: AI response to check
        
    Returns:
        bool: True if response is meaningful, False otherwise
    """
    if not response or not response.strip():
        return False
    
    # Skip if response is just whitespace or error messages
    response_lower = response.lower().strip()
    if response_lower in ['', 'none', 'null', 'undefined']:
        return False
    
    # Skip if response contains error indicators
    error_indicators = ['error:', 'failed:', 'exception:', '[injection failed']
    if any(indicator in response_lower for indicator in error_indicators):
        return False
    
    return True

def is_supported_file(filename: str, extensions: List[str]) -> bool:
    """
    Check if a file should be processed based on its extension
    
    Args:
        filename: Name of the file to check
        extensions: List of supported file extensions (e.g., ['.py', '.html'])
        
    Returns:
        True if file should be processed, False otherwise
    """
    if not extensions:
        return True
    
    file_ext = Path(filename).suffix.lower()
    return file_ext in [ext.lower() for ext in extensions]

def get_file_encoding(file_path: Path) -> str:
    """
    Detect the encoding of a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Detected encoding (defaults to 'utf-8' if detection fails)
    """
    try:
        # Read a sample of the file to detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
        
        if not raw_data:
            return 'utf-8'
        
        # Detect encoding
        result = chardet.detect(raw_data)
        encoding = result.get('encoding', 'utf-8')
        
        # Validate encoding by trying to decode
        try:
            raw_data.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            return 'utf-8'
            
    except Exception:
        return 'utf-8'

def safe_read_file(file_path: Path) -> Optional[str]:
    """
    Safely read a file with proper encoding detection
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        File content as string, or None if reading fails
    """
    try:
        encoding = get_file_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def safe_write_file(file_path: Path, content: str, backup: bool = True) -> bool:
    """
    Safely write content to a file with optional backup
    
    Args:
        file_path: Path to the file to write
        content: Content to write
        backup: Whether to create a backup of the original file
        
    Returns:
        True if write was successful, False otherwise
    """
    try:
        # Create backup if requested and file exists
        if backup and file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            with open(file_path, 'r', encoding=get_file_encoding(file_path)) as f:
                original_content = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
        
        # Write new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return False

def get_file_stats(file_path: Path) -> dict:
    """
    Get basic statistics about a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file statistics
    """
    try:
        stat = file_path.stat()
        return {
            'size': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified': stat.st_mtime,
            'created': stat.st_ctime
        }
    except Exception as e:
        print(f"Error getting stats for {file_path}: {e}")
        return {}

def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in MB
    """
    try:
        return file_path.stat().st_size / (1024 * 1024)
    except Exception as e:
        print(f"Error getting size for {file_path}: {e}")
        return 0.0

def load_prompt(prompt_path: str) -> str:
    """
    Load prompt text from a file with proper encoding detection
    
    Args:
        prompt_path: Path to the prompt file
        
    Returns:
        Prompt text as string
        
    Raises:
        FileNotFoundError: If prompt file doesn't exist
        Exception: If file cannot be read
    """
    prompt_file = Path(prompt_path)
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    try:
        encoding = get_file_encoding(prompt_file)
        with open(prompt_file, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Could not read prompt file {prompt_path}: {e}")

def save_output(original_path: str, response: str) -> str:
    """
    Save injection response to a .surgiout file
    
    Args:
        original_path: Path to the original file
        response: AI response to save
        
    Returns:
        Path to the saved output file
    """
    try:
        out_path = f"{original_path}.surgiout"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response)
        return out_path
    except Exception as e:
        print(f"Error saving output to {out_path}: {e}")
        raise

def filter_files_by_size(files: List[Path], max_size_mb: float = 10.0) -> List[Path]:
    """
    Filter files by maximum size to avoid processing very large files
    
    Args:
        files: List of file paths
        max_size_mb: Maximum file size in MB
        
    Returns:
        Filtered list of files
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    return [f for f in files if f.stat().st_size <= max_size_bytes]

def is_binary_file(file_path: Path) -> bool:
    """
    Check if a file is binary (should be skipped for text processing)
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file appears to be binary
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\x00' in chunk
    except Exception:
        return False

def get_project_files(
    root_path: Path,
    extensions: List[str] = None,
    exclude_dirs: List[str] = None,
    max_size_mb: float = 10.0
) -> List[Path]:
    """
    Get all project files matching criteria
    
    Args:
        root_path: Root directory to search
        extensions: File extensions to include (None for all)
        exclude_dirs: Directory names to exclude (e.g., ['__pycache__', '.git'])
        max_size_mb: Maximum file size in MB
        
    Returns:
        List of matching file paths
    """
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', '.venv', 'node_modules', '.pytest_cache']
    
    files = []
    
    for file_path in root_path.rglob('*'):
        if file_path.is_file():
            # Skip binary files
            if is_binary_file(file_path):
                continue
            
            # Skip excluded directories
            if any(exclude_dir in file_path.parts for exclude_dir in exclude_dirs):
                continue
            
            # Check extension filter
            if extensions and not is_supported_file(file_path.name, extensions):
                continue
            
            # Check size limit
            if file_path.stat().st_size > max_size_mb * 1024 * 1024:
                continue
            
            files.append(file_path)
    
    return sorted(files) 