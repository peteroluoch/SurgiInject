#!/usr/bin/env python3
"""
Simple argparse-based CLI for SurgiInject (Phase 2 implementation)
"""

import argparse
from engine import injector
from engine.diff import generate_diff

def main():
    parser = argparse.ArgumentParser(description="SurgiInject CLI")
    parser.add_argument("--file", required=True, help="Target source file")
    parser.add_argument("--prompt", required=True, help="Prompt file")
    parser.add_argument("--apply", action="store_true", help="Apply injection to file")
    args = parser.parse_args()

    with open(args.file, 'r', encoding='utf-8') as f:
        original_code = f.read()

    modified_code = injector.run_injection_from_files(args.file, args.prompt)

    if args.apply:
        with open(args.file, 'w', encoding='utf-8') as f:
            f.write(modified_code)
        print("[✅] Code injected and file updated.")
    else:
        diff_text = generate_diff(original_code, modified_code, args.file)
        print(diff_text)

if __name__ == "__main__":
    main()