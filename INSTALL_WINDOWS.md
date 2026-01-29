# MarkLatex Windows Installation Guide

## Quick Start

### Option 1: Download Pre-built Executable (Recommended)
1. Go to the [GitHub Releases page](https://github.com/yourusername/mark-latex/releases)
2. Download the latest `MarkLatex.exe` file
3. Double-click to run the application
4. No installation required!

### Option 2: Build from Source
1. Install Python 3.10 or later from [python.org](https://python.org)
2. Download this repository
3. Open Command Prompt and navigate to the project folder
4. Run: `python build_simple.py`
5. Find the executable in the `dist/` folder

## System Requirements

- **Operating System**: Windows 10, 11, or later
- **Architecture**: 64-bit system recommended
- **Disk Space**: At least 60 MB for the executable
- **Dependencies**: None (all dependencies are bundled)

## First Time Setup

### Visual C++ Redistributable (If Needed)
If you get an error about missing Visual C++ libraries:
1. Download from Microsoft: https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Run the installer
3. Restart your computer if prompted
4. Try running MarkLatex.exe again

### Font Support
The application includes support for Fira Code font. If you want additional fonts:
1. Install your preferred fonts in Windows
2. The application will automatically detect and use them

## Using MarkLatex

### Basic Workflow
1. **Open Folder**: Click "Open Folder" and select a folder containing PDFs
2. **Add Annotations**: Double-click on a page to add text annotations
3. **Customize**: Use the dialog to set font, size, and text wrapping
4. **Export**: Click "Export PDF" to save a marked version

### Keyboard Shortcuts
- **Page Up/Down**: Navigate between pages
- **Delete**: Remove selected annotations
- **Ctrl+Z**: Undo last action
- **Ctrl+Mouse Wheel**: Zoom in/out
- **Shift+Mouse Wheel**: Horizontal scrolling

### Features
- **Batch Processing**: Load all PDFs from a folder at once
- **Moodle Support**: Automatically detects Moodle submission folders
- **LaTeX Math**: Render mathematical formulas using $...$ syntax
- **Custom Styling**: Choose fonts, sizes, and text wrapping
- **Non-destructive**: Original PDFs remain unchanged
- **Export All**: Batch export all marked PDFs

## Troubleshooting

### Common Issues

**"Application failed to start"**
- Install Visual C++ Redistributable (link above)
- Ensure you're running a 64-bit version of Windows

**"Missing DLL" errors**
- Update Windows to the latest version
- Install Visual C++ Redistributable

**"Font not found"**
- The application uses system fonts
- Install additional fonts if needed

**"Large file size"**
- The executable is ~60-80 MB because it includes all dependencies
- This is normal for standalone Python applications

### Performance Tips
- For large PDFs, consider processing in smaller batches
- Close other applications if experiencing slow performance
- The application works best with PDFs under 50 pages

## File Locations

### Application Data
- **Settings**: Stored in the application folder as `.mlat` files
- **Temporary Files**: Automatically cleaned up on exit
- **Exported PDFs**: Saved in the same folder as the original with `_marked.pdf` suffix

### Folder Structure
```
YourProjectFolder/
├── student1_assignment.pdf
├── student1_assignment.mlat    # Annotation data
├── student1_assignment_marked.pdf  # Exported with annotations
├── student2_assignment.pdf
├── student2_assignment.mlat
└── student2_assignment_marked.pdf
```

## Security Notes

- The executable is built with PyInstaller and includes all dependencies
- No internet connection is required during normal operation
- The application only reads and writes files in the selected folder
- All annotation data is stored locally in `.mlat` files

## Getting Help

### Documentation
- **Main README**: General information and features
- **DEVELOPER.md**: Technical details and architecture
- **This file**: Windows-specific installation and usage

### Support
- Report issues on GitHub: [Issues page](https://github.com/yourusername/mark-latex/issues)
- Check the [Wiki](https://github.com/yourusername/mark-latex/wiki) for tips and tricks

## Uninstallation

Since this is a portable application:
1. Simply delete the `MarkLatex.exe` file
2. Delete any `.mlat` files if you no longer need annotation data
3. No registry entries or system files are modified

## Version Information

- **Current Version**: 1.0
- **Build Date**: See GitHub releases
- **Compatibility**: Windows 10+ (64-bit)
- **License**: See LICENSE file in repository

## Contributing

If you'd like to contribute:
1. Fork the repository on GitHub
2. Create a feature branch
3. Submit a pull request

For more details, see the CONTRIBUTING.md file (if available).