# SurgiInject

🚀 **SurgiInject** is an AI-powered CLI tool for precise code injection and modification using intelligent prompt templating.

## Features

- **AI-Powered Code Modification**: Leverages AI models to intelligently modify source code
- **Prompt Templating**: Consistent, structured prompts for reliable AI interactions
- **Safe Preview Mode**: Shows diffs before applying changes
- **Multi-Language Support**: Works with Python, JavaScript, Java, and many other languages
- **Backup & Recovery**: Automatic backup creation before modifications
- **Extensible Architecture**: Easy to add new AI model providers

## Installation

1. Clone or download SurgiInject to your project directory
2. Ensure you have Python 3.10+ installed
3. The tool uses standard library modules, so no additional dependencies are required for basic functionality

## Quick Start

### Basic Usage

```bash
# Show what changes would be made (safe preview mode)
python cli.py inject --file mycode.py --prompt prompts/fix_mobile_blank_bug.txt

# Apply changes directly to the file
python cli.py inject --file mycode.py --prompt prompts/fix_mobile_blank_bug.txt --apply

# Verbose output for debugging
python cli.py inject --file mycode.py --prompt prompts/fix_mobile_blank_bug.txt --verbose
