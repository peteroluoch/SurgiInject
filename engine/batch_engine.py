"""
Batch Injection Engine for SurgiInject
Coordinates multi-file, context-aware, and deduplicated injections
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from .file_utils import file_contains_marker, add_marker_to_content, is_meaningful_response, safe_write_file
from .context_builder import inject_with_context, ContextBuilder
from .injector import run_injection
import time
import os
import re

logger = logging.getLogger(__name__)

HISTORY_DIR = Path('.surgiinject/history')
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def batch_inject(files: List[Path], prompt_path: str, with_context: bool = True, coordinated: bool = False) -> Dict[str, Any]:
    """
    Inject/refactor multiple files in a coordinated, context-aware batch.
    Args:
        files: List of file paths to inject
        prompt_path: Path to prompt template
        with_context: Use context builder for each file
        coordinated: Enable cross-file deduplication and consistency
    Returns:
        Dict with per-file results and summary
    """
    results = []
    file_states = {}
    injected_outputs = {}
    timestamp = int(time.time())
    
    # Read prompt
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # Build context builder (assume all files in same project root)
    project_root = files[0].parent if files else Path.cwd()
    context_builder = ContextBuilder(project_root)
    
    for file_path in files:
        file_path = Path(file_path)
        logger.info(f"Processing: {file_path}")
        
        # Skip already injected
        if file_contains_marker(file_path):
            logger.info(f"Skipping already-injected file: {file_path}")
            results.append({'file': str(file_path), 'status': 'skipped', 'reason': 'already injected'})
            continue
        
        # Read original content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            results.append({'file': str(file_path), 'status': 'failed', 'reason': 'read error'})
            continue
        
        if not original_content.strip():
            logger.info(f"Skipping empty file: {file_path}")
            results.append({'file': str(file_path), 'status': 'skipped', 'reason': 'empty'})
            continue
        
        # Save pre-injection state for coordination
        file_states[str(file_path)] = original_content
        
        # Inject with context
        if with_context:
            modified = inject_with_context(
                file_path=file_path,
                prompt_template=prompt_template,
                project_root=project_root,
                max_context_files=5
            )
        else:
            modified = run_injection(
                source_code=original_content,
                prompt_template=prompt_template,
                file_path=str(file_path),
                provider='auto',
                force=False
            )
        
        # Check response
        if not is_meaningful_response(modified):
            logger.warning(f"Weak/empty response for {file_path}")
            results.append({'file': str(file_path), 'status': 'failed', 'reason': 'empty/weak response'})
            continue
        
        # Store output for coordination
        injected_outputs[str(file_path)] = modified
        
    # Coordination: deduplicate helpers/classes across files
    if coordinated:
        logger.info("Running cross-file deduplication and consistency checks...")
        injected_outputs = deduplicate_across_files(injected_outputs)
    
    # Write results and log
    for file_path_str, modified in injected_outputs.items():
        file_path = Path(file_path_str)
        marked = add_marker_to_content(modified, file_path)
        if safe_write_file(file_path, marked, backup=True):
            results.append({'file': str(file_path), 'status': 'injected', 'coordinated': coordinated})
            # Save to history
            save_injection_history(file_path, marked, timestamp)
        else:
            results.append({'file': str(file_path), 'status': 'failed', 'reason': 'write error'})
    
    return {
        'results': results,
        'timestamp': timestamp,
        'coordinated': coordinated
    }

def deduplicate_across_files(injected_outputs: Dict[str, str]) -> Dict[str, str]:
    """
    Remove duplicate function/class definitions across injected files.
    Args:
        injected_outputs: Dict of file_path -> injected content
    Returns:
        Dict with deduplicated content
    """
    seen_defs = set()
    deduped_outputs = {}
    def_pattern = re.compile(r'^(def|class)\s+(\w+)', re.MULTILINE)
    
    for file_path, content in injected_outputs.items():
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            match = def_pattern.match(line.strip())
            if match:
                def_type, name = match.groups()
                key = f"{def_type}:{name}"
                if key in seen_defs:
                    continue  # skip duplicate
                seen_defs.add(key)
            new_lines.append(line)
        deduped_outputs[file_path] = '\n'.join(new_lines)
    return deduped_outputs

def save_injection_history(file_path: Path, content: str, timestamp: int):
    """
    Save injected file content to .surgiinject/history/ for audit/logging
    """
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history_file = HISTORY_DIR / f"{file_path.name}.{timestamp}.txt"
    with open(history_file, 'w', encoding='utf-8') as f:
        f.write(content) 