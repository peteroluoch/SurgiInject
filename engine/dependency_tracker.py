"""
Dependency Tracker for SurgiInject Phase 6.9
Intelligent file relationship analysis and cross-file coordination
"""

import ast
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict, deque
import graphlib
from datetime import datetime

logger = logging.getLogger(__name__)

class DependencyTracker:
    """Tracks file dependencies and manages injection order"""
    
    def __init__(self):
        self.dependency_graph = {}
        self.reverse_graph = defaultdict(set)
        self.file_metadata = {}
        self.injection_order = []
        self.context_cache = {}
        
    def build_dependency_graph(self, folder_path: str, extensions: List[str] = None) -> Dict[str, List[str]]:
        """
        Build dependency graph for all files in a folder
        
        Args:
            folder_path: Root folder to analyze
            extensions: File extensions to include (default: all supported)
            
        Returns:
            Dictionary mapping files to their dependencies
        """
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.html', '.css', '.md', '.txt']
        
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        logger.info(f"Building dependency graph for: {folder_path}")
        
        # Reset state
        self.dependency_graph = {}
        self.reverse_graph = defaultdict(set)
        self.file_metadata = {}
        
        # Find all source files
        source_files = self._find_source_files(folder, extensions)
        logger.info(f"Found {len(source_files)} source files")
        
        # Analyze dependencies for each file
        for file_path in source_files:
            try:
                dependencies = self._extract_dependencies(file_path)
                self.dependency_graph[str(file_path)] = dependencies
                
                # Build reverse graph for context resolution
                for dep in dependencies:
                    self.reverse_graph[dep].add(str(file_path))
                
                # Store file metadata
                self.file_metadata[str(file_path)] = {
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime,
                    'extension': file_path.suffix,
                    'dependencies': dependencies
                }
                
            except Exception as e:
                logger.error(f"Failed to analyze dependencies for {file_path}: {e}")
                self.dependency_graph[str(file_path)] = []
        
        # Calculate injection order
        self.injection_order = self._calculate_injection_order()
        
        logger.info(f"Dependency graph built: {len(self.dependency_graph)} files, {len(self.injection_order)} injection order")
        return self.dependency_graph
    
    def _find_source_files(self, folder: Path, extensions: List[str]) -> List[Path]:
        """Find all source files in folder and subfolders"""
        files = []
        
        for file_path in folder.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                # Skip common excluded directories
                if any(excluded in file_path.parts for excluded in ['__pycache__', '.git', '.venv', 'node_modules']):
                    continue
                files.append(file_path)
        
        return sorted(files)
    
    def _extract_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from a single file"""
        dependencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if file_path.suffix == '.py':
                dependencies = self._extract_python_dependencies(content, file_path)
            elif file_path.suffix in ['.js', '.ts']:
                dependencies = self._extract_javascript_dependencies(content, file_path)
            elif file_path.suffix in ['.html', '.htm']:
                dependencies = self._extract_html_dependencies(content, file_path)
            elif file_path.suffix == '.css':
                dependencies = self._extract_css_dependencies(content, file_path)
            
        except Exception as e:
            logger.warning(f"Could not extract dependencies from {file_path}: {e}")
        
        return dependencies
    
    def _extract_python_dependencies(self, content: str, file_path: Path) -> List[str]:
        """Extract Python import dependencies"""
        dependencies = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        # Convert module name to potential file path
                        file_dep = self._resolve_python_import(module_name, file_path)
                        if file_dep:
                            dependencies.append(file_dep)
                
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module
                    if module_name:
                        file_dep = self._resolve_python_import(module_name, file_path)
                        if file_dep:
                            dependencies.append(file_dep)
        
        except SyntaxError:
            # Fallback to regex for files with syntax errors
            dependencies = self._extract_python_dependencies_regex(content, file_path)
        
        return dependencies
    
    def _extract_python_dependencies_regex(self, content: str, file_path: Path) -> List[str]:
        """Fallback regex-based Python dependency extraction"""
        dependencies = []
        
        # Match import statements
        import_patterns = [
            r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
            r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                file_dep = self._resolve_python_import(match, file_path)
                if file_dep:
                    dependencies.append(file_dep)
        
        return dependencies
    
    def _extract_javascript_dependencies(self, content: str, file_path: Path) -> List[str]:
        """Extract JavaScript/TypeScript dependencies"""
        dependencies = []
        
        # Match ES6 imports
        import_patterns = [
            r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s+[\'"]([^\'"]+)[\'"]',
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                file_dep = self._resolve_javascript_import(match, file_path)
                if file_dep:
                    dependencies.append(file_dep)
        
        return dependencies
    
    def _extract_html_dependencies(self, content: str, file_path: Path) -> List[str]:
        """Extract HTML dependencies (scripts, stylesheets, etc.)"""
        dependencies = []
        
        # Match script src
        script_pattern = r'<script[^>]*src\s*=\s*[\'"]([^\'"]+)[\'"]'
        script_matches = re.findall(script_pattern, content, re.IGNORECASE)
        
        # Match link href (stylesheets)
        link_pattern = r'<link[^>]*href\s*=\s*[\'"]([^\'"]+)[\'"]'
        link_matches = re.findall(link_pattern, content, re.IGNORECASE)
        
        for match in script_matches + link_matches:
            file_dep = self._resolve_html_import(match, file_path)
            if file_dep:
                dependencies.append(file_dep)
        
        return dependencies
    
    def _extract_css_dependencies(self, content: str, file_path: Path) -> List[str]:
        """Extract CSS dependencies (@import statements)"""
        dependencies = []
        
        # Match @import statements
        import_pattern = r'@import\s+[\'"]([^\'"]+)[\'"]'
        matches = re.findall(import_pattern, content)
        
        for match in matches:
            file_dep = self._resolve_css_import(match, file_path)
            if file_dep:
                dependencies.append(file_dep)
        
        return dependencies
    
    def _resolve_python_import(self, module_name: str, file_path: Path) -> Optional[str]:
        """Resolve Python import to file path"""
        # Handle relative imports
        if module_name.startswith('.'):
            # Convert relative import to absolute
            parts = module_name.split('.')
            current_dir = file_path.parent
            
            for part in parts[1:]:  # Skip the first dot
                if part == '':
                    current_dir = current_dir.parent
                else:
                    current_dir = current_dir / part
            
            # Try common Python file extensions
            for ext in ['.py', '.pyi']:
                potential_file = current_dir.with_suffix(ext)
                if potential_file.exists():
                    return str(potential_file)
            
            # Try as directory with __init__.py
            init_file = current_dir / '__init__.py'
            if init_file.exists():
                return str(init_file)
        
        # Handle absolute imports (simplified)
        else:
            # Look for the module in the same directory structure
            module_parts = module_name.split('.')
            current_dir = file_path.parent
            
            for part in module_parts:
                current_dir = current_dir / part
            
            # Try common extensions
            for ext in ['.py', '.pyi']:
                potential_file = current_dir.with_suffix(ext)
                if potential_file.exists():
                    return str(potential_file)
            
            # Try as directory with __init__.py
            init_file = current_dir / '__init__.py'
            if init_file.exists():
                return str(init_file)
        
        return None
    
    def _resolve_javascript_import(self, import_path: str, file_path: Path) -> Optional[str]:
        """Resolve JavaScript import to file path"""
        # Handle relative imports
        if import_path.startswith('.'):
            # Convert relative import to absolute
            if import_path.startswith('./'):
                import_path = import_path[2:]
            elif import_path.startswith('../'):
                # Go up directories
                up_count = import_path.count('../')
                import_path = import_path[3 * up_count:]
                current_dir = file_path.parent
                for _ in range(up_count):
                    current_dir = current_dir.parent
            else:
                current_dir = file_path.parent
        else:
            # Absolute import (simplified - could be enhanced for node_modules)
            current_dir = file_path.parent
        
        # Try to resolve the file
        potential_file = current_dir / import_path
        
        # Try common extensions
        for ext in ['.js', '.ts', '.jsx', '.tsx']:
            if potential_file.with_suffix(ext).exists():
                return str(potential_file.with_suffix(ext))
        
        # Try as-is
        if potential_file.exists():
            return str(potential_file)
        
        return None
    
    def _resolve_html_import(self, import_path: str, file_path: Path) -> Optional[str]:
        """Resolve HTML import to file path"""
        # Handle relative paths
        if import_path.startswith('.'):
            if import_path.startswith('./'):
                import_path = import_path[2:]
            elif import_path.startswith('../'):
                # Go up directories
                up_count = import_path.count('../')
                import_path = import_path[3 * up_count:]
                current_dir = file_path.parent
                for _ in range(up_count):
                    current_dir = current_dir.parent
            else:
                current_dir = file_path.parent
        else:
            current_dir = file_path.parent
        
        potential_file = current_dir / import_path
        
        if potential_file.exists():
            return str(potential_file)
        
        return None
    
    def _resolve_css_import(self, import_path: str, file_path: Path) -> Optional[str]:
        """Resolve CSS import to file path"""
        return self._resolve_html_import(import_path, file_path)
    
    def _calculate_injection_order(self) -> List[str]:
        """Calculate optimal injection order using topological sort"""
        try:
            # Create a copy of the graph for sorting
            graph_copy = {k: list(v) for k, v in self.dependency_graph.items()}
            
            # Use graphlib for topological sorting
            sorter = graphlib.TopologicalSorter(graph_copy)
            order = list(sorter.static_order())
            
            return order
        except graphlib.CycleError as e:
            logger.warning(f"Circular dependency detected: {e}")
            # Fallback: return files in dependency order (most independent first)
            return self._fallback_injection_order()
        except Exception as e:
            logger.error(f"Error calculating injection order: {e}")
            return list(self.dependency_graph.keys())
    
    def _fallback_injection_order(self) -> List[str]:
        """Fallback injection order when topological sort fails"""
        # Sort by number of dependencies (least dependent first)
        files_with_deps = [(file, len(deps)) for file, deps in self.dependency_graph.items()]
        files_with_deps.sort(key=lambda x: x[1])
        return [file for file, _ in files_with_deps]
    
    def get_context_files(self, file_path: str, depth: int = 3) -> List[str]:
        """
        Get context files for a given file up to specified depth
        
        Args:
            file_path: Path to the file
            depth: How deep to go in the dependency chain
            
        Returns:
            List of context file paths
        """
        if file_path not in self.dependency_graph:
            return []
        
        context_files = set()
        visited = set()
        queue = deque([(file_path, 0)])  # (file, depth)
        
        while queue:
            current_file, current_depth = queue.popleft()
            
            if current_file in visited or current_depth > depth:
                continue
            
            visited.add(current_file)
            
            # Add dependencies as context
            for dep in self.dependency_graph.get(current_file, []):
                if dep not in visited and current_depth < depth:
                    context_files.add(dep)
                    queue.append((dep, current_depth + 1))
            
            # Add files that depend on this file (reverse dependencies)
            for dependent in self.reverse_graph.get(current_file, []):
                if dependent not in visited and current_depth < depth:
                    context_files.add(dependent)
                    queue.append((dependent, current_depth + 1))
        
        return list(context_files)
    
    def prepare_context_prompt(self, file_path: str, depth: int = 3, max_tokens: int = 8000) -> str:
        """
        Prepare a context-aware prompt for injection
        
        Args:
            file_path: Path to the file to inject
            depth: Context depth
            max_tokens: Maximum tokens for context
            
        Returns:
            Context-aware prompt string
        """
        context_files = self.get_context_files(file_path, depth)
        
        # Read the target file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                target_content = f.read()
        except Exception as e:
            logger.error(f"Could not read target file {file_path}: {e}")
            return ""
        
        # Build context from related files
        context_parts = []
        total_tokens = 0
        
        for context_file in context_files:
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
                estimated_tokens = len(content) // 4
                
                if total_tokens + estimated_tokens > max_tokens:
                    # Trim content to fit
                    max_chars = (max_tokens - total_tokens) * 4
                    content = content[:max_chars] + "\n# ... (truncated for token limit)"
                
                context_parts.append(f"# Context from: {context_file}\n{content}\n")
                total_tokens += estimated_tokens
                
            except Exception as e:
                logger.warning(f"Could not read context file {context_file}: {e}")
        
        # Build final prompt
        if context_parts:
            context_section = "\n".join(context_parts)
            prompt = f"""# Context Files
{context_section}

