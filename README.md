# MarkLatex

A lightweight desktop application for academics to grade PDF assignments with styled text annotations.

## Features

- **Batch Processing**: Recursively load all PDFs from a folder
- **Moodle Folder Support**: Detect Moodle-style submission folders and label PDFs by student name
- **Non-Destructive Editing**: Annotations saved in separate `.mlat` files, original PDFs remain untouched
- **Custom Styled Text**: Add annotations with custom fonts, sizes, and text wrapping
- **LaTeX Support**: Render mathematical formulas using Matplotlib
- **Smart Export**: Automatically expand PDF canvas if annotations go out of bounds
- **Export All**: Batch-export all PDFs and warn about unmarked files
- **Undo**: Ctrl+Z and toolbar undo button for per-PDF edits (max depth 20)
- **Enhanced Navigation**: Use Page Up/Down keys for easy page switching
- **High DPI Rendering**: Sharp annotations at 300 DPI
- **Remarks Tree**: Sidebar shows remark subitems under each PDF for quick jumping

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install PyQt6 PyMuPDF matplotlib
   ```

2. **Run the Application**
   ```bash
   python main.py
   ```

3. **Open a Folder**
   - Click "Open Folder" in the toolbar
   - Select a folder containing PDF files, or a Moodle-unzipped submission folder
   - The application will load all PDFs recursively or map Moodle submissions by student

4. **Add Annotations**
   - Double-click on any PDF page to add a new annotation
   - Customize font, size, and text wrapping in the dialog
   - Drag annotations to reposition them
   - Double-click existing annotations to edit them

5. **Export Marked PDFs**
   - Click "Export PDF" to save a new PDF with all annotations
   - Click "Export All" to export every PDF in the list (warnings shown for unmarked files)
   - Exported files use the `_marked.pdf` suffix

## User Interface

- **Left Sidebar**: Tree of PDFs with remark subitems (click a remark to jump to its page)
- **Main Area**: PDF page display with annotations
- **Toolbar**: Navigation buttons, Moodle mode indicator, export tools, and undo
- **Keyboard Shortcuts**:
  - `Page Up/Down`: Navigate between pages
  - `Delete`: Remove selected annotations
  - `Ctrl+Z`: Undo last change (per PDF)
  - `Ctrl + Mouse Wheel`: Zoom in/out
  - `Shift + Mouse Wheel`: Horizontal scrolling

## File Structure

- **Main Application**: `main.py`
- **Developer Documentation**: `DEVELOPER.md`
- **Dependencies**: Listed in `requirements.txt`

## Export Process

When exporting, the application:
1. Renders each annotation as a transparent PNG
2. Places annotations at their specified coordinates
3. Expands the PDF canvas if annotations extend beyond page boundaries
4. Saves the result as a new PDF file

## Requirements

- Python 3.7+
- PyQt6
- PyMuPDF (fitz)
- Matplotlib

## Known Issues

- Memory usage increases with large numbers of PDFs
- Stylus support is limited

## License

This project is open source. Feel free to contribute or modify for your needs.