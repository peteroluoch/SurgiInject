"""
Recursive Engine for SurgiInject
Handles directory-wide injections with smart dependency tracking
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from .injector import run_injection, run_injection_from_files
from .file_utils import (
    is_supported_file, 
    get_file_encoding, 
    file_contains_marker, 
    add_marker_to_content,
    is_meaningful_response,
    safe_write_file
)

logger = logging.getLogger(__name__)

class RecursiveInjector:
    """Handles recursive directory injections with context awareness"""
    
    def __init__(self):
        self.injected_files = []
        self.failed_files = []
        self.dependency_map = {}
        
    def inject_directory(
        self, 
        directory_path: str, 
        prompt_path: str, 
        extensions: List[str] = [".py", ".html", ".js", ".css", ".txt"],
        recursive: bool = True,
        apply_changes: bool = False,
        verbose: bool = False
    ) -> Dict[str, any]:
        """
        Inject AI modifications into all files in a directory
        
        Args:
            directory_path: Path to directory to process
            prompt_path: Path to prompt template file
            extensions: List of file extensions to process
            recursive: Whether to process subdirectories
            apply_changes: Whether to apply changes or just show diff
            verbose: Enable verbose logging
            
        Returns:
            Dict containing results and statistics
        """
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
            
        logger.info(f"Starting recursive injection in: {directory_path}")
        logger.info(f"Extensions: {extensions}")
        logger.info(f"Recursive: {recursive}")
        
        # Reset state
        self.injected_files = []
        self.failed_files = []
        
        # Read prompt template
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except Exception as e:
            raise FileNotFoundError(f"Could not read prompt file {prompt_path}: {e}")
        
        # Process files
        for file_path in self._get_files_to_process(directory, extensions, recursive):
            try:
                logger.info(f"Processing: {file_path}")
                
                # Check if file is already injected
                if file_contains_marker(file_path):
                    logger.info(f"Skipping already-injected file: {file_path}")
                    continue
                
                # Read source file
                with open(file_path, 'r', encoding=get_file_encoding(file_path)) as f:
                    source_code = f.read()
                
                # Skip empty files
                if not source_code.strip():
                    logger.info(f"Skipping empty file: {file_path}")
                    continue
                
                # Run injection using the correct function signature
                modified_code = run_injection(
                    source_code=source_code,
                    prompt_template=prompt_template,
                    file_path=str(file_path),
                    provider='auto',
                    force=False
                )
                
                # Check if injection was successful and meaningful
                if is_meaningful_response(modified_code):
                    # Add marker to the modified content
                    marked_content = add_marker_to_content(modified_code, file_path)
                    
                    self.injected_files.append({
                        'file': str(file_path),
                        'original': source_code,
                        'modified': marked_content,
                        'success': True
                    })
                    logger.info(f"Success: {file_path}")
                    
                    # Apply changes if requested
                    if apply_changes:
                        if safe_write_file(file_path, marked_content):
                            logger.info(f"Applied changes to: {file_path}")
                        else:
                            logger.error(f"Failed to write changes to: {file_path}")
                            self.failed_files.append({
                                'file': str(file_path),
                                'error': 'Failed to write file'
                            })
                else:
                    error_msg = "AI response was not meaningful or contained errors"
                    self.failed_files.append({
                        'file': str(file_path),
                        'error': error_msg
                    })
                    logger.error(f"Failed: {file_path} - {error_msg}")
                    
            except Exception as e:
                error_msg = f"Exception processing {file_path}: {str(e)}"
                logger.error(error_msg)
                self.failed_files.append({
                    'file': str(file_path),
                    'error': error_msg
                })
        
        # Build results summary
        results = {
            'total_files': len(self.injected_files) + len(self.failed_files),
            'successful': len(self.injected_files),
            'failed': len(self.failed_files),
            'injected_files': self.injected_files,
            'failed_files': self.failed_files,
            'directory': directory_path,
            'prompt': prompt_path
        }
        
        logger.info(f"Injection complete: {results['successful']}/{results['total_files']} files processed")
        return results
    
    def _get_files_to_process(
        self, 
        directory: Path, 
        extensions: List[str], 
        recursive: bool
    ) -> List[Path]:
        """Get list of files to process based on criteria"""
        files = []
        
        if recursive:
            # Walk through all subdirectories
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = Path(root) / filename
                    if is_supported_file(filename, extensions):
                        files.append(file_path)
        else:
            # Only process files in the specified directory
            for item in directory.iterdir():
                if item.is_file() and is_supported_file(item.name, extensions):
                    files.append(item)
        
        return sorted(files)
    
    def analyze_dependencies(self, directory: str) -> Dict[str, List[str]]:
        """
        Analyze file dependencies in a directory
        This is a foundation for future context-aware injections
        """
        dependency_map = {}
        directory_path = Path(directory)
        
        for file_path in directory_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.html', '.js']:
                dependencies = self._extract_dependencies(file_path)
                if dependencies:
                    dependency_map[str(file_path)] = dependencies
        
        self.dependency_map = dependency_map
        return dependency_map
    
    def _extract_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from a single file"""
        dependencies = []
        
        try:
            encoding = get_file_encoding(file_path)
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # Python imports
            if file_path.suffix == '.py':
                import_lines = [line.strip() for line in content.split('\n') 
                              if line.strip().startswith(('import ', 'from '))]
                dependencies.extend(import_lines)
            
            # HTML includes/scripts
            elif file_path.suffix == '.html':
                # Look for script src, link href, etc.
                import re
                script_srcs = re.findall(r'src=["\']([^"\']+)["\']', content)
                link_hrefs = re.findall(r'href=["\']([^"\']+)["\']', content)
                dependencies.extend(script_srcs + link_hrefs)
            
            # JavaScript imports
            elif file_path.suffix == '.js':
                import_lines = [line.strip() for line in content.split('\n') 
                              if line.strip().startswith(('import ', 'require('))]
                dependencies.extend(import_lines)
                
        except Exception as e:
            logger.warning(f"Could not analyze dependencies for {file_path}: {e}")
        
        return dependencies

