"""
Dependency Visualizer for SurgiInject Phase 6.9
Simple text-based dependency graph visualization
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_dependency_graph(dependency_graph: Dict[str, List[str]], directory: str) -> str:
    """
    Generate a text-based visualization of the dependency graph
    
    Args:
        dependency_graph: Dictionary mapping files to their dependencies
        directory: Root directory name for the graph
        
    Returns:
        Path to the generated visualization file
    """
    try:
        # Create visualization directory
        viz_dir = Path("dependency_viz")
        viz_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"deps_{Path(directory).name}_{timestamp}.txt"
        output_path = viz_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Dependency Graph for: {directory}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            
            # Show file count and dependency statistics
            total_files = len(dependency_graph)
            total_deps = sum(len(deps) for deps in dependency_graph.values())
            avg_deps = total_deps / total_files if total_files > 0 else 0
            
            f.write(f"📊 STATISTICS:\n")
            f.write(f"   Total files: {total_files}\n")
            f.write(f"   Total dependencies: {total_deps}\n")
            f.write(f"   Average dependencies per file: {avg_deps:.1f}\n\n")
            
            # Show files with most dependencies
            files_by_deps = sorted(
                [(file, len(deps)) for file, deps in dependency_graph.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            f.write(f"🔝 TOP 10 FILES BY DEPENDENCIES:\n")
            for i, (file_path, dep_count) in enumerate(files_by_deps[:10], 1):
                f.write(f"   {i:2d}. {file_path} ({dep_count} deps)\n")
            f.write("\n")
            
            # Show dependency tree
            f.write(f"🌳 DEPENDENCY TREE:\n")
            f.write(f"   (Files are shown with their dependencies)\n\n")
            
            # Sort files for consistent output
            sorted_files = sorted(dependency_graph.keys())
            
            for file_path in sorted_files:
                deps = dependency_graph[file_path]
                if deps:
                    f.write(f"📁 {file_path}\n")
                    for dep in sorted(deps):
                        f.write(f"   └─ {dep}\n")
                    f.write("\n")
            
            # Show files with no dependencies
            files_without_deps = [file for file, deps in dependency_graph.items() if not deps]
            if files_without_deps:
                f.write(f"📄 FILES WITH NO DEPENDENCIES:\n")
                for file_path in sorted(files_without_deps):
                    f.write(f"   • {file_path}\n")
                f.write("\n")
            
            # Show circular dependency warnings
            circular_deps = find_circular_dependencies(dependency_graph)
            if circular_deps:
                f.write(f"⚠️  POTENTIAL CIRCULAR DEPENDENCIES:\n")
                for cycle in circular_deps:
                    f.write(f"   {' -> '.join(cycle)} -> {cycle[0]}\n")
                f.write("\n")
            
            # Show recommended injection order
            try:
                from .dependency_tracker import dependency_tracker
                if dependency_tracker.injection_order:
                    f.write(f"🔄 RECOMMENDED INJECTION ORDER:\n")
                    for i, file_path in enumerate(dependency_tracker.injection_order, 1):
                        f.write(f"   {i:2d}. {file_path}\n")
                    f.write("\n")
            except ImportError:
                pass
            
            # Show file size information
            f.write(f"📏 FILE SIZE ANALYSIS:\n")
            size_ranges = {'<1KB': 0, '1-10KB': 0, '10-100KB': 0, '>100KB': 0}
            
            for file_path in dependency_graph.keys():
                try:
                    size = Path(file_path).stat().st_size
                    if size < 1024:
                        size_ranges['<1KB'] += 1
                    elif size < 10240:
                        size_ranges['1-10KB'] += 1
                    elif size < 102400:
                        size_ranges['10-100KB'] += 1
                    else:
                        size_ranges['>100KB'] += 1
                except:
                    pass
            
            for range_name, count in size_ranges.items():
                f.write(f"   {range_name}: {count} files\n")
            f.write("\n")
            
            # Show file type breakdown
            f.write(f"📋 FILE TYPE BREAKDOWN:\n")
            file_types = {}
            for file_path in dependency_graph.keys():
                ext = Path(file_path).suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
            
            for ext, count in sorted(file_types.items()):
                f.write(f"   {ext or 'no extension'}: {count} files\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("End of dependency analysis\n")
        
        logger.info(f"Dependency visualization saved to: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Failed to generate dependency visualization: {e}")
        return ""


def find_circular_dependencies(dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    Find potential circular dependencies in the graph
    
    Args:
        dependency_graph: Dictionary mapping files to their dependencies
        
    Returns:
        List of circular dependency cycles
    """
    cycles = []
    visited = set()
    rec_stack = set()
    
    def dfs(node: str, path: List[str]) -> None:
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycles.append(cycle)
            return
        
        if node in visited:
            return
        
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for dep in dependency_graph.get(node, []):
            dfs(dep, path.copy())
        
        rec_stack.remove(node)
    
    for node in dependency_graph:
        if node not in visited:
            dfs(node, [])
    
    return cycles


