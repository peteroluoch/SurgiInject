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
from engine.recursive import inject_directory
from engine.diff import show_diff
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
@click.option('--file', '-f', required=True, help='Path to source file to modify')
@click.option('--prompt', '-p', required=True, help='Prompt name or path to prompt template file. If the prompt contains spaces and no file matches, it is treated as an inline prompt.')
@click.option('--apply', '-a', is_flag=True, help='Apply changes to file (default: show diff only)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--provider', '-pr', default='auto', type=click.Choice(['anthropic', 'groq-mixtral', 'groq-gemma', 'groq-llama', 'auto']), help='Specify the provider to use')
@click.option('--force', is_flag=True, help='Force injection even if duplicate prompt is detected')
@click.option('--encoding', default='utf-8', help='Specify the file encoding')
@click.option('--debug', is_flag=True, help='Enable debug mode for detailed logs')
@click.option('--no-cache', is_flag=True, help='Disable cache usage')
@click.option('--force-refresh', is_flag=True, help='Force refresh even if result is cached')
def inject(file, prompt, apply, verbose, provider, force, encoding, debug, no_cache, force_refresh):
    """
    Inject AI-powered modifications into a source file using a prompt template.
    """

    try:
        # Validate source file
        if not os.path.exists(file):
            click.echo(f"❌ Error: Source file '{file}' not found", err=True)
            sys.exit(1)

        # Resolve prompt path or use inline prompt
        if ' ' in prompt or not os.path.isfile(os.path.join("prompts", f"{prompt}.txt")):
            prompt_template = prompt
        else:
            prompt_path = os.path.join("prompts", f"{prompt}.txt")
            prompt_template = read_input_file(prompt_path)

        if verbose:
            click.echo(f"🔍 Using prompt: {prompt_template}")

        # Read source code with encoding handling
        source_code = read_input_file(file)

        if debug:
            logger.setLevel(logging.DEBUG)

        if verbose:
            click.echo(f"📖 Reading source file: {file}")

        # Handle provider selection
        if provider == 'auto':
            provider = auto_select_provider()
        click.echo(f"Selected provider: {provider}")

        # Check for duplicate prompt
        prompt_hash = hash(prompt_template)
        if not force and is_duplicate(prompt_hash):
            click.echo("⚠️ Prompt already injected previously. Use --force to override.")
            return

        # Run AI injection
        if verbose:
            click.echo("🚀 Running AI injection...")
        modified_code = run_injection(source_code, prompt_template, file_path=file, provider=provider, force=force)

        # Output results
        if apply:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(modified_code)
            click.echo(f"✅ Changes applied to {file}")
        else:
            click.echo("📋 Proposed changes:")
            show_diff(source_code, modified_code, file)
            click.echo("\n💡 Use --apply to write these changes to the file")

        # Log injection details
        logger.info(f"✅ Injected: {provider} | Tokens used: ~{len(source_code)} | Timestamp: {datetime.now()}")

    except KeyboardInterrupt:
        click.echo("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--path', '-p', required=True, help='Path to directory to process')
@click.option('--prompt', '-pr', required=True, help='Path to prompt template file')
@click.option('--extensions', '-e', multiple=True, default=['.py', '.html', '.js', '.css', '.txt'], help='File extensions to process')
@click.option('--recursive', '-r', is_flag=True, default=True, help='Process subdirectories recursively')
@click.option('--apply', '-a', is_flag=True, help='Apply changes to files (default: show diffs only)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--max-size', default=10.0, help='Maximum file size in MB to process')
@click.option('--exclude', multiple=True, help='Directories to exclude (e.g., __pycache__, .git)')
def inject_dir(path, prompt, extensions, recursive, apply, verbose, max_size, exclude):
    """
    Inject AI-powered modifications into all files in a directory.
    
    This command processes multiple files recursively, applying the same prompt
    to each file that matches the specified extensions.
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
        
        # Set default exclusions if none provided
        if not exclude:
            exclude = ['__pycache__', '.git', '.venv', 'node_modules', '.pytest_cache']
            
        # Run directory injection
        results = inject_directory(
            directory_path=path,
            prompt_path=prompt,
            extensions=list(extensions),
            recursive=recursive,
            apply_changes=apply,
            verbose=verbose
        )
        
        # Display results
        click.echo(f"\n🎯 Injection Results:")
        click.echo(f"📊 Total files processed: {results['total_files']}")
        click.echo(f"✅ Successful: {results['successful']}")
        click.echo(f"❌ Failed: {results['failed']}")
        
        if results['failed'] > 0:
            click.echo(f"\n❌ Failed files:")
            for failed in results['failed_files']:
                click.echo(f"   - {failed['file']}: {failed['error']}")
                
        if results['successful'] > 0:
            click.echo(f"\n✅ Successfully processed:")
            for success in results['injected_files']:
                click.echo(f"   - {success['file']}")
                
        # Log summary
        logger.info(f"Directory injection complete: {results['successful']}/{results['total_files']} files processed in {path}")
        
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
