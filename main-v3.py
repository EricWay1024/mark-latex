import sys
import json
import io
import os
import fitz  # PyMuPDF
import matplotlib
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QFileDialog, QInputDialog, QToolBar, 
                             QMessageBox, QGraphicsItem, QLabel, QDockWidget, QListWidget,
                             QWidget, QVBoxLayout)
from PyQt6.QtGui import QPixmap, QImage, QAction, QColor
from PyQt6.QtCore import Qt, QBuffer, QIODevice

matplotlib.use('Agg')

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
        new_text, ok = QInputDialog.getText(None, "Edit Mark", "LaTeX:", text=self.latex_text)
        if ok and new_text:
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
        self.setWindowTitle("MarkLatex V3 - Batch Marking")
        self.resize(1400, 900)

        # -- State --
        self.file_list = []      # List of full paths to PDFs
        self.current_file_index = -1
        
        self.doc = None          # Current PyMuPDF Document
        self.pdf_path = None     # Current PDF Path
        self.current_page_idx = 0
        self.all_marks = {}      # Marks for CURRENT file { page: [marks] }

        # -- UI Components --
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        # self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setCentralWidget(self.view)
        
        self.create_toolbar()
        self.create_sidebar()
        
        # Click handler
        self.scene.mousePressEvent = self.scene_click_handler

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Folder Loading
        btn_folder = QAction("Open Folder Recursive", self)
        btn_folder.triggered.connect(self.open_folder_recursive)
        toolbar.addAction(btn_folder)
        
        toolbar.addSeparator()

        # PDF Navigation
        btn_prev_pdf = QAction("Prev PDF", self)
        btn_prev_pdf.triggered.connect(self.prev_file)
        toolbar.addAction(btn_prev_pdf)

        btn_next_pdf = QAction("Next PDF", self)
        btn_next_pdf.triggered.connect(self.next_file)
        toolbar.addAction(btn_next_pdf)

        toolbar.addSeparator()
        
        # Page Navigation
        btn_prev_page = QAction("< Page", self)
        btn_prev_page.triggered.connect(self.prev_page)
        toolbar.addAction(btn_prev_page)
        
        self.lbl_status = QLabel(" No File ")
        toolbar.addWidget(self.lbl_status)

        btn_next_page = QAction("Page >", self)
        btn_next_page.triggered.connect(self.next_page)
        toolbar.addAction(btn_next_page)

        toolbar.addSeparator()
        
        # Export
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

    # --- File Discovery ---
    def open_folder_recursive(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder: return
        
        self.file_list = []
        self.file_list_widget.clear()
        
        # Walk through directory
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(".pdf"):
                    full_path = os.path.join(root, file)
                    self.file_list.append(full_path)
                    
                    # Display relative path in sidebar for readability
                    rel_path = os.path.relpath(full_path, folder)
                    self.file_list_widget.addItem(rel_path)
        
        if self.file_list:
            self.load_file_by_index(0)
            self.status_bar.showMessage(f"Found {len(self.file_list)} PDFs.")
        else:
            QMessageBox.warning(self, "No PDFs", "No PDF files found in that folder.")

    # --- File Switching Logic ---
    def load_file_by_index(self, index):
        if not (0 <= index < len(self.file_list)): return
        
        # 1. Save work on OLD file if open
        if self.pdf_path:
            self.save_sidecar() 

        # 2. Reset State for NEW file
        self.current_file_index = index
        self.pdf_path = self.file_list[index]
        self.doc = fitz.open(self.pdf_path)
        self.current_page_idx = 0
        self.all_marks = {}
        
        # Highlight in sidebar
        self.file_list_widget.setCurrentRow(index)
        
        # 3. Load Sidecar Data (if exists)
        self.load_sidecar_data()
        
        # 4. Render
        self.render_current_page()
        
        # Update UI
        fname = os.path.basename(self.pdf_path)
        self.setWindowTitle(f"MarkLatex - {fname}")

    def sidebar_file_clicked(self, item):
        idx = self.file_list_widget.row(item)
        self.load_file_by_index(idx)

    def next_file(self):
        self.load_file_by_index(self.current_file_index + 1)

    def prev_file(self):
        self.load_file_by_index(self.current_file_index - 1)

    # --- Data Persistence (Sidecar) ---
    def get_sidecar_path(self):
        if not self.pdf_path: return None
        return os.path.splitext(self.pdf_path)[0] + ".mlat"

    def save_sidecar(self):
        """Save memory state to disk."""
        if not self.pdf_path: return
        
        # Sync current screen to memory first
        self.update_memory_from_scene()
        
        path = self.get_sidecar_path()
        data = { "pdf_path": self.pdf_path, "all_marks": self.all_marks }
        
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            self.status_bar.showMessage(f"Auto-saved: {os.path.basename(path)}", 1000)
        except Exception as e:
            print(f"Save error: {e}")

    def load_sidecar_data(self):
        path = self.get_sidecar_path()
        if path and os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    # Convert JSON string keys back to int
                    self.all_marks = {int(k): v for k, v in data.get("all_marks", {}).items()}
            except:
                self.all_marks = {}

    def update_memory_from_scene(self):
        """Capture marks from current scene into self.all_marks"""
        if self.doc is None: return
        marks = []
        for item in self.scene.items():
            if isinstance(item, LatexItem):
                marks.append({
                    "text": item.latex_text,
                    "x": item.x(), 
                    "y": item.y()
                })
        self.all_marks[self.current_page_idx] = marks

    # --- Rendering ---
    def render_latex(self, text):
        buf = io.BytesIO()
        fig = plt.figure(figsize=(0.1, 0.1))
        fig.patch.set_alpha(0.0)
        try:
            plt.text(0, 0, text, fontsize=12, color='red')
        except:
            plt.text(0, 0, "LATEX ERROR", fontsize=12, color='red')
        plt.axis('off')
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05, dpi=150, transparent=True)
        plt.close(fig)
        buf.seek(0)
        return QPixmap.fromImage(QImage.fromData(buf.read()))

    def render_current_page(self):
        if not self.doc: return
        
        # Save previous page marks before clearing? 
        # (Ideally handled by update_memory_from_scene called before page switch)
        
        self.scene.clear()
        
        # 1. Background
        page = self.doc[self.current_page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img = QImage.fromData(pix.tobytes("ppm"))
        bg = self.scene.addPixmap(QPixmap.fromImage(img))
        bg.setZValue(-1)
        bg.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.scene.setSceneRect(0, 0, pix.width, pix.height)
        
        self.lbl_status.setText(f" Page {self.current_page_idx + 1} / {len(self.doc)} ")

        # 2. Marks
        if self.current_page_idx in self.all_marks:
            for m in self.all_marks[self.current_page_idx]:
                # Pass save_sidecar as callback so every move saves instantly
                item = LatexItem(m["text"], self.render_latex, m["x"], m["y"], self.save_sidecar)
                self.scene.addItem(item)

    # --- Navigation & Events ---
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
    
    def scene_click_handler(self, event):
        # 1. Check what is under the mouse
        item = self.scene.itemAt(event.scenePos(), self.view.transform())
        
        # 2. ALLOW creation if:
        #    a) There is no item (item is None) OR
        #    b) The item is the background image (we check if ZValue is -1)
        if (item is None or item.zValue() == -1) and self.doc:
            pos = event.scenePos()
            text, ok = QInputDialog.getText(self, "Mark", "LaTeX:")
            if ok and text:
                # Add the item
                item = LatexItem(text, self.render_latex, pos.x(), pos.y(), self.save_sidecar)
                self.scene.addItem(item)
                self.save_sidecar()
        else:
            # If we clicked an EXISTING annotation, let the scene handle the selection/move
            QGraphicsScene.mousePressEvent(self.scene, event)
            
    # def scene_click_handler(self, event):
    #     item = self.scene.itemAt(event.scenePos(), self.view.transform())
    #     if item is None and self.doc:
    #         pos = event.scenePos()
    #         text, ok = QInputDialog.getText(self, "Mark", "LaTeX:")
    #         if ok and text:
    #             item = LatexItem(text, self.render_latex, pos.x(), pos.y(), self.save_sidecar)
    #             self.scene.addItem(item)
    #             self.save_sidecar()
    #     else:
    #         QGraphicsScene.mousePressEvent(self.scene, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for item in self.scene.selectedItems():
                self.scene.removeItem(item)
            self.save_sidecar()

    def export_current_pdf(self):
        if not self.doc: return
        
        # Auto-generate export name: "filename_marked.pdf"
        base = os.path.splitext(self.pdf_path)[0]
        out_path = f"{base}_marked.pdf"
        
        # Ensure latest marks are captured from the screen
        self.update_memory_from_scene() 
        
        # Open a fresh copy of the PDF for exporting
        export_doc = fitz.open(self.pdf_path)
        screen_scale = 1.5
        
        for p_idx, marks in self.all_marks.items():
            if p_idx >= len(export_doc): continue
            page = export_doc[p_idx]
            
            for m in marks:
                # 1. Render the LaTeX to a QPixmap
                pix = self.render_latex(m["text"])
                
                # --- THE FIX STARTS HERE ---
                # Use QBuffer (Qt's version of BytesIO)
                ba = QBuffer()
                ba.open(QIODevice.OpenModeFlag.ReadWrite)
                pix.toImage().save(ba, "PNG")
                
                # Extract the raw bytes from the QBuffer
                png_bytes = ba.data().data()
                # --- THE FIX ENDS HERE ---
                
                # Calculate coordinates (Screen scale -> PDF scale)
                x = m["x"] / screen_scale
                y = m["y"] / screen_scale
                w = pix.width() / screen_scale
                h = pix.height() / screen_scale
                
                # Insert the image using PyMuPDF
                page.insert_image(fitz.Rect(x, y, x+w, y+h), stream=png_bytes)
        
        export_doc.save(out_path)
        QMessageBox.information(self, "Exported", f"Saved: {out_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MarkLatexApp()
    window.show()
    sys.exit(app.exec())