def generate_simple_dot_graph(dependency_graph: Dict[str, List[str]], directory: str) -> str:
    """
    Generate a simple DOT format graph for visualization tools
    
    Args:
        dependency_graph: Dictionary mapping files to their dependencies
        directory: Root directory name
        
    Returns:
        Path to the generated DOT file
    """
    try:
        # Create visualization directory
        viz_dir = Path("dependency_viz")
        viz_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"deps_{Path(directory).name}_{timestamp}.dot"
        output_path = viz_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"// Dependency Graph for: {directory}\n")
            f.write(f"// Generated: {datetime.now().isoformat()}\n\n")
            f.write("digraph dependency_graph {\n")
            f.write("  rankdir=TB;\n")
            f.write("  node [shape=box, style=filled, fillcolor=lightblue];\n\n")
            
            # Add nodes
            for file_path in dependency_graph:
                node_name = file_path.replace('/', '_').replace('.', '_').replace('-', '_')
                f.write(f'  "{node_name}" [label="{file_path}"];\n')
            
            f.write("\n")
            
            # Add edges
            for file_path, deps in dependency_graph.items():
                source_node = file_path.replace('/', '_').replace('.', '_').replace('-', '_')
                for dep in deps:
                    target_node = dep.replace('/', '_').replace('.', '_').replace('-', '_')
                    f.write(f'  "{source_node}" -> "{target_node}";\n')
            
            f.write("}\n")
        
        logger.info(f"DOT graph saved to: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Failed to generate DOT graph: {e}")
        return ""


def generate_html_report(dependency_graph: Dict[str, List[str]], directory: str) -> str:
    """
    Generate an HTML report of the dependency analysis
    
    Args:
        dependency_graph: Dictionary mapping files to their dependencies
        directory: Root directory name
        
    Returns:
        Path to the generated HTML file
    """
    try:
        # Create visualization directory
        viz_dir = Path("dependency_viz")
        viz_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"deps_{Path(directory).name}_{timestamp}.html"
        output_path = viz_dir / filename
        
        # Calculate statistics
        total_files = len(dependency_graph)
        total_deps = sum(len(deps) for deps in dependency_graph.values())
        avg_deps = total_deps / total_files if total_files > 0 else 0
        
        # Find files with most dependencies
        files_by_deps = sorted(
            [(file, len(deps)) for file, deps in dependency_graph.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Dependency Analysis - {directory}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-box {{ background: #e8f4fd; padding: 15px; border-radius: 5px; flex: 1; }}
        .file-list {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .dependency-tree {{ font-family: monospace; }}
        .file-item {{ margin: 5px 0; }}
        .dependency {{ margin-left: 20px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Dependency Analysis Report</h1>
        <p><strong>Directory:</strong> {directory}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <h3>📁 Total Files</h3>
            <p style="font-size: 24px; font-weight: bold;">{total_files}</p>
        </div>
        <div class="stat-box">
            <h3>🔗 Total Dependencies</h3>
            <p style="font-size: 24px; font-weight: bold;">{total_deps}</p>
        </div>
        <div class="stat-box">
            <h3>📈 Avg Dependencies</h3>
            <p style="font-size: 24px; font-weight: bold;">{avg_deps:.1f}</p>
        </div>
    </div>
    
    <div class="file-list">
        <h2>🔝 Top Files by Dependencies</h2>
""")
            
            for i, (file_path, dep_count) in enumerate(files_by_deps[:10], 1):
                f.write(f'        <div class="file-item">{i}. {file_path} ({dep_count} deps)</div>\n')
            
            f.write("""
    </div>
    
    <div class="file-list">
        <h2>🌳 Dependency Tree</h2>
        <div class="dependency-tree">
""")
            
            # Show dependency tree
            sorted_files = sorted(dependency_graph.keys())
            for file_path in sorted_files:
                deps = dependency_graph[file_path]
                if deps:
                    f.write(f'            <div class="file-item">📁 {file_path}</div>\n')
                    for dep in sorted(deps):
                        f.write(f'                <div class="dependency">└─ {dep}</div>\n')
                    f.write('            <br>\n')
            
            f.write("""
        </div>
    </div>
</body>
</html>
""")
        
        logger.info(f"HTML report saved to: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Failed to generate HTML report: {e}")
        return "" 