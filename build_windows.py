#!/usr/bin/env python3
"""
Windows build script for MarkLatex application using PyInstaller.
This script creates a standalone .exe file for distribution.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True

def create_icon():
    """Create a simple icon file for the application."""
    import tempfile
    from PIL import Image, ImageDraw
    
    # Create a simple icon (if PIL is available)
    try:
        # Create 256x256 icon
        img = Image.new('RGB', (256, 256), color='#2c3e50')
        d = ImageDraw.Draw(img)
        
        # Draw a document icon with LaTeX symbol
        d.rectangle([40, 40, 216, 216], fill='#ecf0f1')
        d.rectangle([40, 40, 80, 216], fill='#34495e')
        
        # Draw LaTeX symbol
        d.ellipse([100, 100, 156, 156], fill='#e74c3c')
        d.line([128, 100, 128, 156], fill='white', width=4)
        d.line([100, 128, 156, 128], fill='white', width=4)
        
        icon_path = Path("marklatex.ico")
        img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print(f"Created icon: {icon_path}")
        return str(icon_path)
    except ImportError:
        print("PIL not available, using default icon")
        return None

def build_executable():
    """Build the standalone executable using PyInstaller."""
    
    # Check if PyInstaller is available
    if not check_pyinstaller():
        return False
    
    # Create icon if possible
    icon_path = create_icon()
    
    # PyInstaller command arguments
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--name=MarkLatex",
        "--windowed",  # No console window
        "--onefile",   # Single executable
        "--clean",     # Clean PyInstaller cache
        "--noconfirm", # Don't prompt for overwrite
    ]
    
    # Add icon if created
    if icon_path:
        pyinstaller_args.extend(["--icon", icon_path])
    
    # Add hidden imports (PyInstaller might miss these)
    hidden_imports = [
        "fitz",  # PyMuPDF
        "matplotlib.backends.backend_agg",
        "matplotlib.font_manager",
        "matplotlib.pyplot",
        "matplotlib.text",
        "matplotlib.transforms",
        "matplotlib.path",
        "matplotlib.patches",
        "matplotlib.backend_bases",
        "matplotlib.figure",
        "matplotlib._layoutbox",
        "matplotlib._tight_bbox",
        "matplotlib._tight_layout",
        "matplotlib._constrained_layout",
        "matplotlib._blocking_input",
        "matplotlib._c_internal_utils",
        "matplotlib._docstring",
        "matplotlib._enums",
        "matplotlib._fontconfig_pattern",
        "matplotlib._image",
        "matplotlib._layoutgrid",
        "matplotlib._mathtext",
        "matplotlib._mathtext_data",
        "matplotlib._path",
        "matplotlib._pylab_helpers",
        "matplotlib._qhull",
        "matplotlib._text_helpers",
        "matplotlib._ttconv",
        "matplotlib._type1font",
        "matplotlib._version",
        "matplotlib.afm",
        "matplotlib.artist",
        "matplotlib.axes",
        "matplotlib.axis",
        "matplotlib.backend_managers",
        "matplotlib.backend_tools",
        "matplotlib.bezier",
        "matplotlib.blocking_input",
        "matplotlib.category",
        "matplotlib.cbook",
        "matplotlib.cm",
        "matplotlib.collections",
        "matplotlib.colorbar",
        "matplotlib.colors",
        "matplotlib.container",
        "matplotlib.contour",
        "matplotlib.dates",
        "matplotlib.dviread",
        "matplotlib.figure",
        "matplotlib.font_manager",
        "matplotlib.gridspec",
        "matplotlib.hatch",
        "matplotlib.image",
        "matplotlib.layout_engine",
        "matplotlib.legend",
        "matplotlib.legend_handler",
        "matplotlib.lines",
        "matplotlib.markers",
        "matplotlib.mathtext",
        "matplotlib.mlab",
        "matplotlib.offsetbox",
        "matplotlib.patches",
        "matplotlib.path",
        "matplotlib.patheffects",
        "matplotlib.projections",
        "matplotlib.quiver",
        "matplotlib.rcsetup",
        "matplotlib.scale",
        "matplotlib.spines",
        "matplotlib.stackplot",
        "matplotlib.streamplot",
        "matplotlib.style",
        "matplotlib.table",
        "matplotlib.texmanager",
        "matplotlib.text",
        "matplotlib.textpath",
        "matplotlib.ticker",
        "matplotlib.tight_bbox",
        "matplotlib.tight_layout",
        "matplotlib.transforms",
        "matplotlib.tri",
        "matplotlib.type1font",
        "matplotlib.units",
        "matplotlib.widgets",
    ]
    
    for imp in hidden_imports:
        pyinstaller_args.extend(["--hidden-import", imp])
    
    # Add data files (fonts, etc.)
    pyinstaller_args.extend([
        "--add-data", "C:\\Windows\\Fonts\\FiraCode-Regular.ttf;.",
        "--add-data", "C:\\Windows\\Fonts\\FiraCode-Bold.ttf;.",
        "--add-data", "C:\\Windows\\Fonts\\FiraCode-Medium.ttf;.",
        "--add-data", "C:\\Windows\\Fonts\\FiraCode-SemiBold.ttf;.",
    ])
    
    # Add main script
    pyinstaller_args.append("main.py")
    
    print("Building MarkLatex executable...")
    print("PyInstaller command:", " ".join(pyinstaller_args))
    
    try:
        # Run PyInstaller
        result = subprocess.run(pyinstaller_args, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(result.stdout)
        
        # Find the executable
        dist_dir = Path("dist")
        exe_file = dist_dir / "MarkLatex.exe"
        
        if exe_file.exists():
            print(f"Executable created: {exe_file}")
            print(f"File size: {exe_file.stat().st_size / (1024*1024):.2f} MB")
            return True
        else:
            print("Warning: Executable not found in expected location")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def create_installer():
    """Create a simple installer using NSIS (if available)."""
    try:
        # Check if makensis is available
        result = subprocess.run(["makensis", "/VERSION"], capture_output=True)
        if result.returncode == 0:
            print("NSIS found, creating installer...")
            create_nsis_script()
            return True
    except FileNotFoundError:
        print("NSIS not found, skipping installer creation")
    
    return False

def create_nsis_script():
    """Create NSIS script for installer."""
    nsis_script = """!define APP_NAME "MarkLatex"
