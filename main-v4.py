import sys
import json
import io
import os
import fitz  # PyMuPDF
import matplotlib
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QFileDialog, QToolBar, 
                             QMessageBox, QGraphicsItem, QLabel, QDockWidget, QListWidget,
                             QWidget, QVBoxLayout, QDialog, QTextEdit, QPushButton, QDialogButtonBox)
from PyQt6.QtGui import QPixmap, QImage, QAction, QColor, QFont
from PyQt6.QtCore import Qt, QBuffer, QIODevice

# Use Agg backend
matplotlib.use('Agg')

# --- Custom Multi-Line Input Dialog ---
class MultiLineDialog(QDialog):
    def __init__(self, parent=None, title="Mark", initial_text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        self.text_edit.setFont(QFont("Consolas", 11)) # Monospace for coding feel
        layout.addWidget(self.text_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_text(self):
        return self.text_edit.toPlainText()

class LatexItem(QGraphicsPixmapItem):
    """Movable, editable LaTeX annotation."""
    def __init__(self, latex_text, render_func, x, y, on_change_callback):
        super().__init__()
        self.latex_text = latex_text
        self.render_func = render_func
        self.on_change_callback = on_change_callback
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.update_image()

    def update_image(self):
        pixmap = self.render_func(self.latex_text)
        self.setPixmap(pixmap)

    def mouseDoubleClickEvent(self, event):
        # Open custom multi-line dialog
        dialog = MultiLineDialog(None, "Edit Mark", self.latex_text)
        if dialog.exec():
            new_text = dialog.get_text()
            if new_text:
                self.latex_text = new_text
                self.update_image()
                self.on_change_callback()
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.on_change_callback()

class MarkLatexApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarkLatex V4 - High Res & Multi-Line")
        self.resize(1400, 900)

        # -- State --
        self.file_list = []
        self.current_file_index = -1
        self.doc = None
        self.pdf_path = None
        self.current_page_idx = 0
        self.all_marks = {}
        
        # FIX 1: Higher Resolution Scale
        self.view_scale = 2.0 

        # -- UI --
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        # self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Disabled for clicking
        self.setCentralWidget(self.view)
        
        self.create_toolbar()
        self.create_sidebar()
        
        # FIX 3: Double Click Handler
        # We hook into mouseDoubleClickEvent on the scene
        self.scene.mouseDoubleClickEvent = self.scene_double_click_handler

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        btn_folder = QAction("Open Folder Recursive", self)
        btn_folder.triggered.connect(self.open_folder_recursive)
        toolbar.addAction(btn_folder)
        
        toolbar.addSeparator()

        btn_prev_pdf = QAction("Prev PDF", self)
        btn_prev_pdf.triggered.connect(self.prev_file)
        toolbar.addAction(btn_prev_pdf)

        btn_next_pdf = QAction("Next PDF", self)
        btn_next_pdf.triggered.connect(self.next_file)
        toolbar.addAction(btn_next_pdf)

        toolbar.addSeparator()
        
        btn_prev_page = QAction("< Page", self)
        btn_prev_page.triggered.connect(self.prev_page)
        toolbar.addAction(btn_prev_page)
        
        self.lbl_status = QLabel(" No File ")
        toolbar.addWidget(self.lbl_status)

        btn_next_page = QAction("Page >", self)
        btn_next_page.triggered.connect(self.next_page)
        toolbar.addAction(btn_next_page)

        toolbar.addSeparator()
        
        btn_export = QAction("Export Current PDF", self)
        btn_export.triggered.connect(self.export_current_pdf)
        toolbar.addAction(btn_export)

        self.status_bar = self.statusBar()

    def create_sidebar(self):
        dock = QDockWidget("Files in Folder", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.file_list_widget = QListWidget()
        self.file_list_widget.itemClicked.connect(self.sidebar_file_clicked)
        dock.setWidget(self.file_list_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    # --- File / Folder Logic ---
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
                    rel_path = os.path.relpath(full_path, folder)
                    self.file_list_widget.addItem(rel_path)
        if self.file_list:
            self.load_file_by_index(0)

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
        
        fname = os.path.basename(self.pdf_path)
        self.setWindowTitle(f"MarkLatex - {fname}")

    def sidebar_file_clicked(self, item):
        self.load_file_by_index(self.file_list_widget.row(item))

    def next_file(self): self.load_file_by_index(self.current_file_index + 1)
    def prev_file(self): self.load_file_by_index(self.current_file_index - 1)

    # --- Data & Rendering ---
    def get_sidecar_path(self):
        if not self.pdf_path: return None
        return os.path.splitext(self.pdf_path)[0] + ".mlat"

    def save_sidecar(self):
        if not self.pdf_path: return
        self.update_memory_from_scene()
        path = self.get_sidecar_path()
        try:
            with open(path, 'w') as f:
                json.dump({"pdf_path": self.pdf_path, "all_marks": self.all_marks}, f, indent=2)
            self.status_bar.showMessage(f"Auto-saved", 1000)
        except: pass

    def load_sidecar_data(self):
        path = self.get_sidecar_path()
        if path and os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.all_marks = {int(k): v for k, v in data.get("all_marks", {}).items()}
            except: self.all_marks = {}

    def update_memory_from_scene(self):
        if self.doc is None: return
        marks = []
        for item in self.scene.items():
            if isinstance(item, LatexItem):
                marks.append({"text": item.latex_text, "x": item.x(), "y": item.y()})
        self.all_marks[self.current_page_idx] = marks

    def render_latex(self, text):
        buf = io.BytesIO()
        # Matplotlib rendering
        fig = plt.figure(figsize=(0.1, 0.1))
        fig.patch.set_alpha(0.0)
        try:
            # Multi-line text support
            plt.text(0, 0, text, fontsize=12, color='red', va='bottom', ha='left')
        except:
            plt.text(0, 0, "LATEX ERROR", fontsize=12, color='red')
        plt.axis('off')
        
        # High DPI for sharpness
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05, dpi=200, transparent=True)
        plt.close(fig)
        buf.seek(0)
        return QPixmap.fromImage(QImage.fromData(buf.read()))

    def render_current_page(self):
        if not self.doc: return
        self.scene.clear()
        
        # FIX 1: High Res Background
        page = self.doc[self.current_page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(self.view_scale, self.view_scale))
        img = QImage.fromData(pix.tobytes("ppm"))
        bg = self.scene.addPixmap(QPixmap.fromImage(img))
        bg.setZValue(-1)
        bg.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.scene.setSceneRect(0, 0, pix.width, pix.height)
        
        self.lbl_status.setText(f" Page {self.current_page_idx + 1} / {len(self.doc)} ")

        if self.current_page_idx in self.all_marks:
            for m in self.all_marks[self.current_page_idx]:
                item = LatexItem(m["text"], self.render_latex, m["x"], m["y"], self.save_sidecar)
                self.scene.addItem(item)

    # --- Interaction ---
    def scene_double_click_handler(self, event):
        """FIX 3: Only create on Double Click"""
        item = self.scene.itemAt(event.scenePos(), self.view.transform())
        
        # Allow creation if clicking background or empty space
        if (item is None or item.zValue() == -1) and self.doc:
            pos = event.scenePos()
            
            # FIX 4: Use MultiLineDialog
            dialog = MultiLineDialog(self, "Add Mark", "")
            if dialog.exec():
                text = dialog.get_text()
                if text:
                    item = LatexItem(text, self.render_latex, pos.x(), pos.y(), self.save_sidecar)
                    self.scene.addItem(item)
                    self.save_sidecar()
        else:
            # Pass through to Item's double click (edit)
            QGraphicsScene.mouseDoubleClickEvent(self.scene, event)

    def next_page(self):
        if self.doc and self.current_page_idx < len(self.doc) - 1:
            self.update_memory_from_scene()
            self.current_page_idx += 1
            self.render_current_page()

    def prev_page(self):
        if self.doc and self.current_page_idx > 0:
            self.update_memory_from_scene()
            self.current_page_idx -= 1
            self.render_current_page()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for item in self.scene.selectedItems():
                self.scene.removeItem(item)
            self.save_sidecar()

    # --- Export with Boundary Expansion ---
    def export_current_pdf(self):
        if not self.doc: return
        base = os.path.splitext(self.pdf_path)[0]
        out_path = f"{base}_marked.pdf"
        self.update_memory_from_scene()
        
        export_doc = fitz.open(self.pdf_path)
        
        for p_idx, marks in self.all_marks.items():
            if p_idx >= len(export_doc): continue
            page = export_doc[p_idx]
            
            # Get current page dimensions
            # PyMuPDF coords are 1/72 inch.
            page_rect = page.rect 
            
            # We track the "max extent" of our annotations to see if we need to grow the page
            min_x, min_y = page_rect.x0, page_rect.y0
            max_x, max_y = page_rect.x1, page_rect.y1
            
            # Insert Images & Calculate Bounds
            for m in marks:
                pix = self.render_latex(m["text"])
                ba = QBuffer()
                ba.open(QIODevice.OpenModeFlag.ReadWrite)
                pix.toImage().save(ba, "PNG")
                png_bytes = ba.data().data()
                
                # Convert Screen Coords -> PDF Coords
                x = m["x"] / self.view_scale
                y = m["y"] / self.view_scale
                w = pix.width() / self.view_scale
                h = pix.height() / self.view_scale
                
                # Check bounds (FIX 2)
                # If annotation sticks out right/bottom, expand max_x/max_y
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x + w > max_x: max_x = x + w
                if y + h > max_y: max_y = y + h
                
                page.insert_image(fitz.Rect(x, y, x+w, y+h), stream=png_bytes)
            
            # Apply boundary expansion if needed
            if max_x > page_rect.x1 or max_y > page_rect.y1 or min_x < page_rect.x0 or min_y < page_rect.y0:
                 # Expand the MediaBox to include the new area
                 page.set_mediabox(fitz.Rect(min_x, min_y, max_x, max_y))

        export_doc.save(out_path)
        QMessageBox.information(self, "Exported", f"Saved: {out_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MarkLatexApp()
    window.show()
    sys.exit(app.exec())