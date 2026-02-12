#!/usr/bin/env python3
"""
Simple Windows build script for MarkLatex using PyInstaller.
This creates a standalone .exe file for distribution.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Build the MarkLatex executable."""
    print("MarkLatex Windows Build Script")
    print("=" * 40)
    
    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    print(f"Working directory: {script_dir}")
    
    # Check if main.py exists
    if not Path("main.py").exists():
        print("Error: main.py not found!")
        return 1
    
    # PyInstaller command
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=MarkLatex",
        "--windowed",      # No console window
        "--onefile",       # Single executable
        "--clean",         # Clean PyInstaller cache
        "--noconfirm",     # Don't prompt for overwrite
        "--hidden-import=fitz",  # PyMuPDF
        "--hidden-import=matplotlib.backends.backend_agg",
        "--hidden-import=matplotlib.font_manager",
        "--hidden-import=matplotlib.pyplot",
        "--hidden-import=matplotlib.text",
        "--hidden-import=matplotlib.transforms",
        "--hidden-import=matplotlib.path",
        "--hidden-import=matplotlib.patches",
        "--hidden-import=matplotlib.backend_bases",
        "--hidden-import=matplotlib.figure",
        "main.py"
    ]
    
    print("Building MarkLatex executable...")
    print("Command:", " ".join(pyinstaller_cmd))
    
    try:
        # Run PyInstaller
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        
        # Show output
        if result.stdout:
            print("Output:", result.stdout)
        
        # Find the executable
        dist_dir = Path("dist")
        exe_file = dist_dir / "MarkLatex.exe"
        
        if exe_file.exists():
            size_mb = exe_file.stat().st_size / (1024*1024)
            print(f"Executable created: {exe_file}")
            print(f"  File size: {size_mb:.1f} MB")
            print(f"  Location: {exe_file.absolute()}")
            
            # Create a simple README for distribution
            create_distribution_readme(exe_file, size_mb)
            
            return 0
        else:
            print("Warning: Executable not found in expected location")
            return 1
            
    except subprocess.CalledProcessError as e:
        print("Build failed!")
        print(f"Error: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

def create_distribution_readme(exe_file, size_mb):
    """Create a README for distribution."""
    readme_content = f"""# MarkLatex Windows Installation

## Quick Start
1. Download `MarkLatex.exe` from this folder
2. Double-click the executable to run the application
3. No installation required - it's a standalone application!

## System Requirements
- Windows 10 or later
- 64-bit system recommended
- At least {size_mb:.1f} MB of free disk space

## Features
- Batch process PDF assignments
- LaTeX math rendering support
- Custom font and styling options
- Export marked PDFs with annotations

## Troubleshooting
If you get an error about missing Visual C++ Redistributable:
1. Download from Microsoft: https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Install the redistributable
3. Try running MarkLatex.exe again

## Notes
- The application creates `.mlat` files to save your annotations
- Original PDFs are never modified during editing
- Use the Export function to create marked PDFs

For more information, see the main README.md file.
"""
    
    readme_path = Path("MarkLatex_README.txt")
    with open(readme_path, "w") as f:
        f.write(readme_content)
    
    print(f"Created distribution README: {readme_path}")

if __name__ == "__main__":
    sys.exit(main())