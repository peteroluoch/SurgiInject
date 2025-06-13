"""
Enhanced Recursive Injection Engine for SurgiInject Phase 6.9
Supports dependency tracking, context awareness, and intelligent file splitting
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .injector import run_injection
from .file_utils import load_prompt, get_file_size_mb, save_output
from .dependency_tracker import dependency_tracker, get_context_files, prepare_context_prompt
from .file_splitter import file_splitter, split_file
from .injection_queue import injection_queue

logger = logging.getLogger(__name__)

class EnhancedRecursiveInjector:
    """Enhanced recursive injection with dependency tracking and file splitting"""
    
    def __init__(self):
        self.results = {
            'total_files_found': 0,
            'files_processed': 0,
            'successful_injections': [],
            'failed_injections': [],
            'skipped_files': [],
            'context_aware_count': 0,
            'provider_usage': {},
            'performance_metrics': {},
            'dependency_aware': False,
            'files_split': 0,
            'chunks_processed': 0
        }
        self.lock = threading.Lock()
    
    def inject_directory_enhanced(
        self,
        directory: str,
        prompt_path: str,
        extensions: List[str] = None,
        recursive: bool = True,
        apply: bool = False,
        with_context: bool = True,
        provider_chain: List[str] = None,
        max_size: float = 10.0,
        exclude: List[str] = None,
        track_deps: bool = False,
        context_depth: int = 3,
        skip_known: bool = False,
        split_large: bool = False,
        dependency_graph: Dict[str, List[str]] = None,
        max_workers: int = 4
    ) -> Dict[str, Any]:
        """
        Enhanced directory injection with dependency tracking
        
        Args:
            directory: Root directory to process
            prompt_path: Path to prompt template
            extensions: File extensions to process
            recursive: Process subdirectories
            apply: Apply changes to files
            with_context: Use context-aware injection
            provider_chain: AI providers to try
            max_size: Maximum file size in MB
            exclude: Directories to exclude
            track_deps: Enable dependency tracking
            context_depth: Depth for context resolution
            skip_known: Skip files with cached results
            split_large: Split large files into chunks
            dependency_graph: Pre-built dependency graph
            max_workers: Maximum concurrent workers
            
        Returns:
            Dictionary with injection results
        """
        start_time = time.time()
        
        # Initialize defaults
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.html', '.css', '.md', '.txt']
        if provider_chain is None:
            provider_chain = ['anthropic', 'groq', 'fallback']
        if exclude is None:
            exclude = ['__pycache__', '.git', '.venv', 'node_modules', '.pytest_cache']
        
        # Load prompt template
        try:
            prompt_template = load_prompt(prompt_path)
            logger.info(f"Loaded prompt template: {prompt_path}")
        except Exception as e:
            logger.error(f"Failed to load prompt template: {e}")
            return {'success': False, 'error': f'Failed to load prompt: {e}'}
        
        # Build or use dependency graph
        if track_deps:
            if dependency_graph:
                dependency_tracker.dependency_graph = dependency_graph
                dependency_tracker.injection_order = dependency_tracker._calculate_injection_order()
                logger.info(f"Using provided dependency graph with {len(dependency_graph)} files")
            else:
                logger.info("Building dependency graph...")
                dependency_graph = dependency_tracker.build_dependency_graph(directory, extensions)
            
            self.results['dependency_aware'] = True
            logger.info(f"Dependency graph built: {len(dependency_graph)} files")
        
        # Find all files to process
        files_to_process = self._find_files(directory, extensions, recursive, exclude, max_size)
        self.results['total_files_found'] = len(files_to_process)
        
        if not files_to_process:
            logger.warning("No files found to process")
            return {'success': True, 'total_files': 0, 'message': 'No files found'}
        
        # Sort files by dependency order if tracking dependencies
        if track_deps and dependency_tracker.injection_order:
            files_to_process = self._sort_by_dependency_order(files_to_process)
            logger.info(f"Files sorted by dependency order")
        
        logger.info(f"Processing {len(files_to_process)} files")
        
        # Process files (with optional parallelization)
        if max_workers > 1 and len(files_to_process) > 1:
            self._process_files_parallel(
                files_to_process, prompt_template, apply, with_context, 
                provider_chain, track_deps, context_depth, skip_known, split_large, max_workers
            )
        else:
            self._process_files_sequential(
                files_to_process, prompt_template, apply, with_context,
                provider_chain, track_deps, context_depth, skip_known, split_large
            )
        
        # Calculate performance metrics
        end_time = time.time()
        total_time = end_time - start_time
        
        self.results['performance_metrics'] = {
            'total_time': total_time,
            'avg_time_per_file': total_time / len(files_to_process) if files_to_process else 0,
            'files_per_second': len(files_to_process) / total_time if total_time > 0 else 0
        }
        
        # Update provider usage statistics
        for injection in self.results['successful_injections']:
            provider = injection.get('provider', 'unknown')
            self.results['provider_usage'][provider] = self.results['provider_usage'].get(provider, 0) + 1
        
        return {
            'success': True,
            'total_files': len(files_to_process),
            'successful_injections': len(self.results['successful_injections']),
            'failed_injections': len(self.results['failed_injections']),
            'skipped_files': len(self.results['skipped_files']),
            'dependency_aware': self.results['dependency_aware'],
            'files_split': self.results['files_split'],
            'chunks_processed': self.results['chunks_processed'],
            'injected_files': [inj['file'] for inj in self.results['successful_injections']],
            'skipped_files_list': self.results['skipped_files'],
            'provider_usage': self.results['provider_usage'],
            'performance_metrics': self.results['performance_metrics']
        }
    
    def _find_files(self, directory: str, extensions: List[str], recursive: bool, 
                   exclude: List[str], max_size: float) -> List[str]:
        """Find all files to process"""
        files = []
        directory_path = Path(directory)
        
        if recursive:
            file_iter = directory_path.rglob('*')
        else:
            file_iter = directory_path.glob('*')
        
        for file_path in file_iter:
            if not file_path.is_file():
                continue
            
            # Check if file should be excluded
            if any(excluded in file_path.parts for excluded in exclude):
                continue
            
            # Check file extension
            if file_path.suffix.lower() not in extensions:
                continue
            
            # Check file size
            if get_file_size_mb(str(file_path)) > max_size:
                logger.warning(f"Skipping large file: {file_path} ({get_file_size_mb(str(file_path)):.1f}MB)")
                continue
            
            files.append(str(file_path))
        
        return sorted(files)
    
    def _sort_by_dependency_order(self, files: List[str]) -> List[str]:
        """Sort files by dependency order"""
        ordered_files = []
        remaining_files = set(files)
        
        # Add files in dependency order
        for file_path in dependency_tracker.injection_order:
            if file_path in remaining_files:
                ordered_files.append(file_path)
                remaining_files.remove(file_path)
        
        # Add any remaining files
        ordered_files.extend(sorted(remaining_files))
        
        return ordered_files
    
    def _process_files_sequential(self, files: List[str], prompt_template: str, apply: bool,
                                with_context: bool, provider_chain: List[str], track_deps: bool,
                                context_depth: int, skip_known: bool, split_large: bool):
        """Process files sequentially"""
        for file_path in files:
            self._process_single_file(
                file_path, prompt_template, apply, with_context, provider_chain,
                track_deps, context_depth, skip_known, split_large
            )
    
    def _process_files_parallel(self, files: List[str], prompt_template: str, apply: bool,
                              with_context: bool, provider_chain: List[str], track_deps: bool,
                              context_depth: int, skip_known: bool, split_large: bool, max_workers: int):
        """Process files in parallel"""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for file_path in files:
                future = executor.submit(
                    self._process_single_file,
                    file_path, prompt_template, apply, with_context, provider_chain,
                    track_deps, context_depth, skip_known, split_large
                )
                futures.append(future)
            
            # Wait for all futures to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error in parallel processing: {e}")
    
    def _process_single_file(self, file_path: str, prompt_template: str, apply: bool,
                           with_context: bool, provider_chain: List[str], track_deps: bool,
                           context_depth: int, skip_known: bool, split_large: bool):
        """Process a single file"""
        try:
            logger.info(f"Processing file: {file_path}")
            
            # Check if file should be skipped
            if skip_known and self._has_cached_result(file_path):
                with self.lock:
                    self.results['skipped_files'].append(file_path)
                logger.info(f"Skipping file with cached result: {file_path}")
                return
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                with self.lock:
                    self.results['failed_injections'].append({
                        'file': file_path,
                        'error': f'Failed to read file: {e}'
                    })
                return
            
            # Check if file needs splitting
            if split_large and len(original_content) > 8000:  # Rough token estimate
                logger.info(f"Splitting large file: {file_path}")
                self._process_file_chunks(file_path, original_content, prompt_template, apply,
                                        with_context, provider_chain, track_deps, context_depth)
            else:
                # Process as single file
                self._process_file_content(file_path, original_content, prompt_template, apply,
                                         with_context, provider_chain, track_deps, context_depth)
        
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            with self.lock:
                self.results['failed_injections'].append({
                    'file': file_path,
                    'error': str(e)
                })
    
    def _process_file_chunks(self, file_path: str, original_content: str, prompt_template: str,
                           apply: bool, with_context: bool, provider_chain: List[str],
                           track_deps: bool, context_depth: int):
        """Process a file by splitting it into chunks"""
        try:
            # Split file into chunks
            chunks = split_file(file_path)
            logger.info(f"Split {file_path} into {len(chunks)} chunks")
            
            with self.lock:
                self.results['files_split'] += 1
            
            # Process each chunk
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} of {file_path}")
                
                # Prepare chunk-specific prompt
                chunk_prompt = self._prepare_chunk_prompt(prompt_template, chunk, i+1, len(chunks))
                
                # Process chunk
                chunk_result = self._inject_chunk(
                    file_path, chunk, chunk_prompt, with_context, provider_chain,
                    track_deps, context_depth, chunk_index=i
                )
                
                if chunk_result:
                    processed_chunks.append(chunk_result)
                    with self.lock:
                        self.results['chunks_processed'] += 1
                else:
                    logger.error(f"Failed to process chunk {i+1} of {file_path}")
            
            # Reassemble file if all chunks processed successfully
            if len(processed_chunks) == len(chunks):
                final_content = self._reassemble_chunks(processed_chunks, original_content)
                
                if apply:
                    save_output(file_path, final_content)
                    logger.info(f"Applied chunked injection to {file_path}")
                
                # Add to injection queue for dashboard
                injection_queue.add_injection_result(
                    file_path=file_path,
                    original_content=original_content,
                    injected_content=final_content,
                    status='success',
                    provider='chunked',
                    with_context=with_context
                )
                
                with self.lock:
                    self.results['successful_injections'].append({
                        'file': file_path,
                        'provider': 'chunked',
                        'chunks': len(chunks),
                        'with_context': with_context
                    })
            else:
                logger.error(f"Failed to process all chunks for {file_path}")
                with self.lock:
                    self.results['failed_injections'].append({
                        'file': file_path,
                        'error': f'Failed to process {len(chunks) - len(processed_chunks)} chunks'
                    })
        
        except Exception as e:
            logger.error(f"Error processing file chunks for {file_path}: {e}")
            with self.lock:
                self.results['failed_injections'].append({
                    'file': file_path,
                    'error': f'Chunk processing failed: {e}'
                })
    
    def _process_file_content(self, file_path: str, original_content: str, prompt_template: str,
                            apply: bool, with_context: bool, provider_chain: List[str],
                            track_deps: bool, context_depth: int):
        """Process a single file's content"""
        try:
            # Prepare context-aware prompt if needed
            if with_context and track_deps:
                enhanced_prompt = prepare_context_prompt(file_path, context_depth)
                final_prompt = f"{prompt_template}\n\n{enhanced_prompt}"
                logger.info(f"Prepared context-aware prompt for {file_path} (depth: {context_depth})")
            else:
                final_prompt = f"{prompt_template}\n\n{original_content}"
            
            # Run injection with provider chain
            modified_content = None
            used_provider = None
            
            for provider in provider_chain:
                try:
                    logger.info(f"Trying provider {provider} for {file_path}")
                    modified_content = run_injection(
                        source_code=original_content,
                        prompt_template=final_prompt,
                        file_path=file_path,
                        provider=provider
                    )
                    used_provider = provider
                    break
                except Exception as e:
                    logger.warning(f"Provider {provider} failed for {file_path}: {e}")
                    continue
            
            if modified_content is None:
                logger.error(f"All providers failed for {file_path}")
                with self.lock:
                    self.results['failed_injections'].append({
                        'file': file_path,
                        'error': 'All providers failed'
                    })
                return
            
            # Apply changes if requested
            if apply:
                save_output(file_path, modified_content)
                logger.info(f"Applied injection to {file_path}")
            
            # Add to injection queue for dashboard
            injection_queue.add_injection_result(
                file_path=file_path,
                original_content=original_content,
                injected_content=modified_content,
                status='success',
                provider=used_provider,
                with_context=with_context
            )
            
            with self.lock:
                self.results['successful_injections'].append({
                    'file': file_path,
                    'provider': used_provider,
                    'with_context': with_context
                })
                
                if with_context:
                    self.results['context_aware_count'] += 1
        
        except Exception as e:
            logger.error(f"Error processing file content for {file_path}: {e}")
            with self.lock:
                self.results['failed_injections'].append({
                    'file': file_path,
                    'error': str(e)
                })
    
    def _inject_chunk(self, file_path: str, chunk: Any, prompt_template: str, with_context: bool,
                     provider_chain: List[str], track_deps: bool, context_depth: int, chunk_index: int) -> Optional[str]:
        """Inject into a single chunk"""
        try:
            # Prepare chunk-specific prompt
            chunk_prompt = self._prepare_chunk_prompt(prompt_template, chunk, chunk_index + 1, 1)
            
            # Add context if needed
            if with_context and track_deps:
                context_prompt = prepare_context_prompt(file_path, context_depth)
                final_prompt = f"{chunk_prompt}\n\n{context_prompt}"
            else:
                final_prompt = f"{chunk_prompt}\n\n{chunk.content}"
            
            # Try providers
            for provider in provider_chain:
                try:
                    modified_content = run_injection(
                        source_code=chunk.content,
                        prompt_template=final_prompt,
                        file_path=f"{file_path}:chunk_{chunk_index}",
                        provider=provider
                    )
                    return modified_content
                except Exception as e:
                    logger.warning(f"Provider {provider} failed for chunk {chunk_index}: {e}")
                    continue
            
            return None
        
        except Exception as e:
            logger.error(f"Error injecting chunk {chunk_index}: {e}")
            return None
    
    def _prepare_chunk_prompt(self, base_prompt: str, chunk: Any, chunk_num: int, total_chunks: int) -> str:
        """Prepare a prompt specific to a chunk"""
        chunk_info = f"""
CHUNK INFORMATION:
- This is chunk {chunk_num} of {total_chunks} from the original file
- Chunk type: {chunk.chunk_type}
- Chunk name: {chunk.name}
- Lines: {chunk.start_line}-{chunk.end_line}

IMPORTANT: When modifying this chunk, maintain consistency with other chunks and the overall file structure.
"""
        
        return f"{base_prompt}\n\n{chunk_info}"
    
    def _reassemble_chunks(self, processed_chunks: List[str], original_content: str) -> str:
        """Reassemble processed chunks into final content"""
        # For now, simple concatenation - could be enhanced with proper merging
        return '\n\n'.join(processed_chunks)
    
    def _has_cached_result(self, file_path: str) -> bool:
        """Check if file has a cached strong result"""
        # This could be enhanced with actual caching logic
        return False


# Global enhanced injector instance
enhanced_injector = EnhancedRecursiveInjector()


def inject_directory_enhanced(
    directory: str,
    prompt_path: str,
    extensions: List[str] = None,
    recursive: bool = True,
    apply: bool = False,
    with_context: bool = True,
    provider_chain: List[str] = None,
    max_size: float = 10.0,
    exclude: List[str] = None,
    track_deps: bool = False,
    context_depth: int = 3,
    skip_known: bool = False,
    split_large: bool = False,
    dependency_graph: Dict[str, List[str]] = None,
    max_workers: int = 4
) -> Dict[str, Any]:
    """Convenience function for enhanced directory injection"""
    return enhanced_injector.inject_directory_enhanced(
        directory=directory,
        prompt_path=prompt_path,
        extensions=extensions,
        recursive=recursive,
        apply=apply,
        with_context=with_context,
        provider_chain=provider_chain,
        max_size=max_size,
        exclude=exclude,
        track_deps=track_deps,
        context_depth=context_depth,
        skip_known=skip_known,
        split_large=split_large,
        dependency_graph=dependency_graph,
        max_workers=max_workers
    ) 