!define APP_VERSION "1.0"
!define APP_PUBLISHER "MarkLatex Team"
!define APP_EXE "MarkLatex.exe"
!define INSTALLER_NAME "MarkLatex_Installer.exe"

SetCompressor /SOLID lzma

!include "MUI2.nsh"

!define MUI_ABORTWARNING

VIProductVersion  1.0.0.0
VIAddVersionKey ProductName "${APP_NAME}"
VIAddVersionKey ProductVersion "${APP_VERSION}"
VIAddVersionKey CompanyName "${APP_PUBLISHER}"
VIAddVersionKey FileVersion "${APP_VERSION}"
VIAddVersionKey FileDescription "${APP_NAME}"
VIAddVersionKey LegalCopyright "Copyright (c) ${APP_PUBLISHER}"

Name "${APP_NAME}"
OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES\\${APP_NAME}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOverwrite ifnewer
    SetOutPath "$INSTDIR"
    File "dist\\${APP_EXE}"
    File "README.md"
    File "LICENSE"
    
    CreateDirectory "$SMPROGRAMS\\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}"
    CreateShortCut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}"
    
    WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\\${APP_EXE}"
    Delete "$INSTDIR\\README.md"
    Delete "$INSTDIR\\LICENSE"
    Delete "$INSTDIR\\uninstall.exe"
    
    Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"
    Delete "$DESKTOP\\${APP_NAME}.lnk"
    RmDir "$SMPROGRAMS\\${APP_NAME}"
    
    RmDir "$INSTDIR"
SectionEnd
"""
    
    with open("installer.nsi", "w") as f:
        f.write(nsis_script)
    
    print("NSIS script created: installer.nsi")
    print("To build installer, run: makensis installer.nsi")

def main():
    """Main build function."""
    print("MarkLatex Windows Build Script")
    print("=" * 40)
    
    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    print(f"Working directory: {script_dir}")
    
    # Build executable
    if build_executable():
        print("\n✓ Executable build completed successfully!")
        
        # Try to create installer
        if create_installer():
            print("✓ Installer script created!")
        else:
            print("ℹ Installer creation skipped (NSIS not available)")
            
        print("\nNext steps:")
        print("1. Test the executable: dist\\MarkLatex.exe")
        print("2. If using NSIS: run 'makensis installer.nsi' to create installer")
        print("3. Distribute the .exe file or installer")
        
    else:
        print("\n✗ Build failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())