"""
MRZ Scanner GUI Application using PySide6 and Dynamsoft Capture Vision SDK.

Features:
- Input sources: Image files (single/folder), camera stream
- Drag-and-drop, clipboard paste, and load button support
- Real-time overlay of portrait (face) area and MRZ location
- Panel showing MRZ raw string and parsed results
"""

import sys
import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QSplitter,
    QComboBox, QGroupBox, QListWidget, QListWidgetItem, QFrame,
    QScrollArea, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QMimeData, QUrl
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont, QDragEnterEvent, QDropEvent, QClipboard

from dynamsoft_capture_vision_bundle import *

# Suppress OpenCV logging
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except AttributeError:
    pass


# ==============================================================================
# Data Classes and Helper Classes
# ==============================================================================

@dataclass
class MRZResult:
    """Stores parsed MRZ result data."""
    raw_lines: List[str]
    doc_type: str
    doc_id: str
    surname: str
    given_name: str
    nationality: str
    issuer: str
    gender: str
    date_of_birth: str
    date_of_expiry: str
    is_passport: bool
    mrz_locations: List['Quadrilateral']
    portrait_zone: Optional['Quadrilateral'] = None


class NeededResultUnit:
    """Container class for intermediate result units needed for portrait extraction."""
    def __init__(self):
        self.deskewed_image_unit = None
        self.localized_text_lines_unit = None
        self.scaled_colour_img_unit = None
        self.detected_quads_unit = None
        self.recognized_text_lines_unit = None


class MyIntermediateResultReceiver(IntermediateResultReceiver):
    """Custom receiver to intercept and store intermediate processing results."""

    def __init__(self, cvr: CaptureVisionRouter):
        super().__init__()
        self.cvr = cvr
        self.unit_groups: Dict[str, NeededResultUnit] = {}

    def on_deskewed_image_received(self, result: "DeskewedImageUnit", info: IntermediateResultExtraInfo) -> None:
        if info.is_section_level_result:
            id = result.get_original_image_hash_id()
            if self.unit_groups.get(id) is None:
                self.unit_groups[id] = NeededResultUnit()
            self.unit_groups[id].deskewed_image_unit = result

    def on_localized_text_lines_received(self, result: "LocalizedTextLinesUnit", info: IntermediateResultExtraInfo) -> None:
        if info.is_section_level_result:
            id = result.get_original_image_hash_id()
            if self.unit_groups.get(id) is None:
                self.unit_groups[id] = NeededResultUnit()
            self.unit_groups[id].localized_text_lines_unit = result

    def on_scaled_colour_image_unit_received(self, result: ScaledColourImageUnit, info: IntermediateResultExtraInfo) -> None:
        id = result.get_original_image_hash_id()
        if self.unit_groups.get(id) is None:
            self.unit_groups[id] = NeededResultUnit()
        self.unit_groups[id].scaled_colour_img_unit = result

    def on_recognized_text_lines_received(self, result: RecognizedTextLinesUnit, info: IntermediateResultExtraInfo) -> None:
        if info.is_section_level_result:
            id = result.get_original_image_hash_id()
            if self.unit_groups.get(id) is None:
                self.unit_groups[id] = NeededResultUnit()
            self.unit_groups[id].recognized_text_lines_unit = result

    def on_detected_quads_received(self, result: DetectedQuadsUnit, info: IntermediateResultExtraInfo) -> None:
        if info.is_section_level_result:
            id = result.get_original_image_hash_id()
            if self.unit_groups.get(id) is None:
                self.unit_groups[id] = NeededResultUnit()
            self.unit_groups[id].detected_quads_unit = result

    def get_portrait_zone(self, hash_id: str) -> Optional['Quadrilateral']:
        if self.unit_groups.get(hash_id) is None:
            return None
        id_processor = IdentityProcessor()
        units = self.unit_groups[hash_id]
        ret, portrait_zone = id_processor.find_portrait_zone(
            units.scaled_colour_img_unit,
            units.localized_text_lines_unit,
            units.recognized_text_lines_unit,
            units.detected_quads_unit,
            units.deskewed_image_unit
        )
        if ret != EnumErrorCode.EC_OK:
            return None
        return portrait_zone

    def clear(self):
        """Clear all stored intermediate results."""
        self.unit_groups.clear()