def inject_directory(
    directory_path: str,
    prompt_path: str,
    extensions: List[str] = [".py", ".html", ".js", ".css", ".txt"],
    recursive: bool = True,
    apply_changes: bool = False,
    verbose: bool = False
) -> Dict[str, any]:
    """Convenience function for directory injection"""
    injector = RecursiveInjector()
    return injector.inject_directory(
        directory_path=directory_path,
        prompt_path=prompt_path,
        extensions=extensions,
        recursive=recursive,
        apply_changes=apply_changes,
        verbose=verbose
    )

def file_contains_marker(file_path: Path, marker: str = "# Injected by SurgiInject") -> bool:
    """Legacy function for backward compatibility"""
    from .file_utils import file_contains_marker as new_file_contains_marker
    return new_file_contains_marker(file_path)

def inject_dir(
    path: str,
    prompt_path: str,
    extensions: List[str] = [".py", ".html", ".js"],
    recursive: bool = True
) -> Dict[str, List[str]]:
    """
    Enhanced inject_dir function with marker logic and meaningful response checking
    """
    injected = []
    skipped = []
    failed = []
    base = Path(path)
    
    if not base.exists():
        logger.error(f"Directory not found: {path}")
        return {"injected": injected, "skipped": skipped, "failed": failed}
    
    files = []
    if recursive:
        for root, _, filenames in os.walk(base):
            for fname in filenames:
                fpath = Path(root) / fname
                if is_supported_file(fname, extensions):
                    files.append(fpath)
    else:
        for item in base.iterdir():
            if item.is_file() and is_supported_file(item.name, extensions):
                files.append(item)
    
    for file_path in sorted(files):
        try:
            # Check if already injected
            if file_contains_marker(file_path):
                logger.info(f"Skipping already-injected file: {file_path}")
                skipped.append(str(file_path))
                continue
            
            # Read original content
            with open(file_path, 'r', encoding=get_file_encoding(file_path)) as f:
                original_content = f.read()
            
            # Skip empty files
            if not original_content.strip():
                logger.info(f"Skipping empty file: {file_path}")
                continue
            
            logger.info(f"Injecting: {file_path}")
            result = run_injection_from_files(str(file_path), prompt_path)
            
            # Check if response is meaningful
            if is_meaningful_response(result):
                # Add marker and write
                marked_result = add_marker_to_content(result, file_path)
                if safe_write_file(file_path, marked_result, backup=True):
                    injected.append(str(file_path))
                    logger.info(f"Successfully injected: {file_path}")
                else:
                    failed.append(str(file_path))
                    logger.error(f"Failed to write: {file_path}")
            else:
                failed.append(str(file_path))
                logger.error(f"Meaningless response for: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to inject {file_path}: {e}")
            failed.append(str(file_path))
    
    return {"injected": injected, "skipped": skipped, "failed": failed} 