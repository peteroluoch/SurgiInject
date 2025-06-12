#!/usr/bin/env python3
"""
SurgiInject CLI - AI-powered code injection and modification tool
"""

import click
import os
import sys
from pathlib import Path
from engine.injector import run_injection
from engine.diff import show_diff

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
@click.option('--prompt', '-p', required=True, help='Prompt name or path to prompt template file')
@click.option('--apply', '-a', is_flag=True, help='Apply changes to file (default: show diff only)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def inject(file, prompt, apply, verbose):
    """
    Inject AI-powered modifications into a source file using a prompt template.
    """

    try:
        # Validate source file
        if not os.path.exists(file):
            click.echo(f"❌ Error: Source file '{file}' not found", err=True)
            sys.exit(1)

        # Resolve prompt path
        if os.path.isfile(prompt):
            prompt_path = prompt
        else:
            prompt_path = os.path.join("prompts", f"{prompt}.txt")

        if verbose:
            click.echo(f"🔍 Using prompt path: {prompt_path}")

        if not os.path.exists(prompt_path):
            click.echo(f"❌ Error: Prompt template '{prompt}' not found at {prompt_path}", err=True)
            sys.exit(1)

        # Read source code
        if verbose:
            click.echo(f"📖 Reading source file: {file}")
        with open(file, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Read prompt template
        if verbose:
            click.echo(f"📋 Reading prompt template: {prompt_path}")
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Run AI injection
        if verbose:
            click.echo("🚀 Running AI injection...")
        modified_code = run_injection(source_code, prompt_template, file_path=file)

        # Output results
        if apply:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(modified_code)
            click.echo(f"✅ Changes applied to {file}")
        else:
            click.echo("📋 Proposed changes:")
            show_diff(source_code, modified_code, file)
            click.echo("\n💡 Use --apply to write these changes to the file")

    except KeyboardInterrupt:
        click.echo("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli()