class DCPResultProcessor:
    """Helper class to parse ParsedResultItem into structured MRZ data."""
    
    def __init__(self, item: ParsedResultItem):
        self.doc_type = item.get_code_type()
        self.raw_text = []
        self.doc_id = None
        self.surname = None
        self.given_name = None
        self.nationality = None
        self.issuer = None
        self.gender = None
        self.date_of_birth = None
        self.date_of_expiry = None
        self.is_passport = False
        # self.location = item.get_location()

        if self.doc_type == "MRTD_TD3_PASSPORT":
            if item.get_field_value("passportNumber") is not None and item.get_field_validation_status("passportNumber") != EnumValidationStatus.VS_FAILED:
                self.doc_id = item.get_field_value("passportNumber")
            elif item.get_field_value("documentNumber") is not None and item.get_field_validation_status("documentNumber") != EnumValidationStatus.VS_FAILED:
                self.doc_id = item.get_field_value("documentNumber")
            self.is_passport = True

        for i in range(1, 4):
            line = item.get_field_value(f"line{i}")
            if line is not None:
                if item.get_field_validation_status(f"line{i}") == EnumValidationStatus.VS_FAILED:
                    line += " [Validation Failed]"
                self.raw_text.append(line)

        if item.get_field_value("nationality") is not None and item.get_field_validation_status("nationality") != EnumValidationStatus.VS_FAILED:
            self.nationality = item.get_field_value("nationality")
        if item.get_field_value("issuingState") is not None and item.get_field_validation_status("issuingState") != EnumValidationStatus.VS_FAILED:
            self.issuer = item.get_field_value("issuingState")
        if item.get_field_value("dateOfBirth") is not None and item.get_field_validation_status("dateOfBirth") != EnumValidationStatus.VS_FAILED:
            self.date_of_birth = item.get_field_value("dateOfBirth")
        if item.get_field_value("dateOfExpiry") is not None and item.get_field_validation_status("dateOfExpiry") != EnumValidationStatus.VS_FAILED:
            self.date_of_expiry = item.get_field_value("dateOfExpiry")
        if item.get_field_value("sex") is not None and item.get_field_validation_status("sex") != EnumValidationStatus.VS_FAILED:
            self.gender = item.get_field_value("sex")
        if item.get_field_value("primaryIdentifier") is not None and item.get_field_validation_status("primaryIdentifier") != EnumValidationStatus.VS_FAILED:
            self.surname = item.get_field_value("primaryIdentifier")
        if item.get_field_value("secondaryIdentifier") is not None and item.get_field_validation_status("secondaryIdentifier") != EnumValidationStatus.VS_FAILED:
            self.given_name = item.get_field_value("secondaryIdentifier")

    def to_mrz_result(self, portrait_zone=None, mrz_locations=None) -> MRZResult:
        if mrz_locations is None:
            mrz_locations = []
            
        return MRZResult(
            raw_lines=self.raw_text,
            doc_type=self.doc_type or "",
            doc_id=self.doc_id or "",
            surname=self.surname or "",
            given_name=self.given_name or "",
            nationality=self.nationality or "",
            issuer=self.issuer or "",
            gender=self.gender or "",
            date_of_birth=self.date_of_birth or "",
            date_of_expiry=self.date_of_expiry or "",
            is_passport=self.is_passport,
            mrz_locations=mrz_locations,
            portrait_zone=portrait_zone
        )


# ==============================================================================
# Camera Capture Thread
# ==============================================================================

