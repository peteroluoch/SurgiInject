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

@click.group()
def cli():
    """SurgiInject - AI-powered code injection and modification tool"""
    pass

@cli.command()
@click.option('--file', '-f', required=True, help='Path to source file to modify')
@click.option('--prompt', '-p', required=True, help='Path to prompt template file')
@click.option('--apply', '-a', is_flag=True, help='Apply changes to file (default: show diff only)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def inject(file, prompt, apply, verbose):
    """
    Inject AI-powered modifications into a source file using a prompt template.
    
    By default, shows a diff of proposed changes.
    Use --apply to write changes directly to the file.
    """
    try:
        # Validate input files exist
        if not os.path.exists(file):
            click.echo(f"❌ Error: Source file '{file}' not found", err=True)
            sys.exit(1)
            
        if not os.path.exists(prompt):
            click.echo(f"❌ Error: Prompt template '{prompt}' not found", err=True)
            sys.exit(1)
        
        # Read source file
        if verbose:
            click.echo(f"📖 Reading source file: {file}")
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            click.echo(f"❌ Error reading source file: {e}", err=True)
            sys.exit(1)
        
        # Read prompt template
        if verbose:
            click.echo(f"📋 Reading prompt template: {prompt}")
            
        try:
            with open(prompt, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except Exception as e:
            click.echo(f"❌ Error reading prompt template: {e}", err=True)
            sys.exit(1)
        
        # Run injection
        if verbose:
            click.echo("🚀 Running AI injection...")
            
        try:
            modified_code = run_injection(source_code, prompt_template, file_path=file)
        except Exception as e:
            click.echo(f"❌ Error during injection: {e}", err=True)
            sys.exit(1)
        
        # Handle output
        if apply:
            # Write changes to file
            try:
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(modified_code)
                click.echo(f"✅ Changes applied to {file}")
            except Exception as e:
                click.echo(f"❌ Error writing to file: {e}", err=True)
                sys.exit(1)
        else:
            # Show diff
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
