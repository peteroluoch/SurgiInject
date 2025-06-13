"""
Recursive Engine for SurgiInject
Handles directory-wide injections with smart dependency tracking
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from .injector import run_injection
from .file_utils import is_supported_file, get_file_encoding

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
                
                # Read source file
                with open(file_path, 'r', encoding=get_file_encoding(file_path)) as f:
                    source_code = f.read()
                
                # Run injection using the correct function signature
                modified_code = run_injection(
                    source_code=source_code,
                    prompt_template=prompt_template,
                    file_path=str(file_path),
                    provider='auto',
                    force=False
                )
                
                # Check if injection was successful
                if modified_code and not modified_code.startswith("[Injection failed"):
                    self.injected_files.append({
                        'file': str(file_path),
                        'original': source_code,
                        'modified': modified_code,
                        'success': True
                    })
                    logger.info(f"Success: {file_path}")
                    
                    # Apply changes if requested
                    if apply_changes:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(modified_code)
                        logger.info(f"Applied changes to: {file_path}")
                else:
                    error_msg = modified_code if modified_code.startswith("[Injection failed") else "Unknown error"
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