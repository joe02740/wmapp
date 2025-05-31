#!/usr/bin/env python3
"""
Simple Project Structure Analyzer
Drop this script into any project directory to get a quick overview.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

def get_file_size_human_readable(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

def should_ignore(path, ignore_patterns):
    """Check if path should be ignored"""
    path_str = str(path).lower()
    for pattern in ignore_patterns:
        if pattern in path_str:
            return True
    return False

def extract_dependencies_from_requirements(project_root):
    """Extract dependencies from requirements.txt files"""
    deps = set()
    req_files = ['requirements.txt', 'requirements-dev.txt', 'pyproject.toml', 'setup.py', 'Pipfile']
    
    for req_file in req_files:
        req_path = project_root / req_file
        if req_path.exists():
            try:
                with open(req_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if req_file == 'requirements.txt' or req_file == 'requirements-dev.txt':
                        for line in content.split('\n'):
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Extract package name (before == or >= etc.)
                                package = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].strip()
                                if package:
                                    deps.add(package)
                    elif req_file == 'package.json':
                        try:
                            data = json.loads(content)
                            if 'dependencies' in data:
                                deps.update(data['dependencies'].keys())
                            if 'devDependencies' in data:
                                deps.update(data['devDependencies'].keys())
                        except json.JSONDecodeError:
                            pass
            except Exception:
                pass
    
    return sorted(list(deps))

def get_project_type(project_root, files, dirs):
    """Determine project type based on files present"""
    project_types = []
    
    # Check for specific files
    if 'package.json' in files:
        project_types.append('Node.js')
    if 'requirements.txt' in files or 'setup.py' in files or 'pyproject.toml' in files:
        project_types.append('Python')
    if 'Cargo.toml' in files:
        project_types.append('Rust')
    if 'go.mod' in files:
        project_types.append('Go')
    if 'pom.xml' in files or 'build.gradle' in files:
        project_types.append('Java')
    if 'Dockerfile' in files:
        project_types.append('Docker')
    
    # Check for frameworks in directories
    if 'node_modules' in dirs:
        project_types.append('Node.js')
    if any(d in dirs for d in ['venv', 'env', '__pycache__']):
        if 'Python' not in project_types:
            project_types.append('Python')
    
    return project_types if project_types else ['Unknown']

def analyze_project(project_root=None):
    """Analyze project structure and generate report"""
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root)
    
    # Common ignore patterns
    ignore_patterns = [
        'node_modules', '__pycache__', '.git', '.vscode', '.idea',
        'venv', 'env', '.env', 'dist', 'build', '.next',
        '.cache', 'coverage', '.pytest_cache', '.mypy_cache',
        'target', 'bin', 'obj', '.vs'
    ]
    
    stats = {
        'total_files': 0,
        'total_dirs': 0,
        'total_size': 0,
        'file_extensions': Counter(),
        'largest_files': [],
        'directories': [],
        'files_by_dir': defaultdict(list)
    }
    
    # Walk through directory
    for root, dirs, files in os.walk(project_root):
        root_path = Path(root)
        relative_root = root_path.relative_to(project_root)
        
        # Skip ignored directories
        if should_ignore(relative_root, ignore_patterns):
            continue
        
        # Filter out ignored subdirectories
        dirs[:] = [d for d in dirs if not should_ignore(root_path / d, ignore_patterns)]
        
        stats['total_dirs'] += len(dirs)
        
        for file in files:
            file_path = root_path / file
            
            if should_ignore(file_path, ignore_patterns):
                continue
            
            try:
                size = file_path.stat().st_size
                stats['total_files'] += 1
                stats['total_size'] += size
                
                # File extension
                ext = file_path.suffix.lower() if file_path.suffix else '(no extension)'
                stats['file_extensions'][ext] += 1
                
                # Track files by directory
                rel_dir = str(relative_root) if str(relative_root) != '.' else 'root'
                stats['files_by_dir'][rel_dir].append({
                    'name': file,
                    'size': size,
                    'size_human': get_file_size_human_readable(size)
                })
                
                # Track largest files
                stats['largest_files'].append({
                    'path': str(file_path.relative_to(project_root)),
                    'size': size,
                    'size_human': get_file_size_human_readable(size)
                })
                
            except (OSError, PermissionError):
                continue
    
    # Sort largest files
    stats['largest_files'].sort(key=lambda x: x['size'], reverse=True)
    stats['largest_files'] = stats['largest_files'][:10]  # Top 10
    
    # Get project info
    root_files = [f.name for f in project_root.iterdir() if f.is_file()]
    root_dirs = [f.name for f in project_root.iterdir() if f.is_dir() and not should_ignore(f, ignore_patterns)]
    
    project_types = get_project_type(project_root, root_files, root_dirs)
    dependencies = extract_dependencies_from_requirements(project_root)
    
    return stats, project_types, dependencies, root_files, root_dirs

def generate_report(project_root=None, output_file=None):
    """Generate and save project analysis report"""
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root)
    
    if output_file is None:
        output_file = project_root / f"{project_root.name}_structure.md"
    
    stats, project_types, dependencies, root_files, root_dirs = analyze_project(project_root)
    
    # Generate report
    report = []
    report.append(f"# Project Analysis: {project_root.name}")
    report.append(f"\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Base path: `{project_root}`")
    
    # Project overview
    report.append(f"\n## Project Overview")
    report.append(f"**Type**: {', '.join(project_types)}")
    report.append(f"**Total Files**: {stats['total_files']}")
    report.append(f"**Total Directories**: {stats['total_dirs']}")
    report.append(f"**Total Size**: {get_file_size_human_readable(stats['total_size'])}")
    
    # Dependencies
    if dependencies:
        report.append(f"\n## Dependencies ({len(dependencies)})")
        dep_chunks = [dependencies[i:i+5] for i in range(0, len(dependencies), 5)]
        for chunk in dep_chunks:
            report.append(f"- {' • '.join(chunk)}")
    
    # File extensions
    if stats['file_extensions']:
        report.append(f"\n## File Types")
        for ext, count in stats['file_extensions'].most_common(10):
            report.append(f"- **{ext}**: {count} files")
    
    # Root structure
    report.append(f"\n## Root Directory")
    report.append(f"**Files**: {', '.join(root_files[:10])}")
    if len(root_files) > 10:
        report.append(f"... and {len(root_files) - 10} more files")
    
    report.append(f"\n**Directories**: {', '.join(root_dirs)}")
    
    # Directory structure (simplified tree)
    report.append(f"\n## Directory Structure")
    report.append("```")
    for dir_path, files in sorted(stats['files_by_dir'].items()):
        if dir_path == 'root':
            report.append(f"{project_root.name}/")
            for file_info in sorted(files, key=lambda x: x['name'])[:5]:  # Show first 5 files
                report.append(f"  ├── {file_info['name']} ({file_info['size_human']})")
            if len(files) > 5:
                report.append(f"  └── ... and {len(files) - 5} more files")
        else:
            report.append(f"{dir_path}/")
            for file_info in sorted(files, key=lambda x: x['name'])[:3]:  # Show first 3 files per dir
                report.append(f"  ├── {file_info['name']} ({file_info['size_human']})")
            if len(files) > 3:
                report.append(f"  └── ... and {len(files) - 3} more files")
    report.append("```")
    
    # Largest files
    if stats['largest_files']:
        report.append(f"\n## Largest Files")
        for file_info in stats['largest_files'][:5]:
            report.append(f"- **{file_info['path']}**: {file_info['size_human']}")
    
    # Write report
    report_content = '\n'.join(report)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"✅ Report generated: {output_file}")
        return str(output_file)
    except Exception as e:
        print(f"❌ Error writing report: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    # Get project path from command line or use current directory
    project_path = sys.argv[1] if len(sys.argv) > 1 else None
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("🔍 Analyzing project structure...")
    result = generate_report(project_path, output_path)
    
    if result:
        print(f"📁 Analysis complete! Check: {result}")
    else:
        print("❌ Failed to generate report")