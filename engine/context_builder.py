"""
Context Builder for SurgiInject
Analyzes file dependencies and builds injection context
"""

import ast
import re
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from .file_utils import safe_read_file, get_file_encoding

logger = logging.getLogger(__name__)

# Context limits
MAX_CONTEXT_FILES = 5
MAX_CONTEXT_CHARS = 10000
MAX_CONTEXT_LINES = 500

class ImportAnalyzer:
    """Analyzes Python files for import statements and dependencies"""
    
    def __init__(self):
        self.import_cache = {}
        self.file_dependencies = {}
    
    def analyze_imports(self, file_path: Path, project_root: Path = None) -> List[str]:
        """
        Analyze a Python file and extract all import statements
        
        Args:
            file_path: Path to the Python file to analyze
            project_root: Root directory of the project for relative path resolution
            
        Returns:
            List of imported module/file paths
        """
        if file_path in self.import_cache:
            return self.import_cache[file_path]
        
        try:
            content = safe_read_file(file_path)
            if not content:
                return []
            
            # Parse with AST for accurate import detection
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        if module:
                            imports.append(f"{module}.{alias.name}")
                        else:
                            imports.append(alias.name)
            
            # Filter and resolve relative imports
            resolved_imports = self._resolve_imports(imports, file_path, project_root)
            self.import_cache[file_path] = resolved_imports
            return resolved_imports
            
        except Exception as e:
            logger.warning(f"Could not analyze imports in {file_path}: {e}")
            return []
    
    def _resolve_imports(self, imports: List[str], file_path: Path, project_root: Path = None) -> List[str]:
        """
        Resolve import statements to actual file paths
        
        Args:
            imports: List of import statements
            file_path: Path to the file containing imports
            project_root: Root directory of the project
            
        Returns:
            List of resolved file paths
        """
        resolved = []
        file_dir = file_path.parent
        
        for imp in imports:
            # Skip standard library and third-party imports
            if self._is_standard_library(imp) or self._is_third_party(imp):
                continue
            
            # Handle relative imports
            if imp.startswith('.'):
                resolved_path = self._resolve_relative_import(imp, file_dir)
                if resolved_path:
                    resolved.append(str(resolved_path))
            else:
                # Handle absolute imports within project
                if project_root:
                    resolved_path = self._resolve_absolute_import(imp, project_root)
                    if resolved_path:
                        resolved.append(str(resolved_path))
        
        return resolved
    
    def _is_standard_library(self, module: str) -> bool:
        """Check if module is part of Python standard library"""
        stdlib_modules = {
            'os', 'sys', 're', 'json', 'pathlib', 'typing', 'logging',
            'datetime', 'collections', 'itertools', 'functools', 'asyncio',
            'threading', 'multiprocessing', 'subprocess', 'tempfile',
            'urllib', 'http', 'socket', 'ssl', 'hashlib', 'base64'
        }
        return module.split('.')[0] in stdlib_modules
    
    def _is_third_party(self, module: str) -> bool:
        """Check if module is likely a third-party package"""
        third_party_indicators = {
            'requests', 'numpy', 'pandas', 'matplotlib', 'flask', 'django',
            'fastapi', 'pytest', 'selenium', 'beautifulsoup', 'pillow',
            'sqlalchemy', 'pymongo', 'redis', 'celery', 'jinja2'
        }
        return module.split('.')[0] in third_party_indicators
    
    def _resolve_relative_import(self, import_str: str, current_dir: Path) -> Optional[Path]:
        """Resolve relative import to file path"""
        try:
            # Remove leading dots and count them
            dots = 0
            while import_str.startswith('.'):
                dots += 1
                import_str = import_str[1:]
            
            if not import_str:
                return None
            
            # Navigate up directories based on dot count
            target_dir = current_dir
            for _ in range(dots - 1):
                target_dir = target_dir.parent
            
            # Try different file extensions
            for ext in ['.py', '.pyi']:
                # Direct file import
                file_path = target_dir / f"{import_str}{ext}"
                if file_path.exists():
                    return file_path
                
                # Package import (__init__.py)
                package_path = target_dir / import_str.replace('.', '/') / '__init__.py'
                if package_path.exists():
                    return package_path
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not resolve relative import {import_str}: {e}")
            return None
    
    def _resolve_absolute_import(self, import_str: str, project_root: Path) -> Optional[Path]:
        """Resolve absolute import within project"""
        try:
            # Convert dots to path separators
            module_path = import_str.replace('.', '/')
            
            # Try different file extensions
            for ext in ['.py', '.pyi']:
                file_path = project_root / f"{module_path}{ext}"
                if file_path.exists():
                    return file_path
                
                # Package import
                package_path = project_root / module_path / '__init__.py'
                if package_path.exists():
                    return package_path
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not resolve absolute import {import_str}: {e}")
            return None


