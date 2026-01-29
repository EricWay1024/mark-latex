Here is a comprehensive developer guide (`DEVELOPER.md`) for your **MarkLatex** project. This document explains the architecture, data structures, and the specific design decisions we made (like the transparency hit-test fix).

---

# MarkLatex: Developer Documentation

## 1. Project Overview

**MarkLatex** is a lightweight, high-performance desktop tool designed for academics to grade PDF assignments. Unlike standard PDF editors, it treats styled text as a first-class citizen, rendering mathematical formulas and custom-styled text on the fly without requiring a local TeX installation.

**Key Features:**

* **Batch Processing:** Recursively loads all PDFs in a target folder, supporting both PDF and SVG rendering.
* **Moodle Folder Mode:** Detects Moodle-unzipped submission folders and labels PDFs by student name.
* **Non-Destructive:** Saves annotations in a lightweight JSON sidecar file (`.mlat`), keeping the original PDF untouched until export.
* **LaTeX Support:** Renders math using `matplotlib`'s internal engine.
* **Smart Export:** Automatically expands the PDF canvas if annotations go out of bounds.
* **Export All:** Batch-export all loaded PDFs and warn about unmarked files.
* **Undo:** Per-PDF undo stack (max depth 20) with Ctrl+Z + toolbar button.
* **Remarks Tree:** Sidebar shows remark subitems under each PDF for quick navigation.

## 2. Technology Stack

| Component | Library | Purpose |
| --- | --- | --- |
| **GUI Framework** | `PyQt6` | Handles the main window, graphics scene, events, and sidebars. |
| **PDF Engine** | `PyMuPDF` (fitz) | High-speed PDF rendering (for display) and modification (for export). |
| **Math Rendering** | `Matplotlib` | Renders LaTeX strings to transparent PNGs in memory with custom font support. |
| **Text Processing** | `TextWrap` | Handles character-limit wrapping for annotations. |

## 3. Architecture & Data Flow

The application follows a **Model-View-Controller (MVC)** pattern, though streamlined for a single-file script.

### Data Structure: The `.mlat` Sidecar

We do not modify the PDF during the grading process. Instead, we maintain a state dictionary `self.all_marks` and sync it to a JSON file. The sidecar includes font, size, and width properties for each annotation.

**Schema (`filename.mlat`):**
```json
{
  "pdf_path": "C:/Path/To/Student_Homework.pdf",
  "all_marks": {
    "0": [  // Page Index (Integer)
      {
        "text": "Correct, but $\\delta$ is small.",
        "x": 150.5,
        "y": 300.2,
        "font": "Fira Code",
        "size": 12,
        "width": 50
      }
    ],
    "1": [ ... ]
  }
}
```

```json
{
  "pdf_path": "C:/Path/To/Student_Homework.pdf",
  "all_marks": {
    "0": [  // Page Index (Integer)
      {
        "text": "Correct, but $\\delta$ is small.",
        "x": 150.5,
        "y": 300.2,
        "font": "Fira Code",
        "size": 12,
        "width": 50
      }
    ],
    "1": [ ... ]
  }
}

```

### The Rendering Pipeline

1. **User Input:** User double-clicks -> `MarkPropertiesDialog` captures text/settings.
2. **Generation:** `render_latex()` creates a Matplotlib figure (0 alpha background).
3. **Rasterization:** The figure is saved to an in-memory `io.BytesIO` buffer as a PNG.
4. **Display:** The buffer is converted to a `QImage` -> `QPixmap` -> `LatexItem` and placed on the `QGraphicsScene`.

## 4. Key Classes

### `MarkLatexApp` (Main Window)

* **`load_file_by_index(i)`:** Handles the "context switch." It triggers `save_sidecar()` for the current file, clears the scene, loads the new PDF, and repopulates annotations from the new `.mlat` file. Also resets the per-PDF undo stack.
* **`render_current_page()`:** Renders the PDF page as a background image using SVG-based rendering. Uses natural PDF coordinates (1:1 mapping) without scaling.
* **`refresh_remark_tree()`:** Reads `.mlat` data across all PDFs and rebuilds the sidebar with remark subitems ordered by page and y-position.

### `LatexItem` (The Annotation Object)

Inherits from `QGraphicsPixmapItem`.

* **The "Transparency Fix":** By default, Qt ignores clicks on transparent pixels. We override the `shape()` method to return the full bounding rectangle `QPainterPath`.
```python
def shape(self):
    path = QPainterPath()
    path.addRect(self.boundingRect())
    return path
```

* **Callbacks:** Takes an `on_change_callback` (now `save_and_refresh`) to persist edits and update the remark tree, plus an optional undo callback.
* **Enhanced Interaction:** Supports double-click editing via `MarkPropertiesDialog` and keyboard navigation with Page Up/Down keys.

## 5. The "Tricky" Logic

### A. Boundary Expansion (Export)

When exporting, we cannot simply stamp images because students often write to the very edge of the page, forcing graders to write in the margins.

**The Algorithm:**

1. Iterate through all marks on a page.
2. Calculate the "bounding box" of all annotations.
3. Compare this against the PDF's `Page.rect` (MediaBox).
4. If marks extend beyond the MediaBox (e.g., negative X or Y > height), we call `page.set_mediabox(...)` to grow the physical page dimensions before saving.
* **DPI Conversion:** Export handles DPI conversion from 300 DPI rendering to PDF points (72 DPI) for accurate sizing.

### B. Matplotlib Agg Backend

We explicitly call `matplotlib.use('Agg')` at the start.

* *Reason:* Matplotlib defaults to interactive backends (like TkAgg or QtAgg). Since we are running our own PyQt loop, letting Matplotlib try to spawn its own window logic causes thread conflicts and crashes. `Agg` forces it to be a headless image generator only.
* **High DPI Rendering:** Uses RENDER_DPI constant (300 DPI) for sharp annotation rendering.

### C. Moodle Folder Mode

When the selected folder contains submission subfolders (and no PDFs at root), the app switches to Moodle mode:

1. Each subfolder name is used as the student label (split at the first underscore for display).
2. Every PDF in each subfolder is loaded and listed under its student label.
3. Exported PDFs are saved to:
   `parent\marked\<root>\<student_subfolder>\<original>_marked.pdf`.

### D. Export All

The `Export All` action loops over every loaded PDF, exports a marked copy, and reports any PDFs that have no marks (empty or missing `.mlat`).

### E. Undo Stack

The undo system records add/edit/move/delete actions (max depth 20) per PDF and can be triggered via Ctrl+Z or the toolbar button.

## 6. Setup & Installation

**Requirements:**
Create a `requirements.txt`:

```txt
PyQt6
PyMuPDF
matplotlib
```

**Running the App:**

```bash
python main.py
```

**Packaging for Distribution:**
To create a standalone `.exe` for Windows:

```bash
pyinstaller --noconsole --onefile --name="MarkLatex" main.py
```

## 7. Future Roadmap / Known Limits

* **Memory:** Currently, the app keeps the `all_marks` dictionary in memory. For massive datasets (1000s of PDFs), we might want to release non-active file data.
* **Undo/Redo:** Currently, we only support "Delete". Implementing a `QUndoStack` would be the next major feature.
* **Stylus Support:** The `ScrollHandDrag` was disabled to allow clicking. Re-enabling gesture support for tablet users would require differentiating between "Touch Move" and "Mouse Click."
* **Enhanced Navigation:** Added Page Up/Down keyboard navigation for easier page switching.
* **Custom Styling:** Support for custom fonts, sizes, and text wrapping in annotations.