class CameraCaptureThread(QThread):
    """Thread for capturing camera frames and processing MRZ."""
    
    frame_ready = Signal(np.ndarray, list)  # frame, list of MRZResult
    error_occurred = Signal(str)
    
    def __init__(self, cvr: CaptureVisionRouter, irm, camera_index: int = 0):
        super().__init__()
        self.cvr = cvr
        self.irm = irm
        self.camera_index = camera_index
        self.running = False
        self.irr = None
        
    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.camera_index)
        
        if not cap.isOpened():
            self.error_occurred.emit(f"Failed to open camera {self.camera_index}")
            return
        
        # Set camera resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Setup intermediate result receiver
        if self.irr is not None:
            self.irm.remove_result_receiver(self.irr)
        self.irr = MyIntermediateResultReceiver(self.cvr)
        self.irm.add_result_receiver(self.irr)
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Clear previous intermediate results
            self.irr.clear()
            
            # Process the frame
            mrz_results = self._process_frame(frame)
            
            # Emit the frame and results
            self.frame_ready.emit(frame.copy(), mrz_results)
            
        cap.release()
        
        # Cleanup
        if self.irr is not None:
            self.irm.remove_result_receiver(self.irr)
            self.irr = None
    
    def _process_frame(self, frame: np.ndarray) -> List[MRZResult]:
        """Process a single frame and return MRZ results."""
        results = []
        
        try:
            # Convert frame to ImageData format for the SDK
            height, width = frame.shape[:2]
            
            # Capture using the SDK
            result = self.cvr.capture(frame, "ReadPassportAndId")
            
            if result is None:
                return results
                
            parsed_result = result.get_parsed_result()
            if parsed_result is None:
                return results

            # Get locations from recognized text lines
            mrz_locations = []
            line_result = result.get_recognized_text_lines_result()
            if line_result is not None:
                for item in line_result.get_items():
                    mrz_locations.append(item.get_location())

            hash_id = result.get_original_image_hash_id()
            
            for item in parsed_result.get_items():
                processor = DCPResultProcessor(item)
                portrait_zone = None
                if processor.is_passport and self.irr:
                    portrait_zone = self.irr.get_portrait_zone(hash_id)
                mrz_result = processor.to_mrz_result(portrait_zone, mrz_locations)
                results.append(mrz_result)
                
        except Exception as e:
            print(f"Error processing frame: {e}")
            
        return results
    
    def stop(self):
        self.running = False
        self.wait()


# ==============================================================================
# Image Display Widget with Overlays
# ==============================================================================

