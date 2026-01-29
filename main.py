import sys
import json
import io
import os
import textwrap
import fitz  # PyMuPDF
import matplotlib
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QFileDialog, QToolBar, 
                             QMessageBox, QGraphicsItem, QLabel, QDockWidget, QListWidget,
                             QWidget, QVBoxLayout, QDialog, QTextEdit, QPushButton, 
                             QDialogButtonBox, QSpinBox, QComboBox, QFormLayout, QHBoxLayout,
                             QSlider)
from PyQt6.QtGui import QPixmap, QImage, QAction, QColor, QFont, QFontDatabase, QPainterPath
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import Qt, QBuffer, QIODevice, QByteArray

# Use Agg backend for headless rendering
matplotlib.use('Agg')

# --- Defaults ---
DEFAULT_FONT = "Fira Code"
DEFAULT_SIZE = 10
DEFAULT_WRAP = 30  # Characters before wrapping
RENDER_DPI = 300  # DPI for Matplotlib rendering

class CustomGraphicsView(QGraphicsView):
    """Custom QGraphicsView that supports horizontal scrolling with Shift + mouse wheel."""
    def __init__(self, scene=None):
        super().__init__(scene)
    
    def keyPressEvent(self, event):
        """Handle Page Up/Page Down keys for page navigation."""
        # Check if the main window has a method for page navigation
        parent = self.parent()
        if hasattr(parent, 'prev_page') and hasattr(parent, 'next_page'):
            if event.key() == Qt.Key.Key_PageUp:
                parent.prev_page()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_PageDown:
                parent.next_page()
                event.accept()
                return
        # For other keys, let the parent handle them
        super().keyPressEvent(event)
    
    def wheelEvent(self, event):
        """Handle mouse wheel events with Shift key for horizontal scrolling and Ctrl key for zooming."""
        # Check if Ctrl key is pressed for zooming
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Get the scroll amount (positive = down, negative = up)
            delta = event.angleDelta().y()
            
            # Calculate zoom factor (positive delta = zoom in, negative = zoom out)
            zoom_factor = 1.1 if delta > 0 else 1.0 / 1.1
            
            # Get the cursor position relative to the view
            cursor_pos = event.position()
            
            # Map cursor position to scene coordinates before zoom
            old_pos = self.mapToScene(cursor_pos.toPoint())
            
            # Apply zoom
            self.scale(zoom_factor, zoom_factor)
            
            # Adjust scroll bars to keep cursor position fixed
            new_pos = self.mapToScene(cursor_pos.toPoint())
            delta_pos = new_pos - old_pos
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() + delta_pos.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() + delta_pos.y()))
            
            # Accept the event to prevent default scrolling
            event.accept()
        # Check if Shift key is pressed for horizontal scrolling
        elif event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Get the current horizontal scroll bar
            h_scroll = self.horizontalScrollBar()
            
            # Get the scroll amount (positive = down, negative = up)
            # Convert vertical scroll to horizontal scroll
            delta = event.angleDelta().y()
            
            # Apply the scroll (invert direction to match natural scrolling)
            current_value = h_scroll.value()
            new_value = current_value - delta
            
            # Set the new scroll position
            h_scroll.setValue(new_value)
            
            # Accept the event to prevent default vertical scrolling
            event.accept()
        else:
            # If no modifier keys are pressed, use default vertical scrolling behavior
            super().wheelEvent(event)