class ContextBuilder:
    """Builds injection context by analyzing file dependencies"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.analyzer = ImportAnalyzer()
        self.context_cache = {}
    
    def build_context_for_file(self, file_path: Path, max_files: int = MAX_CONTEXT_FILES) -> str:
        """
        Build context for a target file by analyzing its dependencies
        
        Args:
            file_path: Path to the target file
            max_files: Maximum number of context files to include
            
        Returns:
            Formatted context string for injection
        """
        cache_key = (file_path, max_files)
        if cache_key in self.context_cache:
            return self.context_cache[cache_key]
        
        # Get dependencies
        dependencies = self._get_file_dependencies(file_path)
        
        # Prioritize and limit dependencies
        prioritized_deps = self._prioritize_dependencies(dependencies, max_files)
        
        # Build context string
        context = self._format_context(prioritized_deps)
        
        self.context_cache[cache_key] = context
        return context
    
    def _get_file_dependencies(self, file_path: Path) -> List[Path]:
        """Get all dependencies for a file"""
        if file_path.suffix != '.py':
            return []
        
        # Get direct imports
        imports = self.analyzer.analyze_imports(file_path, self.project_root)
        
        # Convert to Path objects and filter existing files
        dependencies = []
        for imp in imports:
            dep_path = Path(imp)
            if dep_path.exists() and dep_path.is_file():
                dependencies.append(dep_path)
        
        # Add common utility files in the same directory
        file_dir = file_path.parent
        common_utils = ['utils.py', 'helpers.py', 'common.py', 'constants.py']
        for util in common_utils:
            util_path = file_dir / util
            if util_path.exists() and util_path != file_path:
                dependencies.append(util_path)
        
        return dependencies
    
    def _prioritize_dependencies(self, dependencies: List[Path], max_files: int) -> List[Path]:
        """Prioritize dependencies based on importance and file size"""
        if len(dependencies) <= max_files:
            return dependencies
        
        # Score dependencies based on various factors
        scored_deps = []
        for dep in dependencies:
            score = self._score_dependency(dep)
            scored_deps.append((score, dep))
        
        # Sort by score (higher first) and take top N
        scored_deps.sort(key=lambda x: x[0], reverse=True)
        return [dep for _, dep in scored_deps[:max_files]]
    
    def _score_dependency(self, file_path: Path) -> float:
        """Score a dependency based on various factors"""
        score = 0.0
        
        try:
            # File size factor (smaller files get higher score)
            size = file_path.stat().st_size
            if size < 1000:
                score += 10
            elif size < 5000:
                score += 5
            elif size < 10000:
                score += 2
            
            # File type factor
            if file_path.name in ['utils.py', 'helpers.py', 'common.py']:
                score += 5
            elif file_path.name == '__init__.py':
                score += 3
            
            # Directory depth factor (closer files get higher score)
            depth = len(file_path.parts)
            score += max(0, 10 - depth)
            
            # Content factor (files with functions/classes get higher score)
            content = safe_read_file(file_path)
            if content:
                if 'def ' in content or 'class ' in content:
                    score += 3
                if 'import ' in content or 'from ' in content:
                    score += 1
            
        except Exception:
            pass
        
        return score
    
    def _format_context(self, dependencies: List[Path]) -> str:
        """Format dependencies into a context string"""
        if not dependencies:
            return ""
        
        context_parts = []
        total_chars = 0
        
        for dep in dependencies:
            try:
                content = safe_read_file(dep)
                if not content:
                    continue
                
                # Truncate content if too long
                if len(content) > MAX_CONTEXT_CHARS // len(dependencies):
                    lines = content.split('\n')
                    if len(lines) > MAX_CONTEXT_LINES // len(dependencies):
                        lines = lines[:MAX_CONTEXT_LINES // len(dependencies)]
                        content = '\n'.join(lines) + '\n# ... (truncated)'
                
                # Format context block
                context_block = f"""=== CONTEXT START: {dep.name} ===
{content}
=== CONTEXT END: {dep.name} ===

