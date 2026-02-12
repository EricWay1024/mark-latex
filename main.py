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
                             QSlider, QTreeWidget, QTreeWidgetItem)
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
    def __init__(self, mark_data, render_func, on_change_callback, undo_callback=None):
        super().__init__()
        self.mark_data = mark_data 
        self.render_func = render_func
        self.on_change_callback = on_change_callback
        self.undo_callback = undo_callback
        self._drag_start = None
        
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
        before_state = dict(self.mark_data)
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
                if self.undo_callback:
                    self.undo_callback("edit", {
                        "before": before_state,
                        "mark": self.mark_data
                    })
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = (self.x(), self.y())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        old_pos = self._drag_start
        new_pos = (self.x(), self.y())
        self.mark_data['x'] = self.x()
        self.mark_data['y'] = self.y()
        super().mouseReleaseEvent(event)
        self.on_change_callback()
        if old_pos and new_pos != old_pos and self.undo_callback:
            self.undo_callback("move", {
                "before": old_pos,
                "after": new_pos,
                "mark": self.mark_data
            })
        self._drag_start = None

class MarkLatexApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarkLatex V5 - Styled Text")
        self.resize(1400, 900)

        # -- State --
        self.file_list = []
        self.file_student_folders = []
        self.current_file_index = -1
        self.doc = None
        self.pdf_path = None
        self.root_folder = None
        self.current_student_folder = None
        self.is_moodle_mode = False
        self.current_page_idx = 0
        self.all_marks = {}
        self.undo_stack = []
        self.undo_limit = 20
        # Removed view_scale - now using natural PDF coordinates (1:1 mapping)

        # -- UI --
        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene)
        self.setCentralWidget(self.view)
        
        self.create_toolbar()
        self.create_sidebar()
        
        self.scene.mouseDoubleClickEvent = self.scene_double_click_handler

    def update_moodle_indicator(self):
        if self.is_moodle_mode:
            self.lbl_moodle_mode.setText(" Moodle mode ")
            self.lbl_moodle_mode.setStyleSheet("color: #1f7a1f; font-weight: bold;")
            self.lbl_moodle_mode.setVisible(True)
        else:
            self.lbl_moodle_mode.setVisible(False)

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

        self.lbl_moodle_mode = QLabel(" Moodle mode ")
        self.lbl_moodle_mode.setVisible(False)
        toolbar.addWidget(self.lbl_moodle_mode)
        
        toolbar.addSeparator()

        btn_export = QAction("Export PDF", self)
        btn_export.triggered.connect(self.export_current_pdf)
        toolbar.addAction(btn_export)

        btn_export_all = QAction("Export All", self)
        btn_export_all.triggered.connect(self.export_all_pdfs)
        toolbar.addAction(btn_export_all)

        btn_undo = QAction("Undo", self)
        btn_undo.triggered.connect(self.undo_last_action)
        toolbar.addAction(btn_undo)
        
        self.status_bar = self.statusBar()

    def create_sidebar(self):
        dock = QDockWidget("PDF Files", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.file_list_widget = QTreeWidget()
        self.file_list_widget.setHeaderHidden(True)
        self.file_list_widget.itemClicked.connect(self.sidebar_file_clicked)
        dock.setWidget(self.file_list_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    # --- File Logic ---
    def open_folder_recursive(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder: return
        self.file_list = []
        self.file_student_folders = []
        self.file_list_widget.clear()
        self.root_folder = folder
        self.is_moodle_mode = False

        root_pdfs = [
            f for f in os.listdir(folder)
            if f.lower().endswith(".pdf") and not f.endswith("_marked.pdf")
            and os.path.isfile(os.path.join(folder, f))
        ]
        subfolders = [
            d for d in os.listdir(folder)
            if os.path.isdir(os.path.join(folder, d))
        ]

        moodle_entries = []
        for subfolder in subfolders:
            sub_path = os.path.join(folder, subfolder)
            for root, dirs, files in os.walk(sub_path):
                for file in files:
                    if file.lower().endswith(".pdf") and not file.endswith("_marked.pdf"):
                        full_path = os.path.join(root, file)
                        moodle_entries.append((subfolder, full_path))

        if moodle_entries and not root_pdfs:
            self.is_moodle_mode = True
            for subfolder, full_path in moodle_entries:
                clean_name = subfolder.split("_", 1)[0]
                display_name = f"{clean_name} / {os.path.basename(full_path)}"
                self.file_list.append(full_path)
                self.file_student_folders.append(subfolder)
                self.file_list_widget.addTopLevelItem(QTreeWidgetItem([display_name]))
        else:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(".pdf") and not file.endswith("_marked.pdf"):
                        full_path = os.path.join(root, file)
                        self.file_list.append(full_path)
                        self.file_list_widget.addTopLevelItem(
                            QTreeWidgetItem([os.path.relpath(full_path, folder)])
                        )
        self.refresh_remark_tree()
        self.update_moodle_indicator()
        if self.file_list: self.load_file_by_index(0)

    def load_file_by_index(self, index):
        if not (0 <= index < len(self.file_list)): return
        if self.pdf_path: self.save_sidecar() 

        self.current_file_index = index
        self.pdf_path = self.file_list[index]
        self.current_student_folder = (
            self.file_student_folders[index] if self.is_moodle_mode else None
        )
        self.doc = self.get_normalized_doc(self.pdf_path)
        self.current_page_idx = 0
        self.all_marks = {}
        self.undo_stack = []
        
        self.file_list_widget.setCurrentItem(self.file_list_widget.topLevelItem(index))
        self.load_sidecar_data()
        self.render_current_page()
        self.setWindowTitle(f"MarkLatex - {os.path.basename(self.pdf_path)}")



    def get_normalized_doc(self, pdf_path: str) -> fitz.Document | None:
        """
        Pre-flight Normalization:
        Returns a fitz.Document where all pages are physically 0-rotation
        and match the visual dimensions of the original file.

        Vector-preserving approach (no pixmap rasterization):
        - For rotated pages: temporarily set source rotation to 0, then place with rotate=old_rotation
        - For unrotated pages: direct show_pdf_page copy
        """
        try:
            raw_doc = fitz.open(pdf_path)
        except Exception:
            return None

        # If no page needs rotation, return original doc to save memory.
        if not any(page.rotation % 360 != 0 for page in raw_doc):
            return raw_doc

        clean_doc = fitz.open()

        for page in raw_doc:
            r = page.rotation % 360

            # page.rect reflects the *visual* rectangle (rotation applied),
            # which is what you want for your "visual dimensions" invariant.
            vis_rect = page.rect

            new_page = clean_doc.new_page(width=vis_rect.width, height=vis_rect.height)

            if r == 0:
                # no rotation, just copy (vector)
                new_page.show_pdf_page(
                    new_page.rect,
                    raw_doc,
                    page.number,
                )
                continue

            # Rotated page: bake rotation into placed content (vector), output page stays rotation=0.
            # Important: show_pdf_page rotates relative to an unrotated source page.
            # So we temporarily set source page rotation to 0.
            page.set_rotation(0)

            new_page.show_pdf_page(
                new_page.rect,
                raw_doc,
                page.number,
                rotate=-r, # quite crucial here in a subtle way that no one can explains...
            )

            # Restore original rotation on the in-memory source doc object.
            page.set_rotation(r)

        raw_doc.close()
        return clean_doc

    # the following method uses a pixelizing approch which bloat the file size significantly
    # hence we don't use it but it's the first approach that works...
    # def get_normalized_doc(self, pdf_path):
    #     """
    #     Pre-flight Normalization:
    #     Returns a fitz.Document where all pages are physically 0-rotation 
    #     and match the visual dimensions of the original file.
    #     """
    #     try:
    #         # 打开原始文件
    #         raw_doc = fitz.open(pdf_path)
    #     except Exception:
    #         return None

    #     # 检查是否有任何页面需要旋转。如果没有，直接返回原文档，节省内存。
    #     # 注意：这里我们检查 rotation % 360 != 0 以防有 360 度这种奇怪的情况
    #     if not any(page.rotation % 360 != 0 for page in raw_doc):
    #         return raw_doc

    #     # 创建一个新的、干净的内存 PDF
    #     clean_doc = fitz.open()

    #     for page in raw_doc:

    #         if page.rotation != 0:
    #             dpi = 100
    #             zoom = dpi / 72  # 72 is default PDF DPI
    #             mat = fitz.Matrix(zoom, zoom)
                
    #             # get_pixmap 自动处理了旋转！你不需要手动 rotate。
    #             # 它返回的是“用户在屏幕上看到的样子”。
    #             pix = page.get_pixmap(matrix=mat, alpha=False)

    #             # 2. 创建新页面
    #             # 使用图片的宽高 (pixels) 转换回 PDF 单位 (points)
    #             # width = pix.width * 72 / dpi
    #             # height = pix.height * 72 / dpi
    #             # 或者直接用 page.rect (视觉尺寸)，通常是一致的
                
    #             # 关键：新页面的尺寸必须匹配图片的视觉尺寸
    #             img_pdf_width = page.rect.width
    #             img_pdf_height = page.rect.height
                
    #             new_page = clean_doc.new_page(width=img_pdf_width, height=img_pdf_height)

    #             # 3. 插入图片
    #             # 此时图片已经是“正”的了（get_pixmap 处理了），页面也是“正”的。
    #             # 直接填满即可。
    #             new_page.insert_image(
    #                 new_page.rect, 
    #                 stream=pix.tobytes()
    #             )
            
    #         else:
    #             new_page = clean_doc.new_page(width=page.rect.width, height=page.rect.height)
    #             # no rotation, just copy 
    #             new_page.show_pdf_page(
    #                 new_page.rect,                # 填满新页面
    #                 raw_doc,                      # 源文档
    #                 page.number,                  # 页码
    #                 # rotate=0,
    #                 # # clip=page.cropbox,            # 关键：只渲染裁剪框内的内容
    #                 # keep_proportion=True          # 关键：禁止拉伸
    #             )

    #     # 关闭原文档，释放文件句柄
    #     raw_doc.close()
        
    #     # 返回新的、已经“转正”的文档
    #     return clean_doc

    def sidebar_file_clicked(self, item):
        if item.parent() is None:
            index = self.file_list_widget.indexOfTopLevelItem(item)
            self.load_file_by_index(index)
            return
        pdf_index = item.data(0, Qt.ItemDataRole.UserRole)
        page_index = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if pdf_index is None or page_index is None:
            return
        self.load_file_by_index(pdf_index)
        if self.doc and 0 <= page_index < len(self.doc):
            self.current_page_idx = page_index
            self.render_current_page()

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
        def render_text(text_to_render):
            buf = io.BytesIO()
            # Use a small initial figure size - bbox_inches='tight' will adjust it to fit the text
            fig = plt.figure(figsize=(1, 1))
            fig.patch.set_alpha(0.0)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis('off')

            try:
                # Use axes coordinates so the text anchors to the top-left corner
                text_obj = ax.text(0, 1, text_to_render,
                                   fontsize=font_size,
                                   fontname=font_name,
                                   color='red',
                                   va='top', ha='left',
                                   transform=ax.transAxes)
            except Exception:
                text_obj = ax.text(0, 1, "FONT ERROR\n" + text_to_render, fontsize=8, color='red',
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

        try:
            return render_text(wrapped_text)
        except Exception as exc:
            safe_text = wrapped_text.replace("$", "\\$")
            error_text = "LATEX ERROR\n" + safe_text
            if hasattr(self, "status_bar") and self.status_bar:
                self.status_bar.showMessage(f"LaTeX render error: {exc}", 5000)
            try:
                return render_text(error_text)
            except Exception:
                return QPixmap()

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
                
                item = LatexItem(m, self.render_latex, self.save_and_refresh, self.push_undo_action)
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
                    self.push_undo_action("add", {
                        "mark": new_mark,
                        "page": self.current_page_idx
                    })
                    
                    # Add to scene (pass reference to the dict object)
                    item = LatexItem(new_mark, self.render_latex, self.save_and_refresh, self.push_undo_action)
                    self.scene.addItem(item)
                    self.save_and_refresh()
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
                        self.push_undo_action("delete", {
                            "mark": dict(item.mark_data),
                            "page": self.current_page_idx
                        })
                        self.all_marks[self.current_page_idx].remove(item.mark_data)
                    self.scene.removeItem(item)
            self.save_and_refresh()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Z:
            self.undo_last_action()
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
        out_path = self.build_export_path(self.pdf_path, self.current_student_folder)
        self.export_pdf_with_marks(self.pdf_path, self.all_marks, out_path)
        QMessageBox.information(self, "Exported", f"Saved: {out_path}")

    def build_export_path(self, pdf_path, student_folder):
        if self.is_moodle_mode and self.root_folder and student_folder:
            out_root = os.path.join(
                os.path.dirname(self.root_folder),
                "marked",
                os.path.basename(self.root_folder)
            )
            student_dir = os.path.join(out_root, student_folder)
            os.makedirs(student_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            return os.path.join(student_dir, f"{base_name}_marked.pdf")
        base = os.path.splitext(pdf_path)[0]
        return f"{base}_marked.pdf"
    
    def export_pdf_with_marks(self, pdf_path, marks, out_path):

        try:
            content_source_doc = self.get_normalized_doc(pdf_path)
            export_doc = fitz.open()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open source: {e}")
            return

        for p_idx in range(len(content_source_doc)):
            source_page = content_source_doc[p_idx]

            # 1. 计算【原图 + 笔记】的总边界
            # source_page.rect 是视觉边界（已经处理了旋转），这是我们想要的“基准”
            total_rect = fitz.Rect(source_page.rect)
            
            marks_to_render = []

            # 2. 收集这一页的所有笔记
            if p_idx in marks:
                for m in marks[p_idx]:
                    pix = self.render_latex(m)
                    if pix.isNull(): continue

                    # 转换图片数据
                    ba = QBuffer()
                    ba.open(QIODevice.OpenModeFlag.ReadWrite)
                    pix.toImage().save(ba, "PNG")
                    img_data = ba.data().data()

                    # 计算笔记的视觉大小
                    w = pix.width() * 72 / RENDER_DPI
                    h = pix.height() * 72 / RENDER_DPI

                    # m['x'], m['y'] 已经是视觉坐标了
                    m_rect = fitz.Rect(m['x'], m['y'], m['x'] + w, m['y'] + h)
                    
                    # 扩展总边界
                    total_rect |= m_rect
                    marks_to_render.append((m_rect, img_data))

            # 3. 计算偏移量 (Smart Offset)
            # 如果笔记写到了左边 (x<0) 或 上边 (y<0)，我们需要把所有内容往右/下平移
            offset_x = -total_rect.x0 if total_rect.x0 < 0 else 0
            offset_y = -total_rect.y0 if total_rect.y0 < 0 else 0

            # 4. 创建新页面
            # 尺寸就是总边界的宽和高
            new_page = export_doc.new_page(width=total_rect.width, height=total_rect.height)

            # 5. 绘制原 PDF 内容 (应用偏移 + 旋转修正)
            dest_rect = fitz.Rect(
                offset_x,
                offset_y,
                offset_x + source_page.rect.width,
                offset_y + source_page.rect.height
            )

            # if source_page.rotation % 180 == 90:
            #     # 如果是横向的，交换宽高
            #     visual_clip = fitz.Rect(0, 0, source_page.cropbox.height, source_page.cropbox.width)
            # else:
            #     visual_clip = source_page.cropbox
            
            new_page.show_pdf_page(
                dest_rect,                    # 目标位置
                content_source_doc,           # 内容源
                p_idx,                        # 页码
                # clip=source_page.cropbox,     # 裁剪掉物理页面的隐藏边缘
                # rotate=-source_page.rotation, # 【核心】必须逆向旋转才能填满框
                # keep_proportion=True          # 保持比例
            )

            # 6. 绘制笔记 (应用偏移)
            for m_rect, img_data in marks_to_render:
                # 显式构造新的 Rect，加上偏移量
                final_rect = fitz.Rect(
                    m_rect.x0 + offset_x,
                    m_rect.y0 + offset_y,
                    m_rect.x1 + offset_x,
                    m_rect.y1 + offset_y
                )
                new_page.insert_image(final_rect, stream=img_data)

        try:
            export_doc.save(out_path)
            export_doc.close()
            content_source_doc.close()
            print('exported!!')
            # QMessageBox.information(self, "Export Successful", f"Saved to: {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save PDF: {exc}")

    # def export_pdf_with_marks(self, pdf_path, marks, out_path):
    #     if not self.doc:
    #         return

    #     export_doc = fitz.open()

    #     for p_idx in range(len(self.doc)):
    #         source_page = self.doc[p_idx]

    #         total_rect = fitz.Rect(source_page.rect)
    #         marks_to_render = []

    #         if p_idx in marks:
    #             for m in marks[p_idx]:
    #                 pix = self.render_latex(m)
    #                 if pix.isNull():
    #                     continue

    #                 ba = QBuffer()
    #                 ba.open(QIODevice.OpenModeFlag.ReadWrite)
    #                 pix.toImage().save(ba, "PNG")
    #                 img_data = ba.data().data()

    #                 w = pix.width() * 72 / RENDER_DPI
    #                 h = pix.height() * 72 / RENDER_DPI

    #                 m_rect = fitz.Rect(m['x'], m['y'], m['x'] + w, m['y'] + h)
    #                 total_rect |= m_rect
    #                 marks_to_render.append((m_rect, img_data))

    #         offset_x = -total_rect.x0 if total_rect.x0 < 0 else 0
    #         offset_y = -total_rect.y0 if total_rect.y0 < 0 else 0

    #         new_page = export_doc.new_page(width=total_rect.width, height=total_rect.height)

    #         dest_rect = fitz.Rect(
    #             offset_x,
    #             offset_y,
    #             offset_x + source_page.rect.width,
    #             offset_y + source_page.rect.height
    #         )
            
    #         new_page.show_pdf_page(
    #             dest_rect,                  # 目标区域（已经加上了 offset）
    #             self.doc,                   # 源文档
    #             p_idx,                      # 页码
    #             clip=source_page.cropbox,   # 【关键】只渲染可见区域，切掉乱七八糟的边缘
    #             keep_proportion=True        # 【关键】保证不拉伸，不压缩
    #         )

    #         for m_rect, img_data in marks_to_render:
    #             final_rect = fitz.Rect(
    #                 m_rect.x0 + offset_x,
    #                 m_rect.y0 + offset_y,
    #                 m_rect.x1 + offset_x,
    #                 m_rect.y1 + offset_y
    #             )
    #             new_page.insert_image(final_rect, stream=img_data)

    #     try:
    #         export_doc.save(out_path)
    #         export_doc.close()
    #         # QMessageBox.information(self, "Export Successful", f"Saved to: {out_path}")
    #     except Exception as exc:
    #         QMessageBox.critical(self, "Save Error", f"Could not save PDF: {exc}")

    def export_all_pdfs(self):
        if not self.file_list:
            QMessageBox.information(self, "Export All", "No PDFs to export.")
            return

        current_index = self.current_file_index
        current_page = self.current_page_idx
        current_pdf_path = self.pdf_path
        current_student_folder = self.current_student_folder

        unmarked = []
        for index, pdf_path in enumerate(self.file_list):
            student_folder = self.file_student_folders[index] if self.is_moodle_mode else None
            marks = {}
            sidecar_path = os.path.splitext(pdf_path)[0] + ".mlat"
            if os.path.exists(sidecar_path):
                try:
                    with open(sidecar_path, 'r') as f:
                        data = json.load(f)
                        marks = {int(k): v for k, v in data.get("all_marks", {}).items()}
                except:
                    marks = {}
            if not any(marks.values()):
                unmarked.append(os.path.basename(pdf_path))

            out_path = self.build_export_path(pdf_path, student_folder)
            self.export_pdf_with_marks(pdf_path, marks, out_path)

        if current_pdf_path:
            self.pdf_path = current_pdf_path
            self.current_student_folder = current_student_folder
            self.current_file_index = current_index
            self.doc = self.get_normalized_doc(current_pdf_path)
            self.current_page_idx = current_page
            self.load_sidecar_data()
            self.render_current_page()

        if unmarked:
            QMessageBox.information(
                self,
                "Export All",
                "Exported all PDFs. These had no marks:\n" + "\n".join(unmarked)
            )
        else:
            QMessageBox.information(self, "Export All", "Exported all PDFs.")

    def push_undo_action(self, action_type, payload):
        payload["type"] = action_type
        self.undo_stack.append(payload)
        if len(self.undo_stack) > self.undo_limit:
            self.undo_stack.pop(0)

    def undo_last_action(self):
        if not self.undo_stack:
            return

        action = self.undo_stack.pop()
        action_type = action.get("type")

        if action_type == "add":
            page = action["page"]
            mark = action["mark"]
            if page in self.all_marks and mark in self.all_marks[page]:
                self.all_marks[page].remove(mark)
        elif action_type == "delete":
            page = action["page"]
            mark = action["mark"]
            self.all_marks.setdefault(page, []).append(mark)
        elif action_type == "edit":
            before = action["before"]
            mark = action.get("mark")
            if mark in self.all_marks.get(self.current_page_idx, []):
                mark.update(before)
        elif action_type == "move":
            mark = action["mark"]
            before = action["before"]
            mark["x"], mark["y"] = before

        self.save_and_refresh()

    def save_and_refresh(self):
        self.save_sidecar()
        self.refresh_remark_tree()

    def refresh_remark_tree(self):
        if not self.file_list_widget or self.file_list_widget.topLevelItemCount() == 0:
            return
        for i in range(self.file_list_widget.topLevelItemCount()):
            parent_item = self.file_list_widget.topLevelItem(i)
            parent_item.takeChildren()
            pdf_path = self.file_list[i]
            sidecar_path = os.path.splitext(pdf_path)[0] + ".mlat"
            if not os.path.exists(sidecar_path):
                continue
            try:
                with open(sidecar_path, 'r') as f:
                    data = json.load(f)
            except:
                continue
            all_marks = {int(k): v for k, v in data.get("all_marks", {}).items()}
            remarks = []
            for page_idx, marks in all_marks.items():
                for mark in marks:
                    text = mark.get("text", "").strip()
                    if not text:
                        continue
                    remarks.append((page_idx, mark.get("y", 0), text))
            remarks.sort(key=lambda item: (item[0], item[1]))
            for page_idx, y_val, text in remarks:
                child = QTreeWidgetItem([text])
                child.setData(0, Qt.ItemDataRole.UserRole, i)
                child.setData(0, Qt.ItemDataRole.UserRole + 1, page_idx)
                parent_item.addChild(child)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MarkLatexApp()
    window.show()
    sys.exit(app.exec())