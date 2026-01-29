# MarkLatex

A lightweight desktop application for academics to grade PDF assignments with styled text annotations.

## Features

- **Batch Processing**: Recursively load all PDFs from a folder
- **Non-Destructive Editing**: Annotations saved in separate `.mlat` files, original PDFs remain untouched
- **Custom Styled Text**: Add annotations with custom fonts, sizes, and text wrapping
- **LaTeX Support**: Render mathematical formulas using Matplotlib
- **Smart Export**: Automatically expand PDF canvas if annotations go out of bounds
- **Enhanced Navigation**: Use Page Up/Down keys for easy page switching
- **High DPI Rendering**: Sharp annotations at 300 DPI

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
   - Select a folder containing PDF files
   - The application will load all PDFs recursively

4. **Add Annotations**
   - Double-click on any PDF page to add a new annotation
   - Customize font, size, and text wrapping in the dialog
   - Drag annotations to reposition them
   - Double-click existing annotations to edit them

5. **Export Marked PDFs**
   - Click "Export PDF" to save a new PDF with all annotations
   - The exported file will have `_marked.pdf` suffix

## User Interface

- **Left Sidebar**: List of PDF files in the selected folder
- **Main Area**: PDF page display with annotations
- **Toolbar**: Navigation buttons and folder selection
- **Keyboard Shortcuts**:
  - `Page Up/Down`: Navigate between pages
  - `Delete`: Remove selected annotations
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
- No undo/redo functionality (coming soon)
- Stylus support is limited

## License

This project is open source. Feel free to contribute or modify for your needs.