"""
                
                context_parts.append(context_block)
                total_chars += len(context_block)
                
                # Stop if we're approaching the limit
                if total_chars > MAX_CONTEXT_CHARS:
                    break
                    
            except Exception as e:
                logger.warning(f"Could not read dependency {dep}: {e}")
        
        return ''.join(context_parts)


def inject_with_context(
    file_path: Path,
    prompt_template: str,
    project_root: Path = None,
    max_context_files: int = MAX_CONTEXT_FILES
) -> str:
    """
    Inject AI modifications with context from dependencies
    
    Args:
        file_path: Path to the target file
        prompt_template: Prompt template for injection
        project_root: Root directory of the project
        max_context_files: Maximum number of context files to include
        
    Returns:
        Modified file content
    """
    from .injector import run_injection
    
    # Build context
    context_builder = ContextBuilder(project_root)
    context = context_builder.build_context_for_file(file_path, max_context_files)
    
    # Read target file
    source_content = safe_read_file(file_path)
    if not source_content:
        return ""
    
    # Create enhanced prompt with context
    if context:
        enhanced_prompt = f"""{prompt_template}

=== PROJECT CONTEXT ===
{context}
=== END CONTEXT ===

Please analyze the context above and apply the requested changes to the following file:

=== TARGET FILE: {file_path.name} ===
{source_content}
=== END TARGET FILE ===
"""
    else:
        enhanced_prompt = f"""{prompt_template}

=== TARGET FILE: {file_path.name} ===
{source_content}
=== END TARGET FILE ===
"""
    
    # Run injection with enhanced prompt
    return run_injection(
        source_code=source_content,
        prompt_template=enhanced_prompt,
        file_path=str(file_path),
        provider='auto',
        force=False
    )


def analyze_project_dependencies(project_root: Path) -> Dict[str, List[str]]:
    """
    Analyze all Python files in a project and build dependency map
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        Dictionary mapping file paths to their dependencies
    """
    analyzer = ImportAnalyzer()
    dependency_map = {}
    
    # Find all Python files
    python_files = list(project_root.rglob("*.py"))
    
    for file_path in python_files:
        dependencies = analyzer.analyze_imports(file_path, project_root)
        dependency_map[str(file_path)] = dependencies
    
    return dependency_map


def get_related_files(file_path: Path, project_root: Path = None, max_files: int = 5) -> List[Path]:
    """
    Get files related to a target file (dependencies and dependents)
    
    Args:
        file_path: Path to the target file
        project_root: Root directory of the project
        max_files: Maximum number of related files to return
        
    Returns:
        List of related file paths
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # Get dependencies
    analyzer = ImportAnalyzer()
    dependencies = analyzer.analyze_imports(file_path, project_root)
    dep_paths = [Path(dep) for dep in dependencies if Path(dep).exists()]
    
    # Get dependents (files that import this file)
    dependents = []
    for py_file in project_root.rglob("*.py"):
        if py_file != file_path:
            imports = analyzer.analyze_imports(py_file, project_root)
            if str(file_path) in imports:
                dependents.append(py_file)
    
    # Combine and limit results
    related = dep_paths + dependents
    return related[:max_files] 