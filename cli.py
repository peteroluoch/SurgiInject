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
            
    except FileNotFoundError as e:
        click.echo(f"❌ File not found: {e}", err=True)
        return 1
    except Exception as e:
        click.echo(f"❌ Injection failed: {e}", err=True)
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
@click.option('--path', '-p', required=True, help='Path to directory to process')
@click.option('--prompt', '-pr', required=True, help='Path to prompt template file')
@click.option('--extensions', '-e', multiple=True, default=['.py', '.html', '.js', '.css', '.txt'], help='File extensions to process')
@click.option('--recursive', '-r', is_flag=True, default=True, help='Process subdirectories recursively')
@click.option('--apply', '-a', is_flag=True, help='Apply changes to files (default: show diffs only)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--max-size', default=10.0, help='Maximum file size in MB to process')
@click.option('--exclude', multiple=True, help='Directories to exclude (e.g., __pycache__, .git)')
@click.option('--with-context', is_flag=True, help='Include dependency context for Python files')
@click.option('--project-root', help='Root directory of the project for context analysis')
def inject_dir(path, prompt, extensions, recursive, apply, verbose, max_size, exclude, with_context, project_root):
    """
    Inject AI-powered modifications into all files in a directory.
    
    This command processes multiple files recursively, applying the same prompt
    to each file that matches the specified extensions.
    
    When --with-context is used, Python files will include dependency context
    from imported modules to provide better AI understanding of the codebase.
    """
    
    try:
        # Validate directory
        if not os.path.exists(path):
            click.echo(f"❌ Error: Directory '{path}' not found", err=True)
            sys.exit(1)
            
        if not os.path.isdir(path):
            click.echo(f"❌ Error: '{path}' is not a directory", err=True)
            sys.exit(1)
            
        # Validate prompt file
        if not os.path.exists(prompt):
            click.echo(f"❌ Error: Prompt file '{prompt}' not found", err=True)
            sys.exit(1)
            
        click.echo(f"🚀 Starting directory injection in: {path}")
        click.echo(f"📁 Extensions: {list(extensions)}")
        click.echo(f"🔄 Recursive: {recursive}")
        click.echo(f"💾 Apply changes: {apply}")
        click.echo(f"🧠 With context: {with_context}")
        
        if with_context:
            project_root_path = project_root if project_root else path
            click.echo(f"📂 Project root for context: {project_root_path}")
        
        # Set default exclusions if none provided
        if not exclude:
            exclude = ['__pycache__', '.git', '.venv', 'node_modules', '.pytest_cache']
            
        # Run directory injection
        results = inject_dir(
            path=path,
            prompt_path=prompt,
            extensions=list(extensions),
            recursive=recursive,
            with_context=with_context,
            project_root=project_root
        )
        
        # Display results
        click.echo(f"\n🎯 Injection Results:")
        click.echo(f"📊 Total files processed: {len(results['injected']) + len(results['skipped']) + len(results['failed'])}")
        click.echo(f"✅ Successfully injected: {len(results['injected'])}")
        click.echo(f"⏭️ Skipped (already injected): {len(results['skipped'])}")
        click.echo(f"❌ Failed: {len(results['failed'])}")
        
        if with_context:
            context_files = [f for f in results['injected'] if f.endswith('.py')]
            click.echo(f"🧠 Context-aware injections: {len(context_files)}")
        
        if results['failed']:
            click.echo(f"\n❌ Failed files:")
            for failed in results['failed']:
                click.echo(f"   - {failed}")
                
        if results['injected']:
            click.echo(f"\n✅ Successfully injected:")
            for success in results['injected']:
                context_indicator = " 🧠" if with_context and success.endswith('.py') else ""
                click.echo(f"   - {success}{context_indicator}")
                
        if results['skipped']:
            click.echo(f"\n⏭️ Skipped (already had marker):")
            for skipped in results['skipped']:
                click.echo(f"   - {skipped}")
                
        # Log summary
        logger.info(f"Directory injection complete: {len(results['injected'])}/{len(results['injected']) + len(results['skipped']) + len(results['failed'])} files processed in {path}")
        
    except KeyboardInterrupt:
        click.echo("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)

# Function to read input file with encoding detection
def read_input_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError as e:
        print(f"⚠️ UTF-8 decoding failed for {path}: {e}")
        # Attempt to detect encoding
        try:
            with open(path, 'rb') as f:
                raw = f.read()
                detected = chardet.detect(raw)
                fallback_encoding = detected.get("encoding", "utf-8")
                print(f"🔍 Detected fallback encoding: {fallback_encoding}")
                return raw.decode(fallback_encoding, errors="replace")
        except Exception as inner_e:
            print(f"❌ Failed to read file with fallback encoding: {inner_e}")
            raise RuntimeError(f"Unable to read file: {path}")

# Function to check for duplicate prompts
def is_duplicate(prompt_hash):
    # Use SQLite or JSON to track hashes
    return False

# Function to auto-select provider
def auto_select_provider():
    # Implement provider selection logic
    return 'anthropic'

if __name__ == '__main__':
    cli()