class MarkPropertiesDialog(QDialog):
    """Dialog to edit Text + Styling Options."""
    # Predefined common marks
    PREDEFINED_MARKS = ["correct", "nice", "good", "important", "review", "check"]

    def __init__(self, parent=None, title="Mark",
                 initial_text="",
                 initial_font=DEFAULT_FONT,
                 initial_size=DEFAULT_SIZE,
                 initial_width=DEFAULT_WRAP):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 1. Common Marks Selection
        self.mark_combo = QComboBox()
        self.mark_combo.addItems(self.PREDEFINED_MARKS)
        self.mark_combo.currentTextChanged.connect(self.on_mark_selected)
        layout.addWidget(self.mark_combo)

        # 2. Text Area
        self.text_edit = QTextEdit()
        # Set initial text from combo box if no initial text provided
        if not initial_text and self.PREDEFINED_MARKS:
            initial_text = self.PREDEFINED_MARKS[0]
        self.text_edit.setPlainText(initial_text)
        # Use a monospaced font for the editor itself
        editor_font = QFont("Consolas", 11)
        if "Fira Code" in QFontDatabase.families():
            editor_font = QFont("Fira Code", 11)
        self.text_edit.setFont(editor_font)
        layout.addWidget(self.text_edit)
        
        # 2. Options Area
        form_layout = QFormLayout()

        # Font Selection
        self.font_combo = QComboBox()
        # Populate with common code/math fonts
        common_fonts = ["Fira Code", "Consolas", "Courier New", "Arial", "Times New Roman"]
        # Add system fonts that match our list
        installed = QFontDatabase.families()
        for f in common_fonts:
            if f in installed:
                self.font_combo.addItem(f)
        # Fallback if preferred fonts aren't found
        if self.font_combo.count() == 0:
            self.font_combo.addItem("Monospace")

        self.font_combo.setCurrentText(initial_font)
        form_layout.addRow("Font:", self.font_combo)
        
        # Size Selection
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(5, 50)
        self.size_slider.setValue(initial_size)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setTickInterval(5)

        # Size value label
        self.size_label = QLabel(f"{initial_size} pt")
        self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Layout for slider and label
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_label)

        form_layout.addRow("Text Size:", size_layout)

        # Connect slider to update label
        self.size_slider.valueChanged.connect(lambda value: self.size_label.setText(f"{value} pt"))
        
        # Width Selection
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(10, 200)
        self.width_slider.setValue(initial_width)
        self.width_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.width_slider.setTickInterval(20)

        # Width value label
        self.width_label = QLabel(f"{initial_width} chars")
        self.width_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Layout for slider and label
        width_layout = QHBoxLayout()
        width_layout.addWidget(self.width_slider)
        width_layout.addWidget(self.width_label)

        form_layout.addRow("Max Width:", width_layout)

        # Connect slider to update label
        self.width_slider.valueChanged.connect(lambda value: self.width_label.setText(f"{value} chars"))
        
        layout.addLayout(form_layout)
        
        # 3. Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def on_mark_selected(self, text):
        """Update text field when a mark is selected from the dropdown."""
        self.text_edit.setPlainText(text)

    def get_data(self):
        return {
            "text": self.text_edit.toPlainText(),
            "font": self.font_combo.currentText(),
            "size": self.size_slider.value(),
            "width": self.width_slider.value()
        }

class LatexItem(QGraphicsPixmapItem):
    """Movable, editable LaTeX annotation with custom styling."""
    def __init__(self, mark_data, render_func, on_change_callback):
        super().__init__()
        self.mark_data = mark_data 
        self.render_func = render_func
        self.on_change_callback = on_change_callback
        
        self.setPos(mark_data['x'], mark_data['y'])
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        # Apply scaling to match 72 DPI scene coordinates with 300 DPI rendered image
        self.setScale(72 / RENDER_DPI)
        self.update_image()

    def update_image(self):
        pixmap = self.render_func(self.mark_data)
        self.setPixmap(pixmap)

    # --- THE FIX: Force the hit-box to be the full rectangle ---
    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path
    # -----------------------------------------------------------

    def mouseDoubleClickEvent(self, event):
        dialog = MarkPropertiesDialog(None, "Edit Mark", 
                                      self.mark_data['text'],
                                      self.mark_data.get('font', DEFAULT_FONT),
                                      self.mark_data.get('size', DEFAULT_SIZE),
                                      self.mark_data.get('width', DEFAULT_WRAP))
        if dialog.exec():
            new_data = dialog.get_data()
            if new_data['text']:
                self.mark_data.update(new_data)
                self.update_image()
                self.on_change_callback()
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        self.mark_data['x'] = self.x()
        self.mark_data['y'] = self.y()
        super().mouseReleaseEvent(event)
        self.on_change_callback()

class MarkLatexApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarkLatex V5 - Styled Text")
        self.resize(1400, 900)

        # -- State --
        self.file_list = []
        self.current_file_index = -1
        self.doc = None
        self.pdf_path = None
        self.current_page_idx = 0
        self.all_marks = {}
        # Removed view_scale - now using natural PDF coordinates (1:1 mapping)

        # -- UI --
        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene)
        self.setCentralWidget(self.view)
        
        self.create_toolbar()
        self.create_sidebar()
        
        self.scene.mouseDoubleClickEvent = self.scene_double_click_handler

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        btn_folder = QAction("Open Folder", self)
        btn_folder.triggered.connect(self.open_folder_recursive)
        toolbar.addAction(btn_folder)
        
        toolbar.addSeparator()

        # Page Navigation Buttons
        btn_prev_page = QAction("< Page", self)
        btn_prev_page.triggered.connect(self.prev_page)
        toolbar.addAction(btn_prev_page)
        
        self.lbl_status = QLabel(" No File ")
        toolbar.addWidget(self.lbl_status)

        btn_next_page = QAction("Page >", self)
        btn_next_page.triggered.connect(self.next_page)
        toolbar.addAction(btn_next_page)
        
        toolbar.addSeparator()

        btn_export = QAction("Export PDF", self)
        btn_export.triggered.connect(self.export_current_pdf)
        toolbar.addAction(btn_export)
        
        self.status_bar = self.statusBar()

    def create_sidebar(self):
        dock = QDockWidget("PDF Files", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.file_list_widget = QListWidget()
        self.file_list_widget.itemClicked.connect(self.sidebar_file_clicked)
        dock.setWidget(self.file_list_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    # --- File Logic ---
    def open_folder_recursive(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder: return
        self.file_list = []
        self.file_list_widget.clear()
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(".pdf") and not file.endswith("_marked.pdf"):
                    full_path = os.path.join(root, file)
                    self.file_list.append(full_path)
                    self.file_list_widget.addItem(os.path.relpath(full_path, folder))
        if self.file_list: self.load_file_by_index(0)

    def load_file_by_index(self, index):
        if not (0 <= index < len(self.file_list)): return
        if self.pdf_path: self.save_sidecar() 

        self.current_file_index = index
        self.pdf_path = self.file_list[index]
        self.doc = fitz.open(self.pdf_path)
        self.current_page_idx = 0
        self.all_marks = {}
        
        self.file_list_widget.setCurrentRow(index)
        self.load_sidecar_data()
        self.render_current_page()
        self.setWindowTitle(f"MarkLatex - {os.path.basename(self.pdf_path)}")

    def sidebar_file_clicked(self, item):
        self.load_file_by_index(self.file_list_widget.row(item))

    # --- Persistence ---
    def get_sidecar_path(self):
        if not self.pdf_path: return None
        return os.path.splitext(self.pdf_path)[0] + ".mlat"

    def save_sidecar(self):
        if not self.pdf_path: return
        # Marks are already updated in self.all_marks by reference/callbacks
        path = self.get_sidecar_path()
        try:
            with open(path, 'w') as f:
                json.dump({"pdf_path": self.pdf_path, "all_marks": self.all_marks}, f, indent=2)
            self.status_bar.showMessage(f"Saved", 1000)
        except: pass

    def load_sidecar_data(self):
        path = self.get_sidecar_path()
        if path and os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.all_marks = {int(k): v for k, v in data.get("all_marks", {}).items()}
            except: self.all_marks = {}

    def ensure_page_list(self):
        if self.current_page_idx not in self.all_marks:
            self.all_marks[self.current_page_idx] = []

    # --- Rendering ---
    def render_latex(self, mark_data):
        """Renders text using Matplotlib with custom font/size/wrap."""
        text = mark_data['text']
        font_name = mark_data.get('font', DEFAULT_FONT)
        font_size = mark_data.get('size', DEFAULT_SIZE)
        wrap_width = mark_data.get('width', DEFAULT_WRAP)
        
        # 1. Apply Wrapping
        # We wrap lines manually to enforce the width limit while keeping $...$ blocks intact.
        def wrap_text(raw_text, width):
            punctuation = ".,;:!?，。；：！？"

            def wrap_line(line):
                tokens = []
                i = 0
                current = ""
                while i < len(line):
                    ch = line[i]
                    if ch.isspace():
                        if current:
                            tokens.append(current)
                            current = ""
                        # Collapse multiple spaces into a single delimiter token
                        while i < len(line) and line[i].isspace():
                            i += 1
                        tokens.append(" ")
                        continue
                    if ch == "$":
                        if current:
                            tokens.append(current)
                            current = ""
                        end = line.find("$", i + 1)
                        if end != -1:
                            token = line[i:end + 1]
                            i = end + 1
                            while i < len(line) and line[i] in punctuation:
                                token += line[i]
                                i += 1
                            tokens.append(token)
                            continue
                    current += ch
                    i += 1
                if current:
                    tokens.append(current)

                lines = []
                current_line = ""
                current_len = 0

                for token in tokens:
                    if token == " ":
                        if current_line and not current_line.endswith(" "):
                            if current_len + 1 > width:
                                lines.append(current_line.rstrip())
                                current_line = ""
                                current_len = 0
                            else:
                                current_line += " "
                                current_len += 1
                        continue

                    token_len = len(token)
                    if not current_line:
                        current_line = token
                        current_len = token_len
                        continue

                    spacer = "" if current_line.endswith(" ") else " "
                    extra_len = (1 if spacer else 0) + token_len
                    if current_len + extra_len > width:
                        lines.append(current_line.rstrip())
                        current_line = token
                        current_len = token_len
                    else:
                        current_line += spacer + token
                        current_len += extra_len

                if current_line:
                    lines.append(current_line.rstrip())
                return lines

            wrapped_lines = []
            for raw_line in raw_text.splitlines():
                wrapped_lines.extend(wrap_line(raw_line))
            return "\n".join(wrapped_lines)

        wrapped_text = wrap_text(text, wrap_width)

        buf = io.BytesIO()
        # Use a small initial figure size - bbox_inches='tight' will adjust it to fit the text
        fig = plt.figure(figsize=(1, 1))
        fig.patch.set_alpha(0.0)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis('off')
        
        try:
            # Use axes coordinates so the text anchors to the top-left corner
            text_obj = ax.text(0, 1, wrapped_text,
                               fontsize=font_size,
                               fontname=font_name,
                               color='red',
                               va='top', ha='left',
                               transform=ax.transAxes)
        except:
            text_obj = ax.text(0, 1, "FONT ERROR\n" + wrapped_text, fontsize=8, color='red',
                               va='top', ha='left', transform=ax.transAxes)

        # Compute exact bounding box to avoid extra top/bottom margins
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbox = text_obj.get_window_extent(renderer=renderer)
        bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

        # High DPI for sharpness - use RENDER_DPI constant
        plt.savefig(buf, format='png', bbox_inches=bbox_inches, pad_inches=0.0, dpi=RENDER_DPI, transparent=True)
        plt.close(fig)
        buf.seek(0)
        return QPixmap.fromImage(QImage.fromData(buf.read()))

    def render_current_page(self):
        if not self.doc: return
        self.scene.clear()
        
        # Background - SVG-based rendering
        page = self.doc[self.current_page_idx]
        
        # Get SVG content from PDF page
        svg_content = page.get_svg_image()
        
        # Convert SVG string to QByteArray
        svg_data = QByteArray(svg_content.encode('utf-8'))
        
        # Create SVG renderer and item
        svg_renderer = QSvgRenderer(svg_data)
        svg_item = QGraphicsSvgItem()
        svg_item.setSharedRenderer(svg_renderer)
        
        # Set position and size based on PDF page dimensions (1:1 mapping)
        page_rect = page.rect
        svg_item.setPos(0, 0)
        svg_item.setScale(1.0)  # Natural scale - 1:1 with PDF coordinates
        
        # Configure SVG item properties
        svg_item.setZValue(-1)
        svg_item.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        # Add to scene
        self.scene.addItem(svg_item)
        
        # Set scene rectangle to match PDF page size (natural coordinates)
        self.scene.setSceneRect(page_rect.x0, page_rect.y0, page_rect.width, page_rect.height)
        
        self.lbl_status.setText(f" Page {self.current_page_idx + 1} / {len(self.doc)} ")

        # Marks
        if self.current_page_idx in self.all_marks:
            for m in self.all_marks[self.current_page_idx]:
                # Ensure defaults for old files
                if 'font' not in m: m['font'] = DEFAULT_FONT
                if 'size' not in m: m['size'] = DEFAULT_SIZE
                if 'width' not in m: m['width'] = DEFAULT_WRAP
                
                item = LatexItem(m, self.render_latex, self.save_sidecar)
                self.scene.addItem(item)

    # --- Interaction ---
    def scene_double_click_handler(self, event):
        item = self.scene.itemAt(event.scenePos(), self.view.transform())
        
        if (item is None or item.zValue() == -1) and self.doc:
            # Create NEW Mark
            pos = event.scenePos()
            
            # Show Dialog with Defaults
            dialog = MarkPropertiesDialog(self, "Add Mark")
            if dialog.exec():
                data = dialog.get_data()
                if data['text']:
                    # Prepare Mark Data structure
                    new_mark = {
                        "text": data['text'],
                        "x": pos.x(),
                        "y": pos.y(),
                        "font": data['font'],
                        "size": data['size'],
                        "width": data['width']
                    }
                    
                    self.ensure_page_list()
                    # Add to data list first
                    self.all_marks[self.current_page_idx].append(new_mark)
                    
                    # Add to scene (pass reference to the dict object)
                    item = LatexItem(new_mark, self.render_latex, self.save_sidecar)
                    self.scene.addItem(item)
                    self.save_sidecar()
        else:
            QGraphicsScene.mouseDoubleClickEvent(self.scene, event)

    def prev_page(self):
        """Navigate to the previous page."""
        if self.doc and self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.render_current_page()

    def next_page(self):
        """Navigate to the next page."""
        if self.doc and self.current_page_idx < len(self.doc) - 1:
            self.current_page_idx += 1
            self.render_current_page()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for item in self.scene.selectedItems():
                if isinstance(item, LatexItem):
                    # Remove from data list
                    if item.mark_data in self.all_marks[self.current_page_idx]:
                        self.all_marks[self.current_page_idx].remove(item.mark_data)
                    self.scene.removeItem(item)
            self.save_sidecar()
        # Page Navigation Keys - Use Page Up/Page Down for page switching
        elif event.key() == Qt.Key.Key_PageUp:
            if self.doc and self.current_page_idx > 0:
                self.current_page_idx -= 1
                self.render_current_page()
        elif event.key() == Qt.Key.Key_PageDown:
            if self.doc and self.current_page_idx < len(self.doc) - 1:
                self.current_page_idx += 1
                self.render_current_page()

    def export_current_pdf(self):
        if not self.doc: return
        base = os.path.splitext(self.pdf_path)[0]
        out_path = f"{base}_marked.pdf"
        
        export_doc = fitz.open(self.pdf_path)
        
        for p_idx, marks in self.all_marks.items():
            if p_idx >= len(export_doc): continue
            page = export_doc[p_idx]
            page_rect = page.rect 
            min_x, min_y, max_x, max_y = page_rect.x0, page_rect.y0, page_rect.x1, page_rect.y1
            
            for m in marks:
                pix = self.render_latex(m)
                ba = QBuffer()
                ba.open(QIODevice.OpenModeFlag.ReadWrite)
                pix.toImage().save(ba, "PNG")
                
                # Coords - Direct mapping since we use 1:1 PDF coordinates
                x = m['x']
                y = m['y']
                w = pix.width() / RENDER_DPI * 72  # Convert from DPI to PDF points (72 DPI)
                h = pix.height() / RENDER_DPI * 72
                
                # Check bounds
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x + w > max_x: max_x = x + w
                if y + h > max_y: max_y = y + h
                
                page.insert_image(fitz.Rect(x, y, x+w, y+h), stream=ba.data().data())
            
            if max_x > page_rect.x1 or max_y > page_rect.y1 or min_x < page_rect.x0 or min_y < page_rect.y0:
                 page.set_mediabox(fitz.Rect(min_x, min_y, max_x, max_y))

        export_doc.save(out_path)
        QMessageBox.information(self, "Exported", f"Saved: {out_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MarkLatexApp()
    window.show()
    sys.exit(app.exec())