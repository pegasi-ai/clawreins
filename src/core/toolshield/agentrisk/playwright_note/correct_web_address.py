#!/usr/bin/env python3
"""
Replace web addresses in MT-AgentRisk_ToolShield codebase.

Usage:
    python correct_web_address.py --domain_name example.com --suffix prod
    
This will replace:
    aa-0.chats-lab-gui-agent.uk -> sa-homepage-prod.example.com
"""

import argparse
from pathlib import Path

OLD_DOMAIN = "aa-0.chats-lab-gui-agent.uk"

def replace_in_file(filepath: Path, old: str, new: str) -> bool:
    """Replace old string with new in file. Returns True if changes were made."""
    try:
        content = filepath.read_text(encoding="utf-8")
        if old in content:
            new_content = content.replace(old, new)
            filepath.write_text(new_content, encoding="utf-8")
            return True
    except (UnicodeDecodeError, PermissionError):
        pass
    return False

def main():
    parser = argparse.ArgumentParser(description="Replace web addresses in codebase")
    parser.add_argument("--domain_name", required=True, help="Your domain (e.g., example.com)")
    parser.add_argument("--suffix", required=True, help="Your suffix (e.g., prod)")
    parser.add_argument("--root", default="MT-AgentRisk_ToolShield", help="Root directory to search")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    args = parser.parse_args()

    new_domain = f"sa-homepage-{args.suffix}.{args.domain_name}"
    root = Path(args.root)

    if not root.exists():
        print(f"Error: Directory {root} not found")
        return

    print(f"Replacing: {OLD_DOMAIN}")
    print(f"     With: {new_domain}")
    print(f"       In: {root}")
    print("-" * 50)

    # File extensions to search
    extensions = {".py", ".md", ".yml", ".yaml", ".json", ".toml", ".txt", ".sh"}
    
    changed_files = []
    for filepath in root.rglob("*"):
        if filepath.is_file() and filepath.suffix in extensions:
            if args.dry_run:
                try:
                    if OLD_DOMAIN in filepath.read_text(encoding="utf-8"):
                        changed_files.append(filepath)
                        print(f"[DRY RUN] Would modify: {filepath}")
                except (UnicodeDecodeError, PermissionError):
                    pass
            else:
                if replace_in_file(filepath, OLD_DOMAIN, new_domain):
                    changed_files.append(filepath)
                    print(f"Modified: {filepath}")

    print("-" * 50)
    print(f"Total files {'would be ' if args.dry_run else ''}modified: {len(changed_files)}")

if __name__ == "__main__":
    main()