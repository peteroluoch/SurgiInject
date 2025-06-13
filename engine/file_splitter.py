"""
File Splitter for SurgiInject Phase 6.9
Intelligent file chunking for token-aware injection
"""

import ast
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FileChunk:
    """Represents a chunk of a file"""
    content: str
    start_line: int
    end_line: int
    chunk_type: str  # 'function', 'class', 'section', 'block'
    name: str  # Function/class name or description
    dependencies: List[str] = None

class FileSplitter:
    """Intelligently splits files into manageable chunks"""
    
    def __init__(self, max_chunk_size: int = 100, max_tokens: int = 4000):
        self.max_chunk_size = max_chunk_size  # Lines per chunk
        self.max_tokens = max_tokens  # Approximate tokens per chunk
    
    def split_file(self, file_path: str) -> List[FileChunk]:
        """
        Split a file into logical chunks
        
        Args:
            file_path: Path to the file to split
            
        Returns:
            List of FileChunk objects
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            raise IOError(f"Could not read file {file_path}: {e}")
        
        # Determine split strategy based on file type
        if file_path.suffix == '.py':
            return self._split_python_file(lines, file_path)
        elif file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
            return self._split_javascript_file(lines, file_path)
        elif file_path.suffix in ['.html', '.htm']:
            return self._split_html_file(lines, file_path)
        elif file_path.suffix == '.css':
            return self._split_css_file(lines, file_path)
        else:
            # Generic split for other file types
            return self._split_generic_file(lines, file_path)
    
    def _split_python_file(self, lines: List[str], file_path: Path) -> List[FileChunk]:
        """Split Python file by functions, classes, and logical blocks"""
        chunks = []
        current_chunk = []
        current_start = 1
        current_type = "block"
        current_name = "main"
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check for function definition
            if stripped.startswith('def ') and ':' in stripped:
                # Save previous chunk if it exists
                if current_chunk:
                    chunks.append(FileChunk(
                        content='\n'.join(current_chunk),
                        start_line=current_start,
                        end_line=i,
                        chunk_type=current_type,
                        name=current_name
                    ))
                
                # Start new function chunk
                func_name = self._extract_python_name(stripped)
                current_chunk = [line]
                current_start = i + 1
                current_type = "function"
                current_name = func_name
                
                # Find function end
                i += 1
                indent_level = self._get_indent_level(line)
                
                while i < len(lines):
                    next_line = lines[i]
                    if (next_line.strip() and 
                        self._get_indent_level(next_line) <= indent_level and 
                        not next_line.strip().startswith('#')):
                        break
                    current_chunk.append(next_line)
                    i += 1
                
                # Check if chunk is too large
                if len(current_chunk) > self.max_chunk_size:
                    # Split large function into smaller parts
                    sub_chunks = self._split_large_python_block(current_chunk, current_start)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(FileChunk(
                        content='\n'.join(current_chunk),
                        start_line=current_start,
                        end_line=i,
                        chunk_type=current_type,
                        name=current_name
                    ))
                
                current_chunk = []
                continue
            
            # Check for class definition
            elif stripped.startswith('class ') and ':' in stripped:
                # Save previous chunk if it exists
                if current_chunk:
                    chunks.append(FileChunk(
                        content='\n'.join(current_chunk),
                        start_line=current_start,
                        end_line=i,
                        chunk_type=current_type,
                        name=current_name
                    ))
                
                # Start new class chunk
                class_name = self._extract_python_name(stripped)
                current_chunk = [line]
                current_start = i + 1
                current_type = "class"
                current_name = class_name
                
                # Find class end
                i += 1
                indent_level = self._get_indent_level(line)
                
                while i < len(lines):
                    next_line = lines[i]
                    if (next_line.strip() and 
                        self._get_indent_level(next_line) <= indent_level and 
                        not next_line.strip().startswith('#')):
                        break
                    current_chunk.append(next_line)
                    i += 1
                
                # Check if chunk is too large
                if len(current_chunk) > self.max_chunk_size:
                    # Split large class into methods
                    sub_chunks = self._split_large_python_class(current_chunk, current_start)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(FileChunk(
                        content='\n'.join(current_chunk),
                        start_line=current_start,
                        end_line=i,
                        chunk_type=current_type,
                        name=current_name
                    ))
                
                current_chunk = []
                continue
            
            # Add line to current chunk
            current_chunk.append(line)
            i += 1
            
            # Check if current chunk is getting too large
            if len(current_chunk) >= self.max_chunk_size:
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=i,
                    chunk_type=current_type,
                    name=current_name
                ))
                current_chunk = []
                current_start = i + 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(FileChunk(
                content='\n'.join(current_chunk),
                start_line=current_start,
                end_line=len(lines),
                chunk_type=current_type,
                name=current_name
            ))
        
        return chunks
    
    def _split_javascript_file(self, lines: List[str], file_path: Path) -> List[FileChunk]:
        """Split JavaScript/TypeScript file by functions, classes, and modules"""
        chunks = []
        current_chunk = []
        current_start = 1
        current_type = "block"
        current_name = "main"
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check for function declaration
            if (re.match(r'^(function\s+\w+|const\s+\w+\s*=\s*\(|let\s+\w+\s*=\s*\(|var\s+\w+\s*=\s*\()', stripped) or
                re.match(r'^\w+\s*\([^)]*\)\s*{', stripped)):
                
                # Save previous chunk if it exists
                if current_chunk:
                    chunks.append(FileChunk(
                        content='\n'.join(current_chunk),
                        start_line=current_start,
                        end_line=i,
                        chunk_type=current_type,
                        name=current_name
                    ))
                
                # Start new function chunk
                func_name = self._extract_javascript_name(stripped)
                current_chunk = [line]
                current_start = i + 1
                current_type = "function"
                current_name = func_name
                
                # Find function end
                i += 1
                brace_count = line.count('{') - line.count('}')
                
                while i < len(lines) and brace_count > 0:
                    next_line = lines[i]
                    brace_count += next_line.count('{') - next_line.count('}')
                    current_chunk.append(next_line)
                    i += 1
                
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=i,
                    chunk_type=current_type,
                    name=current_name
                ))
                
                current_chunk = []
                continue
            
            # Check for class declaration
            elif stripped.startswith('class ') and '{' in stripped:
                # Save previous chunk if it exists
                if current_chunk:
                    chunks.append(FileChunk(
                        content='\n'.join(current_chunk),
                        start_line=current_start,
                        end_line=i,
                        chunk_type=current_type,
                        name=current_name
                    ))
                
                # Start new class chunk
                class_name = self._extract_javascript_name(stripped)
                current_chunk = [line]
                current_start = i + 1
                current_type = "class"
                current_name = class_name
                
                # Find class end
                i += 1
                brace_count = line.count('{') - line.count('}')
                
                while i < len(lines) and brace_count > 0:
                    next_line = lines[i]
                    brace_count += next_line.count('{') - next_line.count('}')
                    current_chunk.append(next_line)
                    i += 1
                
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=i,
                    chunk_type=current_type,
                    name=current_name
                ))
                
                current_chunk = []
                continue
            
            # Add line to current chunk
            current_chunk.append(line)
            i += 1
            
            # Check if current chunk is getting too large
            if len(current_chunk) >= self.max_chunk_size:
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=i,
                    chunk_type=current_type,
                    name=current_name
                ))
                current_chunk = []
                current_start = i + 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(FileChunk(
                content='\n'.join(current_chunk),
                start_line=current_start,
                end_line=len(lines),
                chunk_type=current_type,
                name=current_name
            ))
        
        return chunks
    
    def _split_html_file(self, lines: List[str], file_path: Path) -> List[FileChunk]:
        """Split HTML file by sections and logical blocks"""
        chunks = []
        current_chunk = []
        current_start = 1
        current_type = "section"
        current_name = "main"
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check for major HTML sections
            if (re.match(r'^<(section|article|header|footer|nav|main|aside)', stripped, re.IGNORECASE) or
                re.match(r'^<div[^>]*class\s*=\s*[\'"][^\'"]*(section|container|wrapper)[^\'"]*[\'"]', stripped, re.IGNORECASE)):
                
                # Save previous chunk if it exists
                if current_chunk:
                    chunks.append(FileChunk(
                        content='\n'.join(current_chunk),
                        start_line=current_start,
                        end_line=i,
                        chunk_type=current_type,
                        name=current_name
                    ))
                
                # Start new section chunk
                section_name = self._extract_html_section_name(stripped)
                current_chunk = [line]
                current_start = i + 1
                current_type = "section"
                current_name = section_name
                
                # Find section end
                i += 1
                tag_name = re.search(r'<(\w+)', stripped, re.IGNORECASE)
                if tag_name:
                    end_tag = f"</{tag_name.group(1)}>"
                    
                    while i < len(lines):
                        next_line = lines[i]
                        if end_tag in next_line:
                            current_chunk.append(next_line)
                            i += 1
                            break
                        current_chunk.append(next_line)
                        i += 1
                
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=i,
                    chunk_type=current_type,
                    name=current_name
                ))
                
                current_chunk = []
                continue
            
            # Add line to current chunk
            current_chunk.append(line)
            i += 1
            
            # Check if current chunk is getting too large
            if len(current_chunk) >= self.max_chunk_size:
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=i,
                    chunk_type=current_type,
                    name=current_name
                ))
                current_chunk = []
                current_start = i + 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(FileChunk(
                content='\n'.join(current_chunk),
                start_line=current_start,
                end_line=len(lines),
                chunk_type=current_type,
                name=current_name
            ))
        
        return chunks
    
    def _split_css_file(self, lines: List[str], file_path: Path) -> List[FileChunk]:
        """Split CSS file by rulesets and logical blocks"""
        chunks = []
        current_chunk = []
        current_start = 1
        current_type = "ruleset"
        current_name = "main"
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check for CSS ruleset start
            if re.match(r'^[.#]?\w+[^{]*{', stripped):
                # Save previous chunk if it exists
                if current_chunk:
                    chunks.append(FileChunk(
                        content='\n'.join(current_chunk),
                        start_line=current_start,
                        end_line=i,
                        chunk_type=current_type,
                        name=current_name
                    ))
                
                # Start new ruleset chunk
                selector_name = self._extract_css_selector(stripped)
                current_chunk = [line]
                current_start = i + 1
                current_type = "ruleset"
                current_name = selector_name
                
                # Find ruleset end
                i += 1
                brace_count = line.count('{') - line.count('}')
                
                while i < len(lines) and brace_count > 0:
                    next_line = lines[i]
                    brace_count += next_line.count('{') - next_line.count('}')
                    current_chunk.append(next_line)
                    i += 1
                
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=i,
                    chunk_type=current_type,
                    name=current_name
                ))
                
                current_chunk = []
                continue
            
            # Add line to current chunk
            current_chunk.append(line)
            i += 1
            
            # Check if current chunk is getting too large
            if len(current_chunk) >= self.max_chunk_size:
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=i,
                    chunk_type=current_type,
                    name=current_name
                ))
                current_chunk = []
                current_start = i + 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(FileChunk(
                content='\n'.join(current_chunk),
                start_line=current_start,
                end_line=len(lines),
                chunk_type=current_type,
                name=current_name
            ))
        
        return chunks
    
    def _split_generic_file(self, lines: List[str], file_path: Path) -> List[FileChunk]:
        """Generic file splitting for unknown file types"""
        chunks = []
        current_chunk = []
        current_start = 1
        
        for i, line in enumerate(lines):
            current_chunk.append(line)
            
            # Split by size
            if len(current_chunk) >= self.max_chunk_size:
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=i + 1,
                    chunk_type="block",
                    name=f"block_{len(chunks) + 1}"
                ))
                current_chunk = []
                current_start = i + 2
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(FileChunk(
                content='\n'.join(current_chunk),
                start_line=current_start,
                end_line=len(lines),
                chunk_type="block",
                name=f"block_{len(chunks) + 1}"
            ))
        
        return chunks
    
    def _split_large_python_block(self, lines: List[str], start_line: int) -> List[FileChunk]:
        """Split a large Python block into smaller chunks"""
        chunks = []
        current_chunk = []
        current_start = start_line
        
        for i, line in enumerate(lines):
            current_chunk.append(line)
            
            # Split by size or logical boundaries
            if (len(current_chunk) >= self.max_chunk_size // 2 or
                (line.strip().startswith('def ') and len(current_chunk) > 10)):
                
                chunks.append(FileChunk(
                    content='\n'.join(current_chunk),
                    start_line=current_start,
                    end_line=start_line + i,
                    chunk_type="sub_block",
                    name=f"sub_block_{len(chunks) + 1}"
                ))
                current_chunk = []
                current_start = start_line + i + 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(FileChunk(
                content='\n'.join(current_chunk),
                start_line=current_start,
                end_line=start_line + len(lines) - 1,
                chunk_type="sub_block",
                name=f"sub_block_{len(chunks) + 1}"
            ))
        
        return chunks
    
    def _split_large_python_class(self, lines: List[str], start_line: int) -> List[FileChunk]:
        """Split a large Python class into methods"""
        chunks = []
        current_chunk = []
        current_start = start_line
        current_method = "class_init"
        
        for i, line in enumerate(lines):
            current_chunk.append(line)
            
            # Check for method definition
            if line.strip().startswith('def ') and ':' in line:
                # Save previous chunk
                if current_chunk:
                    chunks.append(FileChunk(
                        content='\n'.join(current_chunk),
                        start_line=current_start,
                        end_line=start_line + i - 1,
                        chunk_type="method",
                        name=current_method
                    ))
                
                # Start new method
                method_name = self._extract_python_name(line.strip())
                current_chunk = [line]
                current_start = start_line + i
                current_method = method_name
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(FileChunk(
                content='\n'.join(current_chunk),
                start_line=current_start,
                end_line=start_line + len(lines) - 1,
                chunk_type="method",
                name=current_method
            ))
        
        return chunks
    
    def _get_indent_level(self, line: str) -> int:
        """Get indentation level of a line"""
        return len(line) - len(line.lstrip())
    
    def _extract_python_name(self, line: str) -> str:
        """Extract function/class name from Python definition"""
        match = re.search(r'(?:def|class)\s+(\w+)', line)
        return match.group(1) if match else "unknown"
    
    def _extract_javascript_name(self, line: str) -> str:
        """Extract function/class name from JavaScript definition"""
        # Try different patterns
        patterns = [
            r'function\s+(\w+)',
            r'const\s+(\w+)\s*=',
            r'let\s+(\w+)\s*=',
            r'var\s+(\w+)\s*=',
            r'class\s+(\w+)',
            r'(\w+)\s*\([^)]*\)\s*{'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        
        return "unknown"
    
    def _extract_html_section_name(self, line: str) -> str:
        """Extract section name from HTML tag"""
        # Try to get class name or id
        class_match = re.search(r'class\s*=\s*[\'"]([^\'"]+)[\'"]', line, re.IGNORECASE)
        if class_match:
            return class_match.group(1).split()[0]
        
        id_match = re.search(r'id\s*=\s*[\'"]([^\'"]+)[\'"]', line, re.IGNORECASE)
        if id_match:
            return id_match.group(1)
        
        # Get tag name
        tag_match = re.search(r'<(\w+)', line, re.IGNORECASE)
        if tag_match:
            return tag_match.group(1)
        
        return "section"
    
    def _extract_css_selector(self, line: str) -> str:
        """Extract CSS selector name"""
        # Remove opening brace and get selector
        selector = line.split('{')[0].strip()
        
        # Clean up selector
        selector = re.sub(r'[.#]', '', selector)
        selector = re.sub(r'\s+', '_', selector)
        
        return selector or "selector"


# Global file splitter instance
file_splitter = FileSplitter()


def split_file(file_path: str, max_chunk_size: int = 100, max_tokens: int = 4000) -> List[FileChunk]:
    """Convenience function to split a file"""
    splitter = FileSplitter(max_chunk_size, max_tokens)
    return splitter.split_file(file_path) 