# Target File: {file_path}
{target_content}"""
        else:
            prompt = f"# Target File: {file_path}\n{target_content}"
        
        return prompt
    
    def save_dependency_map(self, output_path: str = ".injectmap.json") -> None:
        """Save dependency map to file"""
        try:
            map_data = {
                "dependency_graph": self.dependency_graph,
                "injection_order": self.injection_order,
                "file_metadata": self.file_metadata,
                "generated_at": datetime.now().isoformat()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(map_data, f, indent=2)
            
            logger.info(f"Dependency map saved to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save dependency map: {e}")
    
    def load_dependency_map(self, input_path: str = ".injectmap.json") -> bool:
        """Load dependency map from file"""
        try:
            if not Path(input_path).exists():
                return False
            
            with open(input_path, 'r', encoding='utf-8') as f:
                map_data = json.load(f)
            
            self.dependency_graph = map_data.get("dependency_graph", {})
            self.injection_order = map_data.get("injection_order", [])
            self.file_metadata = map_data.get("file_metadata", {})
            
            # Rebuild reverse graph
            self.reverse_graph = defaultdict(set)
            for file_path, deps in self.dependency_graph.items():
                for dep in deps:
                    self.reverse_graph[dep].add(file_path)
            
            logger.info(f"Dependency map loaded from: {input_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load dependency map: {e}")
            return False


# Global dependency tracker instance
dependency_tracker = DependencyTracker()


def build_dependency_graph(folder_path: str, extensions: List[str] = None) -> Dict[str, List[str]]:
    """Convenience function to build dependency graph"""
    return dependency_tracker.build_dependency_graph(folder_path, extensions)


def get_context_files(file_path: str, depth: int = 3) -> List[str]:
    """Convenience function to get context files"""
    return dependency_tracker.get_context_files(file_path, depth)


def prepare_context_prompt(file_path: str, depth: int = 3, max_tokens: int = 8000) -> str:
    """Convenience function to prepare context prompt"""
    return dependency_tracker.prepare_context_prompt(file_path, depth, max_tokens) 