class ImageDisplayWidget(QLabel):
    """Widget for displaying images with MRZ and portrait overlays."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #2d2d2d; border: 2px dashed #555;")
        self.setText("Drop image here or use Load button")
        
        self.current_image: Optional[np.ndarray] = None
        self.mrz_results: List[MRZResult] = []
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
    def set_image(self, image: np.ndarray, mrz_results: List[MRZResult] = None):
        """Set the image and optionally MRZ results to display."""
        self.current_image = image
        self.mrz_results = mrz_results or []
        self._update_display()
        
    def _update_display(self):
        """Update the displayed image with overlays."""
        if self.current_image is None:
            return
            
        # Convert BGR to RGB
        if len(self.current_image.shape) == 3:
            rgb_image = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = cv2.cvtColor(self.current_image, cv2.COLOR_GRAY2RGB)
        
        # Create QImage
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale to fit the widget while maintaining aspect ratio
        pixmap = QPixmap.fromImage(q_image)
        
        # Calculate scale factor for overlay coordinate mapping
        widget_size = self.size()
        scaled_pixmap = pixmap.scaled(
            widget_size, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        self.scale_factor = scaled_pixmap.width() / w
        self.offset_x = (widget_size.width() - scaled_pixmap.width()) // 2
        self.offset_y = (widget_size.height() - scaled_pixmap.height()) // 2
        
        # Draw overlays on the pixmap
        if self.mrz_results:
            painter = QPainter(scaled_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            for result in self.mrz_results:
                # Draw MRZ locations
                if result.mrz_locations:
                    for location in result.mrz_locations:
                        self._draw_quadrilateral(
                            painter, 
                            location, 
                            QColor(0, 255, 0, 200),  # Green
                            "MRZ"
                        )
                
                # Draw portrait zone
                if result.portrait_zone:
                    self._draw_quadrilateral(
                        painter, 
                        result.portrait_zone, 
                        QColor(255, 165, 0, 200),  # Orange
                        "Portrait"
                    )
            
            painter.end()
        
        self.setPixmap(scaled_pixmap)
        
    def _draw_quadrilateral(self, painter: QPainter, quad, color: QColor, label: str):
        """Draw a quadrilateral overlay with label."""
        pen = QPen(color, 3)
        painter.setPen(pen)
        
        points = quad.points
        if len(points) >= 4:
            # Scale points
            scaled_points = []
            for p in points:
                x = int(p.x * self.scale_factor)
                y = int(p.y * self.scale_factor)
                scaled_points.append((x, y))
            
            # Draw quadrilateral
            for i in range(4):
                x1, y1 = scaled_points[i]
                x2, y2 = scaled_points[(i + 1) % 4]
                painter.drawLine(x1, y1, x2, y2)
            
            # Draw label
            font = QFont("Arial", 12, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QPen(color, 2))
            
            # Position label above the quadrilateral
            min_y = min(p[1] for p in scaled_points)
            min_x = min(p[0] for p in scaled_points)
            painter.drawText(min_x, max(0, min_y - 5), label)
    
    def clear_display(self):
        """Clear the current display."""
        self.current_image = None
        self.mrz_results = []
        self.setPixmap(QPixmap())
        self.setText("Drop image here or use Load button")
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
            self.setStyleSheet("background-color: #3d3d4d; border: 2px dashed #88f;")
        
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        self.setStyleSheet("background-color: #2d2d2d; border: 2px dashed #555;")
        
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        self.setStyleSheet("background-color: #2d2d2d; border: 2px dashed #555;")
        
        mime_data = event.mimeData()
        
        if mime_data.hasUrls():
            urls = mime_data.urls()
            paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if paths:
                # Emit signal or call parent method
                parent = self.parent()
                while parent and not isinstance(parent, MRZScannerWindow):
                    parent = parent.parent()
                if parent:
                    parent.handle_dropped_files(paths)
                    
        event.acceptProposedAction()

    def resizeEvent(self, event):
        """Handle resize event."""
        super().resizeEvent(event)
        if self.current_image is not None:
            self._update_display()


# ==============================================================================
# Main Application Window
# ==============================================================================

class MRZScannerWindow(QMainWindow):
    """Main window for the MRZ Scanner GUI application."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MRZ Scanner - Dynamsoft Capture Vision")
        self.setMinimumSize(1200, 800)
        
        # Initialize SDK
        self._init_sdk()
        
        # Camera thread
        self.camera_thread: Optional[CameraCaptureThread] = None
        
        # Current file list for folder processing
        self.file_list: List[str] = []
        self.current_file_index = 0
        
        # Setup UI
        self._setup_ui()
        
        # Setup clipboard monitoring
        self.clipboard = QApplication.clipboard()
        
    def _init_sdk(self):
        """Initialize the Dynamsoft Capture Vision SDK."""
        # Initialize license
        error_code, error_message = LicenseManager.init_license(
            "DLS2eyJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSJ9"
        )
        
        if error_code != EnumErrorCode.EC_OK and error_code != EnumErrorCode.EC_LICENSE_WARNING:
            QMessageBox.warning(
                None, 
                "License Error",
                f"License initialization failed: {error_message}"
            )
        
        # Create CaptureVisionRouter
        self.cvr = CaptureVisionRouter()
        
        # Get IntermediateResultManager
        self.irm = self.cvr.get_intermediate_result_manager()
        
        # Create intermediate result receiver for image processing
        self.irr = MyIntermediateResultReceiver(self.cvr)
        self.irm.add_result_receiver(self.irr)
        
    def _setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Input controls and image display
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Input source group
        input_group = QGroupBox("Input Source")
        input_layout = QVBoxLayout(input_group)
        
        # Source type selector
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Image File", "Image Folder", "Camera"])
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        source_layout.addWidget(self.source_combo)
        input_layout.addLayout(source_layout)
        
        # Camera selector (hidden by default)
        self.camera_layout = QHBoxLayout()
        self.camera_layout.addWidget(QLabel("Camera:"))
        self.camera_combo = QComboBox()
        self._populate_cameras()
        self.camera_layout.addWidget(self.camera_combo)
        self.camera_widget = QWidget()
        self.camera_widget.setLayout(self.camera_layout)
        self.camera_widget.setVisible(False)
        input_layout.addWidget(self.camera_widget)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load File/Folder")
        self.load_btn.clicked.connect(self._on_load_clicked)
        button_layout.addWidget(self.load_btn)
        
        self.paste_btn = QPushButton("Paste from Clipboard")
        self.paste_btn.clicked.connect(self._on_paste_clicked)
        button_layout.addWidget(self.paste_btn)
        
        self.start_stop_btn = QPushButton("Start Camera")
        self.start_stop_btn.clicked.connect(self._on_start_stop_clicked)
        self.start_stop_btn.setVisible(False)
        button_layout.addWidget(self.start_stop_btn)
        
        input_layout.addLayout(button_layout)
        
        # File list for folder mode
        self.file_list_widget = QListWidget()
        self.file_list_widget.itemClicked.connect(self._on_file_selected)
        self.file_list_widget.setMaximumHeight(150)
        self.file_list_widget.setVisible(False)
        input_layout.addWidget(self.file_list_widget)
        
        # Navigation buttons for folder mode
        self.nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self._on_prev_clicked)
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self._on_next_clicked)
        self.nav_layout.addWidget(self.prev_btn)
        self.nav_layout.addWidget(self.next_btn)
        self.nav_widget = QWidget()
        self.nav_widget.setLayout(self.nav_layout)
        self.nav_widget.setVisible(False)
        input_layout.addWidget(self.nav_widget)
        
        left_layout.addWidget(input_group)
        
        # Image display area
        display_group = QGroupBox("Image / Camera View")
        display_layout = QVBoxLayout(display_group)
        
        self.image_display = ImageDisplayWidget()
        display_layout.addWidget(self.image_display)
        
        left_layout.addWidget(display_group, 1)
        
        # Right panel - Results
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # MRZ Raw Text
        raw_group = QGroupBox("MRZ Raw Text")
        raw_layout = QVBoxLayout(raw_group)
        self.raw_text_edit = QTextEdit()
        self.raw_text_edit.setReadOnly(True)
        self.raw_text_edit.setFont(QFont("Courier New", 10))
        self.raw_text_edit.setMaximumHeight(120)
        raw_layout.addWidget(self.raw_text_edit)
        right_layout.addWidget(raw_group)
        
        # Parsed Results
        parsed_group = QGroupBox("Parsed Results")
        parsed_layout = QVBoxLayout(parsed_group)
        self.parsed_text_edit = QTextEdit()
        self.parsed_text_edit.setReadOnly(True)
        self.parsed_text_edit.setFont(QFont("Segoe UI", 10))
        parsed_layout.addWidget(self.parsed_text_edit)
        right_layout.addWidget(parsed_group, 1)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 400])
        
        # Status bar
        self.statusBar().showMessage("Ready. Load an image or start camera to begin scanning.")
        
    def _populate_cameras(self):
        """Populate the camera dropdown with available cameras."""
        self.camera_combo.clear()
        
        # Check for available cameras (check first 5 indices)
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.camera_combo.addItem(f"Camera {i}", i)
            else:
                break
                cap.release()
                
        if self.camera_combo.count() == 0:
            self.camera_combo.addItem("No cameras found", -1)
            
    def _on_source_changed(self, source: str):
        """Handle source type change."""
        is_camera = source == "Camera"
        is_folder = source == "Image Folder"
        
        self.camera_widget.setVisible(is_camera)
        self.start_stop_btn.setVisible(is_camera)
        self.load_btn.setVisible(not is_camera)
        self.paste_btn.setVisible(not is_camera)
        self.file_list_widget.setVisible(is_folder)
        self.nav_widget.setVisible(is_folder)
        
        # Stop camera if switching away from camera mode
        if not is_camera and self.camera_thread is not None:
            self._stop_camera()
            
        # Update load button text
        if is_folder:
            self.load_btn.setText("Load Folder")
        else:
            self.load_btn.setText("Load File")
            
    def _on_load_clicked(self):
        """Handle load button click."""
        source = self.source_combo.currentText()
        
        if source == "Image Folder":
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Image Folder",
                "",
                QFileDialog.ShowDirsOnly
            )
            if folder_path:
                self._load_folder(folder_path)
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Image File",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.pdf);;All Files (*.*)"
            )
            if file_path:
                self._process_image_file(file_path)
                
    def _on_paste_clicked(self):
        """Handle paste from clipboard."""
        mime_data = self.clipboard.mimeData()
        
        if mime_data.hasImage():
            # Get image from clipboard
            q_image = self.clipboard.image()
            if not q_image.isNull():
                # Convert QImage to numpy array
                q_image = q_image.convertToFormat(QImage.Format_RGB888)
                width = q_image.width()
                height = q_image.height()
                
                ptr = q_image.constBits()
                stride = q_image.bytesPerLine()
                
                # Reshape with stride, then crop to actual width
                arr = np.array(ptr).reshape(height, stride)
                arr = arr[:, :width * 3]
                arr = arr.reshape(height, width, 3)
                
                # Convert RGB to BGR for OpenCV
                bgr_image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                
                self._process_image(bgr_image, "Clipboard Image")
                self.statusBar().showMessage("Processed image from clipboard")
                return
                
        if mime_data.hasUrls():
            urls = mime_data.urls()
            paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if paths:
                self.handle_dropped_files(paths)
                return
                
        if mime_data.hasText():
            # Check if text is a file path
            text = mime_data.text().strip()
            if os.path.exists(text):
                if os.path.isfile(text):
                    self._process_image_file(text)
                elif os.path.isdir(text):
                    self._load_folder(text)
                return
                
        self.statusBar().showMessage("No valid image data in clipboard")
        
    def handle_dropped_files(self, paths: List[str]):
        """Handle files dropped onto the image display."""
        if not paths:
            return
            
        # Check if it's a folder
        if len(paths) == 1 and os.path.isdir(paths[0]):
            self.source_combo.setCurrentText("Image Folder")
            self._load_folder(paths[0])
            return
            
        # Filter for image files
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.pdf'}
        image_files = [p for p in paths if Path(p).suffix.lower() in image_extensions]
        
        if len(image_files) == 1:
            self.source_combo.setCurrentText("Image File")
            self._process_image_file(image_files[0])
        elif len(image_files) > 1:
            # Multiple files - treat as folder mode
            self.source_combo.setCurrentText("Image Folder")
            self._load_file_list(image_files)
            
    def _load_folder(self, folder_path: str):
        """Load all images from a folder."""
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.pdf'}
        
        files = []
        for f in Path(folder_path).iterdir():
            if f.is_file() and f.suffix.lower() in image_extensions:
                files.append(str(f))
                
        files.sort()
        self._load_file_list(files)
        
    def _load_file_list(self, files: List[str]):
        """Load a list of files for processing."""
        self.file_list = files
        self.current_file_index = 0
        
        # Update file list widget
        self.file_list_widget.clear()
        for f in files:
            self.file_list_widget.addItem(Path(f).name)
            
        self.file_list_widget.setVisible(True)
        self.nav_widget.setVisible(True)
        
        if files:
            self.file_list_widget.setCurrentRow(0)
            self._process_image_file(files[0])
            
        self.statusBar().showMessage(f"Loaded {len(files)} images from folder")
        
    def _on_file_selected(self, item: QListWidgetItem):
        """Handle file selection from list."""
        index = self.file_list_widget.row(item)
        if 0 <= index < len(self.file_list):
            self.current_file_index = index
            self._process_image_file(self.file_list[index])
            
    def _on_prev_clicked(self):
        """Navigate to previous file."""
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self.file_list_widget.setCurrentRow(self.current_file_index)
            self._process_image_file(self.file_list[self.current_file_index])
            
    def _on_next_clicked(self):
        """Navigate to next file."""
        if self.current_file_index < len(self.file_list) - 1:
            self.current_file_index += 1
            self.file_list_widget.setCurrentRow(self.current_file_index)
            self._process_image_file(self.file_list[self.current_file_index])
            
    def _on_start_stop_clicked(self):
        """Handle camera start/stop button."""
        if self.camera_thread is None or not self.camera_thread.isRunning():
            self._start_camera()
        else:
            self._stop_camera()
            
    def _start_camera(self):
        """Start the camera capture."""
        camera_index = self.camera_combo.currentData()
        if camera_index is None or camera_index < 0:
            self.statusBar().showMessage("No valid camera selected")
            return
            
        self.camera_thread = CameraCaptureThread(self.cvr, self.irm, camera_index)
        self.camera_thread.frame_ready.connect(self._on_camera_frame)
        self.camera_thread.error_occurred.connect(self._on_camera_error)
        self.camera_thread.start()
        
        self.start_stop_btn.setText("Stop Camera")
        self.statusBar().showMessage("Camera started")
        
    def _stop_camera(self):
        """Stop the camera capture."""
        if self.camera_thread is not None:
            self.camera_thread.stop()
            self.camera_thread = None
            
        self.start_stop_btn.setText("Start Camera")
        self.statusBar().showMessage("Camera stopped")
        
    def _on_camera_frame(self, frame: np.ndarray, results: List[MRZResult]):
        """Handle camera frame with results."""
        self.image_display.set_image(frame, results)
        self._update_results_display(results)
        
    def _on_camera_error(self, error: str):
        """Handle camera error."""
        self.statusBar().showMessage(f"Camera error: {error}")
        self._stop_camera()
        
    def _process_image_file(self, file_path: str):
        """Process an image file."""
        if not os.path.exists(file_path):
            self.statusBar().showMessage(f"File not found: {file_path}")
            return
            
        # Read image
        image = cv2.imread(file_path)
        if image is None:
            # Try using the SDK for PDF or other formats
            try:
                result_array = self.cvr.capture_multi_pages(file_path, "ReadPassportAndId")
                results = result_array.get_results()
                if results:
                    # Process first page
                    result = results[0]
                    self._process_captured_result(result, file_path)
                    return
            except Exception as e:
                self.statusBar().showMessage(f"Failed to load image: {file_path}")
                return
        else:
            self._process_image(image, file_path)
            
    def _process_image(self, image: np.ndarray, source_name: str):
        """Process an image and display results."""
        self.statusBar().showMessage(f"Processing: {source_name}")
        
        # Clear previous intermediate results
        self.irr.clear()
        
        try:
            # Capture using the SDK
            result = self.cvr.capture(image, "ReadPassportAndId")
            
            if result is None:
                self.image_display.set_image(image, [])
                self._update_results_display([])
                self.statusBar().showMessage("No MRZ detected")
                return
                
            # Process the result
            mrz_results = self._extract_mrz_results(result)
            
            # Update display
            self.image_display.set_image(image, mrz_results)
            self._update_results_display(mrz_results)
            
            if mrz_results:
                self.statusBar().showMessage(f"Found {len(mrz_results)} MRZ zone(s)")
            else:
                self.statusBar().showMessage("No MRZ detected")
                
        except Exception as e:
            self.statusBar().showMessage(f"Error processing image: {str(e)}")
            self.image_display.set_image(image, [])
            
    def _process_captured_result(self, result: CapturedResult, file_path: str):
        """Process a CapturedResult from multi-page capture."""
        mrz_results = self._extract_mrz_results(result)
        
        # Try to get original image
        original_image = None
        for item in result.get_items():
            if isinstance(item, OriginalImageResultItem):
                img_data = item.get_image_data()
                if img_data:
                    # Convert ImageData to numpy array
                    # This is a simplified conversion - actual implementation may vary
                    original_image = cv2.imread(file_path)
                    break
                    
        if original_image is not None:
            self.image_display.set_image(original_image, mrz_results)
        else:
            # If we can't get the original image, just load it directly
            image = cv2.imread(file_path)
            if image is not None:
                self.image_display.set_image(image, mrz_results)
                
        self._update_results_display(mrz_results)
        
        if mrz_results:
            self.statusBar().showMessage(f"Found {len(mrz_results)} MRZ zone(s)")
        else:
            self.statusBar().showMessage("No MRZ detected")
            
    def _extract_mrz_results(self, result: CapturedResult) -> List[MRZResult]:
        """Extract MRZ results from a CapturedResult."""
        mrz_results = []
        
        parsed_result = result.get_parsed_result()
        if parsed_result is None or len(parsed_result.get_items()) == 0:
            return mrz_results

        # Get locations from recognized text lines
        mrz_locations = []
        line_result = result.get_recognized_text_lines_result()
        if line_result is not None:
            for item in line_result.get_items():
                mrz_locations.append(item.get_location())
            
        hash_id = result.get_original_image_hash_id()
        
        for item in parsed_result.get_items():
            processor = DCPResultProcessor(item)
            portrait_zone = None
            if processor.is_passport and self.irr:
                portrait_zone = self.irr.get_portrait_zone(hash_id)
            mrz_result = processor.to_mrz_result(portrait_zone, mrz_locations)
            mrz_results.append(mrz_result)
            
        return mrz_results
        
    def _update_results_display(self, results: List[MRZResult]):
        """Update the results text displays."""
        if not results:
            self.raw_text_edit.clear()
            self.parsed_text_edit.clear()
            return
            
        # Raw text
        raw_text = ""
        for i, result in enumerate(results):
            if len(results) > 1:
                raw_text += f"=== MRZ Zone {i + 1} ===\n"
            for j, line in enumerate(result.raw_lines):
                raw_text += f"Line {j + 1}: {line}\n"
            raw_text += "\n"
        self.raw_text_edit.setPlainText(raw_text.strip())
        
        # Parsed results
        parsed_text = ""
        for i, result in enumerate(results):
            if len(results) > 1:
                parsed_text += f"═══ MRZ Zone {i + 1} ═══\n\n"
                
            parsed_text += f"📄 Document Type: {result.doc_type}\n"
            parsed_text += f"🆔 Document ID: {result.doc_id}\n"
            parsed_text += f"👤 Surname: {result.surname}\n"
            parsed_text += f"👤 Given Name: {result.given_name}\n"
            parsed_text += f"🌍 Nationality: {result.nationality}\n"
            parsed_text += f"🏛️ Issuing Country: {result.issuer}\n"
            parsed_text += f"⚧ Gender: {result.gender}\n"
            parsed_text += f"🎂 Date of Birth: {self._format_date(result.date_of_birth)}\n"
            parsed_text += f"📅 Expiry Date: {self._format_date(result.date_of_expiry)}\n"
            
            if result.portrait_zone:
                parsed_text += f"🖼️ Portrait: Detected\n"
            else:
                parsed_text += f"🖼️ Portrait: Not detected\n"
                
            parsed_text += "\n"
            
        self.parsed_text_edit.setPlainText(parsed_text.strip())
        
    def _format_date(self, date_str: str) -> str:
        """Format YYMMDD date string to more readable format."""
        if not date_str or len(date_str) != 6:
            return date_str
        try:
            year = int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            
            # Determine century (assuming 00-30 is 2000s, 31-99 is 1900s)
            if year <= 30:
                year += 2000
            else:
                year += 1900
                
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return date_str
            
    def closeEvent(self, event):
        """Handle window close event."""
        # Stop camera if running
        if self.camera_thread is not None:
            self._stop_camera()
            
        # Remove intermediate result receiver
        if self.irr is not None:
            self.irm.remove_result_receiver(self.irr)
            
        event.accept()


# ==============================================================================
# Application Entry Point
# ==============================================================================

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Dark theme palette
    from PySide6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    window = MRZScannerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
