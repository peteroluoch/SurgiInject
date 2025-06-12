"""
Code parsing utilities for SurgiInject

Handles analysis and parsing of source code files to extract context
and structure information for better AI prompt generation.
"""

import re
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class CodeParser:
    """Parser for extracting metadata and structure from source code"""
    
    def __init__(self):
        self.language_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
            '.sh': 'bash',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.xml': 'xml'
        }
    
    def detect_language(self, file_path: str) -> str:
        """
        Detect programming language from file extension.
        
        Args:
            file_path (str): Path to the source file
            
        Returns:
            str: Detected language or 'unknown'
        """
        ext = Path(file_path).suffix.lower()
        return self.language_extensions.get(ext, 'unknown')
    
    def extract_functions(self, code: str, language: str) -> List[Dict[str, str]]:
        """
        Extract function definitions from code.
        
        Args:
            code (str): Source code content
            language (str): Programming language
            
        Returns:
            List[Dict]: List of function metadata
        """
        functions = []
        
        if language == 'python':
            # Python function pattern
            pattern = r'def\s+(\w+)\s*\([^)]*\):'
            matches = re.finditer(pattern, code, re.MULTILINE)
            for match in matches:
                functions.append({
                    'name': match.group(1),
                    'line': code[:match.start()].count('\n') + 1,
                    'type': 'function'
                })
        
        elif language in ['javascript', 'typescript']:
            # JavaScript/TypeScript function patterns
            patterns = [
                r'function\s+(\w+)\s*\(',  # function name()
                r'(\w+)\s*=\s*function',   # name = function
                r'(\w+)\s*=\s*\([^)]*\)\s*=>',  # name = () =>
                r'(\w+)\s*\([^)]*\)\s*{',  # name() { (method)
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, code, re.MULTILINE)
                for match in matches:
                    functions.append({
                        'name': match.group(1),
                        'line': code[:match.start()].count('\n') + 1,
                        'type': 'function'
                    })
        
        return functions
    
    def extract_classes(self, code: str, language: str) -> List[Dict[str, str]]:
        """
        Extract class definitions from code.
        
        Args:
            code (str): Source code content
            language (str): Programming language
            
        Returns:
            List[Dict]: List of class metadata
        """
        classes = []
        
        if language == 'python':
            pattern = r'class\s+(\w+)(?:\([^)]*\))?:'
            matches = re.finditer(pattern, code, re.MULTILINE)
            for match in matches:
                classes.append({
                    'name': match.group(1),
                    'line': code[:match.start()].count('\n') + 1,
                    'type': 'class'
                })
        
        elif language in ['javascript', 'typescript', 'java', 'csharp']:
            pattern = r'class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*{'
            matches = re.finditer(pattern, code, re.MULTILINE)
            for match in matches:
                classes.append({
                    'name': match.group(1),
                    'line': code[:match.start()].count('\n') + 1,
                    'type': 'class'
                })
        
        return classes
    
    def extract_imports(self, code: str, language: str) -> List[str]:
        """
        Extract import/include statements from code.
        
        Args:
            code (str): Source code content
            language (str): Programming language
            
        Returns:
            List[str]: List of imported modules/libraries
        """
        imports = []
        
        if language == 'python':
            # Python imports
            patterns = [
                r'import\s+([\w.]+)',
                r'from\s+([\w.]+)\s+import',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, code, re.MULTILINE)
                imports.extend(matches)
        
        elif language in ['javascript', 'typescript']:
            # JavaScript/TypeScript imports
            patterns = [
                r'import.*from\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, code, re.MULTILINE)
                imports.extend(matches)
        
        return list(set(imports))  # Remove duplicates
    
    def get_code_stats(self, code: str) -> Dict[str, int]:
        """
        Get basic statistics about the code.
        
        Args:
            code (str): Source code content
            
        Returns:
            Dict[str, int]: Code statistics
        """
        lines = code.split('\n')
        
        return {
            'total_lines': len(lines),
            'non_empty_lines': len([line for line in lines if line.strip()]),
            'comment_lines': len([line for line in lines if line.strip().startswith('#') or line.strip().startswith('//')]),
            'character_count': len(code),
            'word_count': len(code.split())
        }
    
    def analyze_file(self, file_path: str, code: str) -> Dict:
        """
        Perform comprehensive analysis of a source code file.
        
        Args:
            file_path (str): Path to the source file
            code (str): Source code content
            
        Returns:
            Dict: Complete analysis results
        """
        language = self.detect_language(file_path)
        
        analysis = {
            'file_path': file_path,
            'language': language,
            'stats': self.get_code_stats(code),
            'functions': self.extract_functions(code, language),
            'classes': self.extract_classes(code, language),
            'imports': self.extract_imports(code, language)
        }
        
        return analysis

def parse_file_structure(file_path: str, code: str) -> Dict:
    """
    Convenience function to parse file structure.
    
    Args:
        file_path (str): Path to the source file
        code (str): Source code content
        
    Returns:
        Dict: Parsed structure information
    """
    parser = CodeParser()
    return parser.analyze_file(file_path, code)
