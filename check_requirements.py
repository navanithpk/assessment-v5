#!/usr/bin/env python
"""
Check if all imported packages are in requirements.txt
"""
import os
import re
from pathlib import Path

# Standard library modules (don't need to be in requirements.txt)
STDLIB_MODULES = {
    'abc', 'argparse', 'ast', 'base64', 'collections', 'copy', 'csv',
    'datetime', 'decimal', 'difflib', 'enum', 'functools', 'getpass',
    'hashlib', 'io', 'itertools', 'json', 'logging', 'math', 'os',
    'pathlib', 'pickle', 're', 'shutil', 'statistics', 'string', 'sys',
    'tempfile', 'threading', 'time', 'typing', 'unittest', 'uuid',
    'warnings', 'weakref', 'xml', '__future__'
}

# Django modules (included with Django)
DJANGO_MODULES = {'django'}

# Project modules
PROJECT_MODULES = {'core', 'assessment_v3'}

def extract_imports_from_file(filepath):
    """Extract all import statements from a Python file"""
    imports = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Match "import xxx" or "from xxx import yyy"
                if line.startswith('import '):
                    module = line.split()[1].split('.')[0].split(',')[0]
                    imports.add(module)
                elif line.startswith('from '):
                    module = line.split()[1].split('.')[0]
                    imports.add(module)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return imports

def get_all_imports(directory):
    """Get all imports from all Python files in directory"""
    all_imports = set()
    for py_file in Path(directory).rglob('*.py'):
        if '__pycache__' not in str(py_file) and 'venv' not in str(py_file):
            imports = extract_imports_from_file(py_file)
            all_imports.update(imports)
    return all_imports

def read_requirements(requirements_file):
    """Read package names from requirements.txt"""
    packages = set()
    try:
        with open(requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before ==, >=, etc.)
                    package = re.split(r'[=<>!]', line)[0].strip()
                    packages.add(package.lower())
    except FileNotFoundError:
        print(f"Requirements file not found: {requirements_file}")
    return packages

def main():
    # Get all imports from the project
    print("Scanning project for imports...")
    all_imports = get_all_imports('.')

    # Filter out standard library and Django modules
    third_party_imports = {
        imp for imp in all_imports
        if imp not in STDLIB_MODULES
        and imp not in DJANGO_MODULES
        and imp not in PROJECT_MODULES
    }

    print(f"\nFound {len(third_party_imports)} third-party packages:")
    for imp in sorted(third_party_imports):
        print(f"  - {imp}")

    # Read requirements.txt
    print("\nReading requirements.txt...")
    requirements = read_requirements('requirements.txt')

    print(f"\nPackages in requirements.txt:")
    for pkg in sorted(requirements):
        print(f"  - {pkg}")

    # Package name mapping (import name -> package name)
    PACKAGE_MAP = {
        'PIL': 'pillow',
        'fitz': 'pymupdf',
        'google': 'google-auth',
        'google_auth_oauthlib': 'google-auth-oauthlib',
    }

    # Check for missing packages
    print("\n" + "="*60)
    missing = []
    for imp in third_party_imports:
        package_name = PACKAGE_MAP.get(imp, imp).lower()
        # Check various naming conventions
        if not any(pkg.lower() in [package_name, imp.lower(), package_name.replace('-', '_')]
                   or package_name in pkg.lower() or imp.lower() in pkg.lower()
                   for pkg in requirements):
            missing.append(imp)

    if missing:
        print("❌ MISSING PACKAGES IN requirements.txt:")
        for pkg in sorted(missing):
            suggested_name = PACKAGE_MAP.get(pkg, pkg)
            print(f"  - {pkg} (add: {suggested_name})")
    else:
        print("✅ All imported packages are in requirements.txt!")

    print("="*60)

if __name__ == '__main__':
    main()
