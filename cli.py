#!/usr/bin/env python3
"""
SurgiInject CLI - AI-powered code injection and modification tool
"""

import click
import os
import sys
import logging
from pathlib import Path
from engine.injector import run_injection
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
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

        if verbose:
            click.echo(f"🔍 Using prompt: {prompt_template}")

        # Read source code with encoding handling
        try:
            with open(file, 'rb') as f:
                raw_data = f.read(1000)
                detected_encoding = chardet.detect(raw_data)['encoding']
                encoding_to_use = encoding if encoding else detected_encoding
                if verbose:
                    click.echo(f"Detected encoding: {encoding_to_use}")
                f.seek(0)
                source_code = f.read().decode(encoding_to_use)
        except UnicodeDecodeError:
            click.echo(f"❌ Error decoding file {file} with encoding {encoding_to_use}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            if debug:
                raise
            sys.exit(1)

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
        modified_code = run_injection(source_code, prompt_template, file_path=file, provider=provider, no_cache=no_cache, force_refresh=force_refresh)

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
