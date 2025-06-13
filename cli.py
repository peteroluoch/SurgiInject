#!/usr/bin/env python3
"""
SurgiInject CLI - AI-powered code injection and modification tool
"""

import click
import os
import sys
import logging
from pathlib import Path
from typing import List
from engine.injector import run_injection
from engine.recursive import inject_dir
from engine.diff import show_diff
from engine.backup_engine import create_backup, list_backups, restore_backup, restore_latest_backup, get_backup_stats
from datetime import datetime
import chardet

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, environment variables may not be loaded")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("logs/cli.log"),
    logging.StreamHandler()
])
logger = logging.getLogger(__name__)

# Phase 3: API Key Safety Check
if not os.getenv("GROQ_API_KEY"):
    if not any("test" in arg.lower() for arg in sys.argv):
        click.echo("⚠️  GROQ_API_KEY not found - using mock responses", err=True)
        click.echo("💡 Get your free API key at https://console.groq.com", err=True)

@click.group()
def cli():
    """SurgiInject - AI-powered code injection and modification tool"""
    pass

@cli.command()
@click.option('--file', '-f', required=True, help='Target file to inject')
@click.option('--prompt', '-p', required=True, help='Prompt template file')
@click.option('--apply', is_flag=True, help='Apply the injection immediately')
@click.option('--preview-only', is_flag=True, help='Preview injection without applying')
@click.option('--with-context', is_flag=True, default=True, help='Use context-aware injection')
@click.option('--coordinated', is_flag=True, help='Use coordinated batch injection')
@click.option('--provider', default='auto', help='AI provider to use')
@click.option('--force', is_flag=True, help='Force injection even if file is already injected')
@click.option('--no-backup', is_flag=True, help='Skip automatic backup creation')
def inject(file, prompt, apply, preview_only, with_context, coordinated, provider, force, no_backup):
    """Inject AI-generated code into a file"""
    try:
        if preview_only:
            # Use diff engine for preview
            from engine.diff_engine import preview_injection
            
            click.echo(f"🔍 Previewing injection for {file}...")
            result = preview_injection(
                file_path=file,
                prompt_path=prompt,
                with_context=with_context
            )
            
            if "error" in result:
                click.echo(f"❌ Preview failed: {result['error']}", err=True)
                return 1
            
            if not result.get("has_changes", False):
                click.echo("ℹ️  No changes detected in preview.")
                return 0
            
            # Display diff
            click.echo(f"\n📊 Preview for {result['filename']}:")
            click.echo(f"📁 File: {result['filepath']}")
            click.echo(f"🧠 Context-aware: {'Yes' if result.get('with_context') else 'No'}")
            
            if result.get("diff_stats"):
                stats = result["diff_stats"]
                click.echo(f"📈 Changes: +{stats['additions']} -{stats['deletions']} ({stats['total_changes']} total)")
            
            click.echo("\n" + "="*60)
            click.echo("DIFF PREVIEW:")
            click.echo("="*60)
            
            if result.get("diff"):
                # Colorize diff output
                for line in result["diff"].split('\n'):
                    if line.startswith('+') and not line.startswith('+++'):
                        click.echo(click.style(line, fg='green'))
                    elif line.startswith('-') and not line.startswith('---'):
                        click.echo(click.style(line, fg='red'))
                    elif line.startswith('@@'):
                        click.echo(click.style(line, fg='blue', bold=True))
                    else:
                        click.echo(line)
            else:
                click.echo("No diff available")
            
            click.echo("="*60)
            click.echo("💡 Use --apply to apply these changes")
            return 0
        
        elif coordinated:
            # Use batch engine for coordinated injection
            from engine.batch_engine import batch_inject
            
            click.echo(f"🚀 Running coordinated batch injection...")
            result = batch_inject(
                files=[file],
                prompt_path=prompt,
                with_context=with_context,
                provider=provider,
                force=force
            )
            
            if result["success"]:
                click.echo(f"✅ Coordinated injection completed successfully!")
                click.echo(f"📊 Files processed: {result['total_files']}")
                click.echo(f"✅ Successful: {result['successful_injections']}")
                click.echo(f"❌ Failed: {result['failed_injections']}")
                
                if result.get("injected_files"):
                    click.echo("\n📁 Injected files:")
                    for injected_file in result["injected_files"]:
                        click.echo(f"  ✅ {injected_file}")
                
                if result.get("skipped_files"):
                    click.echo("\n⏭️  Skipped files:")
                    for skipped_file in result["skipped_files"]:
                        click.echo(f"  ⏭️  {skipped_file}")
                
                return 0
            else:
                click.echo(f"❌ Coordinated injection failed: {result.get('error', 'Unknown error')}", err=True)
                return 1
        
        elif with_context:
            # Use context-aware injection
            from engine.context_builder import inject_with_context
            
            click.echo(f"🧠 Running context-aware injection for {file}...")
            result = inject_with_context(
                file_path=Path(file),
                prompt_template=prompt,
                project_root=Path(file).parent,
                max_context_files=5
            )
            
            if apply:
                # Create backup before applying changes
                if not no_backup:
                    try:
                        backup_path = create_backup(file)
                        click.echo(f"🛡️  Backup created: {backup_path}")
                    except Exception as e:
                        click.echo(f"⚠️  Failed to create backup: {e}", err=True)
                        if not click.confirm("Continue without backup?"):
                            return 1
                
                # Write the result to file
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(result)
                click.echo(f"✅ Context-aware injection applied to {file}")
            else:
                click.echo(f"💡 Preview of context-aware injection for {file}:")
                click.echo("="*60)
                click.echo(result)
                click.echo("="*60)
                click.echo("💡 Use --apply to apply these changes")
            
            return 0
        
        else:
            # Use regular injection
            from engine.injector import run_injection
            
            click.echo(f"🚀 Running injection for {file}...")
            
            # Read the source file
            with open(file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Read the prompt template
            with open(prompt, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Run the injection
            result = run_injection(
                source_code=source_code,
                prompt_template=prompt_template,
                file_path=file,
                provider=provider,
                force=force
            )
            
            if apply:
                # Create backup before applying changes
                if not no_backup:
                    try:
                        backup_path = create_backup(file)
                        click.echo(f"🛡️  Backup created: {backup_path}")
                    except Exception as e:
                        click.echo(f"⚠️  Failed to create backup: {e}", err=True)
                        if not click.confirm("Continue without backup?"):
                            return 1
                
                # Write the result to file
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(result)
                click.echo(f"✅ Injection applied to {file}")
            else:
                click.echo(f"💡 Preview of injection for {file}:")
                click.echo("="*60)
                click.echo(result)
                click.echo("="*60)
                click.echo("💡 Use --apply to apply these changes")
            
            return 0
            
    except Exception as e:
        click.echo(f"❌ Injection failed: {e}", err=True)
        logger.error(f"Injection failed for {file}: {e}")
        return 1

@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--prompt", required=True, help="Path to prompt file")
@click.option("--extensions", "-e", multiple=True, default=[".py", ".js", ".ts", ".html", ".md", ".txt"], help="File extensions to process")
@click.option("--recursive", "-r", is_flag=True, default=True, help="Process subdirectories recursively")
@click.option("--apply", "-a", is_flag=True, help="Apply changes to files (default: preview only)")
@click.option("--with-context", is_flag=True, help="Include dependency context for better AI understanding")
@click.option("--provider-chain", multiple=True, default=["anthropic", "groq", "fallback"], help="AI providers to try in order")
@click.option("--max-size", default=10.0, help="Maximum file size in MB to process")
@click.option("--exclude", multiple=True, help="Directories to exclude (e.g., __pycache__, .git)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
# Phase 6.9: New dependency tracking options
@click.option("--track-deps", is_flag=True, help="Analyze and honor file dependencies")
@click.option("--context-depth", default=3, help="How deep to go in dependency context")
@click.option("--skip-known", is_flag=True, help="Skip files with cached strong results")
@click.option("--split-large", is_flag=True, help="Auto-chunk large files to fit token limits")
@click.option("--save-deps", is_flag=True, help="Save dependency map to .injectmap.json")
@click.option("--load-deps", help="Load dependency map from file")
def inject_dir(directory, prompt, extensions, recursive, apply, with_context, provider_chain, max_size, exclude, verbose, track_deps, context_depth, skip_known, split_large, save_deps, load_deps):
    """Inject AI-generated code into all files in a directory"""
    try:
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        click.echo(f"🚀 Starting directory injection for: {directory}")
        click.echo(f"📁 Extensions: {', '.join(extensions)}")
        click.echo(f"🧠 Context-aware: {'Yes' if with_context else 'No'}")
        click.echo(f"🔗 Track dependencies: {'Yes' if track_deps else 'No'}")
        
        # Phase 6.9: Load or build dependency graph
        dependency_graph = {}
        if track_deps:
            from engine.dependency_tracker import dependency_tracker
            
            if load_deps:
                click.echo(f"📋 Loading dependency map from: {load_deps}")
                if dependency_tracker.load_dependency_map(load_deps):
                    dependency_graph = dependency_tracker.dependency_graph
                    click.echo(f"✅ Loaded dependency map with {len(dependency_graph)} files")
                else:
                    click.echo("⚠️  Failed to load dependency map, building new one")
                    dependency_graph = dependency_tracker.build_dependency_graph(directory, extensions)
            else:
                click.echo("🔍 Building dependency graph...")
                dependency_graph = dependency_tracker.build_dependency_graph(directory, extensions)
            
            if save_deps:
                dependency_tracker.save_dependency_map()
        
        # Use enhanced recursive engine for Phase 6.9
        from engine.recursive_enhanced import inject_directory_enhanced
        
        result = inject_directory_enhanced(
            directory=directory,
            prompt_path=prompt,
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
            dependency_graph=dependency_graph
        )
        
        if result["success"]:
            click.echo(f"✅ Directory injection completed successfully!")
            click.echo(f"📊 Files processed: {result['total_files']}")
            click.echo(f"✅ Successful: {result['successful_injections']}")
            click.echo(f"❌ Failed: {result['failed_injections']}")
            click.echo(f"⏭️  Skipped: {result['skipped_files']}")
            
            if track_deps:
                click.echo(f"🔗 Dependency-aware injection: {result.get('dependency_aware', False)}")
                click.echo(f"🧠 Context depth used: {context_depth}")
            
            if split_large:
                click.echo(f"✂️  Large files split: {result.get('files_split', 0)}")
            
            if result.get("injected_files"):
                click.echo("\n📁 Injected files:")
                for injected_file in result["injected_files"]:
                    click.echo(f"  ✅ {injected_file}")
            
            if result.get("skipped_files_list"):
                click.echo("\n⏭️  Skipped files:")
                for skipped_file in result["skipped_files_list"]:
                    click.echo(f"  ⏭️  {skipped_file}")
            
            return 0
        else:
            click.echo(f"❌ Directory injection failed: {result.get('error', 'Unknown error')}", err=True)
            return 1
            
    except Exception as e:
        click.echo(f"❌ Directory injection failed: {e}", err=True)
        logger.error(f"Directory injection failed for {directory}: {e}")
        return 1

@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--extensions", "-e", multiple=True, default=[".py", ".js", ".ts", ".html", ".css", ".md"], help="File extensions to analyze")
@click.option("--output", "-o", default=".injectmap.json", help="Output file for dependency map")
@click.option("--visualize", is_flag=True, help="Generate a visual representation of dependencies")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed dependency analysis")
def track_deps(directory, extensions, output, visualize, verbose):
    """Analyze and track file dependencies in a directory"""
    try:
        from engine.dependency_tracker import dependency_tracker
        
        click.echo(f"🔍 Analyzing dependencies in: {directory}")
        click.echo(f"📁 Extensions: {', '.join(extensions)}")
        
        # Build dependency graph
        dependency_graph = dependency_tracker.build_dependency_graph(directory, extensions)
        
        # Save dependency map
        dependency_tracker.save_dependency_map(output)
        
        # Display analysis results
        click.echo(f"\n📊 Dependency Analysis Results:")
        click.echo(f"📁 Total files: {len(dependency_graph)}")
        
        # Count dependencies
        total_deps = sum(len(deps) for deps in dependency_graph.values())
        avg_deps = total_deps / len(dependency_graph) if dependency_graph else 0
        
        click.echo(f"🔗 Total dependencies: {total_deps}")
        click.echo(f"📈 Average dependencies per file: {avg_deps:.1f}")
        
        # Show injection order
        if dependency_tracker.injection_order:
            click.echo(f"\n🔄 Recommended injection order:")
            for i, file_path in enumerate(dependency_tracker.injection_order[:10], 1):
                click.echo(f"  {i:2d}. {file_path}")
            if len(dependency_tracker.injection_order) > 10:
                click.echo(f"  ... and {len(dependency_tracker.injection_order) - 10} more files")
        
        # Show files with most dependencies
        if verbose:
            files_by_deps = sorted(
                [(file, len(deps)) for file, deps in dependency_graph.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            click.echo(f"\n🔝 Files with most dependencies:")
            for file_path, dep_count in files_by_deps[:5]:
                click.echo(f"  📁 {file_path} ({dep_count} deps)")
                if dep_count > 0:
                    for dep in dependency_graph[file_path][:3]:
                        click.echo(f"    └─ {dep}")
                    if len(dependency_graph[file_path]) > 3:
                        click.echo(f"    └─ ... and {len(dependency_graph[file_path]) - 3} more")
        
        # Generate visualization if requested
        if visualize:
            try:
                from engine.dependency_visualizer import generate_dependency_graph
                viz_file = generate_dependency_graph(dependency_graph, directory)
                click.echo(f"\n📊 Dependency visualization saved to: {viz_file}")
            except ImportError:
                click.echo("⚠️  Visualization requires additional dependencies (matplotlib, networkx)")
        
        click.echo(f"\n✅ Dependency analysis complete!")
        click.echo(f"💾 Dependency map saved to: {output}")
        click.echo(f"💡 Use 'inject-dir {directory} --track-deps --load-deps {output}' for dependency-aware injection")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Dependency analysis failed: {e}", err=True)
        logger.error(f"Dependency analysis failed for {directory}: {e}")
        return 1

@cli.command()
@click.option('--file', '-f', required=True, help='File to restore from backup')
@click.option('--backup', '-b', help='Specific backup file to restore from (default: latest)')
@click.option('--list', '-l', is_flag=True, help='List available backups for the file')
@click.option('--force', is_flag=True, help='Force restore without confirmation')
def undo(file, backup, list, force):
    """Undo changes by restoring from backup"""
    try:
        file_path = Path(file)
        if not file_path.exists():
            click.echo(f"❌ File not found: {file}", err=True)
            return 1
        
        if list:
            # List available backups
            backups = list_backups(file_path.name)
            if not backups:
                click.echo(f"❌ No backups found for {file_path.name}")
                return 1
            
            click.echo(f"📁 Available backups for {file_path.name}:")
            for i, backup_file in enumerate(backups, 1):
                click.echo(f"  {i}. {backup_file}")
            return 0
        
        if backup:
            # Restore from specific backup
            if not force and not click.confirm(f"Restore {file} from backup {backup}?"):
                click.echo("Restore cancelled.")
                return 0
            
            success = restore_backup(file, backup)
            if success:
                click.echo(f"✅ File restored from {backup}")
            else:
                click.echo(f"❌ Failed to restore from {backup}", err=True)
                return 1
        else:
            # Restore from latest backup
            if not force and not click.confirm(f"Restore {file} from latest backup?"):
                click.echo("Restore cancelled.")
                return 0
            
            success = restore_latest_backup(file)
            if success:
                click.echo(f"✅ File restored from latest backup")
            else:
                click.echo(f"❌ Failed to restore from latest backup", err=True)
                return 1
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Undo failed: {e}", err=True)
        return 1

@cli.command()
@click.option('--stats', '-s', is_flag=True, help='Show backup statistics')
@click.option('--cleanup', '-c', is_flag=True, help='Clean up old backups (keep 5 most recent)')
@click.option('--file', '-f', help='Clean up backups for specific file')
def backups(stats, cleanup, file):
    """Manage backup files"""
    try:
        if stats:
            # Show backup statistics
            stats_data = get_backup_stats()
            click.echo("📊 Backup Statistics:")
            click.echo(f"  Total backups: {stats_data['total_backups']}")
            click.echo(f"  Total size: {stats_data['total_size']} bytes")
            click.echo(f"  Files with backups: {stats_data['files_with_backups']}")
            if stats_data['oldest_backup']:
                click.echo(f"  Oldest backup: {stats_data['oldest_backup']}")
            if stats_data['newest_backup']:
                click.echo(f"  Newest backup: {stats_data['newest_backup']}")
            
            if stats_data['backup_files']:
                click.echo(f"  Files with backups: {', '.join(stats_data['backup_files'])}")
        
        elif cleanup:
            if file:
                # Clean up backups for specific file
                from engine.backup_engine import cleanup_old_backups
                deleted_count = cleanup_old_backups(Path(file).name, keep_count=5)
                click.echo(f"🧹 Cleaned up {deleted_count} old backups for {file}")
            else:
                # Clean up all backups
                from engine.backup_engine import cleanup_old_backups
                total_deleted = 0
                stats_data = get_backup_stats()
                for backup_file in stats_data.get('backup_files', []):
                    deleted_count = cleanup_old_backups(backup_file, keep_count=5)
                    total_deleted += deleted_count
                click.echo(f"🧹 Cleaned up {total_deleted} old backups total")
        
        else:
            # Show help
            click.echo("Backup management commands:")
            click.echo("  --stats: Show backup statistics")
            click.echo("  --cleanup: Clean up old backups")
            click.echo("  --file <filename> --cleanup: Clean up backups for specific file")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Backup management failed: {e}", err=True)
        return 1

@cli.command()
@click.option('--stats', '-s', is_flag=True, help='Show retry and failure statistics')
@click.option('--clear', '-c', is_flag=True, help='Clear failure log')
@click.option('--export', '-e', help='Export failure report to file')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed failure information')
def retry_stats(stats, clear, export, verbose):
    """Manage retry engine and failure statistics"""
    try:
        from engine.retry_engine import get_retry_stats
        from engine.response_validator import validator
        
        if clear:
            if click.confirm("Clear all failure logs?"):
                validator.failure_log_path.unlink(missing_ok=True)
                click.echo("✅ Failure logs cleared")
            return 0
        
        if export:
            from engine.retry_engine import retry_engine
            retry_engine.export_failure_report(export)
            click.echo(f"✅ Failure report exported to {export}")
            return 0
        
        if stats:
            # Show retry statistics
            stats_data = get_retry_stats()
            
            click.echo("📊 Retry Engine Statistics:")
            click.echo(f"  Max attempts: {stats_data['max_attempts']}")
            click.echo(f"  Max providers: {stats_data['max_providers']}")
            click.echo(f"  Total failures: {stats_data['total_failures']}")
            
            if stats_data['total_failures'] > 0:
                click.echo("\n🔍 Provider Failures:")
                for provider, count in stats_data['providers'].items():
                    click.echo(f"  {provider}: {count} failures")
                
                click.echo("\n📁 File Failures:")
                for file_path, count in stats_data['files'].items():
                    click.echo(f"  {file_path}: {count} failures")
                
                if verbose and stats_data['recent_failures']:
                    click.echo("\n🕒 Recent Failures:")
                    for failure in stats_data['recent_failures'][:5]:
                        click.echo(f"  {failure['timestamp']} - {failure['provider']} failed for {failure['file']}")
                        click.echo(f"    Reason: {failure['reason'][:100]}...")
                        click.echo()
            else:
                click.echo("  🎉 No failures recorded!")
            
            return 0
        
        # Default: show help
        click.echo("Retry engine management commands:")
        click.echo("  --stats: Show retry and failure statistics")
        click.echo("  --clear: Clear failure log")
        click.echo("  --export <file>: Export failure report")
        click.echo("  --verbose: Show detailed failure information")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Retry stats failed: {e}", err=True)
        return 1

if __name__ == '__main__':
    cli()
