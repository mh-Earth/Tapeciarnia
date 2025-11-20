from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QSizePolicy, QMessageBox
)
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QTimer

from utils.path_utils import SAVES_DIR
import logging
from pathlib import Path
import os
import shutil


class FadeOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._pixmap_old = None
        self._pixmap_new = None
        self._opacity = 0.0
        self._anim = None
        if parent:
            self.resize(parent.size())
        else:
            self.resize(800, 600)

    def set_pixmaps(self, old, new):
        self._pixmap_old = old
        self._pixmap_new = new
        self._opacity = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self._pixmap_old:
            painter.setOpacity(1.0)
            painter.drawPixmap(self.rect(), self._pixmap_old)
        if self._pixmap_new:
            painter.setOpacity(self._opacity)
            painter.drawPixmap(self.rect(), self._pixmap_new)

    def animate_to(self, duration=600):
        anim = QPropertyAnimation(self, b"overlayOpacity", self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        self._anim = anim

    def getOpacity(self):
        return self._opacity

    def setOpacity(self, v):
        self._opacity = float(v)
        self.update()

    overlayOpacity = Property(float, getOpacity, setOpacity)


class DownloadProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Video")
        self.setModal(True)
        self.setFixedSize(400, 120)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Preparing download...", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        
        self.percentage_label = QLabel("0%", self)
        self.percentage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.percentage_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.details_label = QLabel("Starting download...", self)
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.details_label.setStyleSheet("font-size: 11px; color: #666;")
        
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.percentage_label)
        layout.addWidget(self.details_label)

    def update_progress(self, percent: float, status_msg: str = ""):
        percent_int = int(percent)
        self.progress.setValue(percent_int)
        self.percentage_label.setText(f"{percent_int}%")
        
        if status_msg:
            if "Downloading..." in status_msg:
                details = status_msg.replace("Downloading... ", "")
                self.details_label.setText(details)
            else:
                self.details_label.setText(status_msg)
        
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()


class EnhancedDragDropWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        logging.debug("Initializing EnhancedDragDropWidget")
        self.dropped_file_path = None
        self.original_wallpaper = None
        self.parent_app = parent
        self.setup_ui()
        self.update_language()
    
    # Function for toggling visibility of buttons and upload icon
    def toggle_buttons_visibility(self, visible: bool):
        logging.debug(f"Toggling buttons visibility: {visible}")
        if visible:
            self.buttons_widget.show()
            self.uploadIcon.hide()
        else:
            self.buttons_widget.hide()
            self.uploadIcon.show()

    def setup_ui(self):
        logging.debug("Setting up EnhancedDragDropWidget UI")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Drag & drop area
        self.parent_app.ui.uploadArea.dragEnterEvent = self.dragEnterEvent
        self.parent_app.ui.uploadArea.dropEvent = self.dropEvent
        self.parent_app.ui.uploadArea.dragLeaveEvent = self.dragLeaveEvent
        
        
        # Upload text
        self.upload_text = QLabel(self.parent_app.lang["uploadSection"]["dragDropInstruction"])
        self.upload_text.setAlignment(Qt.AlignCenter)
        self.upload_text.setAcceptDrops(True)
        self.upload_text.setSizePolicy(self.upload_text.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
        self.upload_text.setProperty('class',"MainUILable")
        
        # Supported formats label
        self.supported_label = QLabel(self.parent_app.lang["uploadSection"]["supportedFormatsHint"])
        self.supported_label.setAlignment(Qt.AlignCenter)
        self.supported_label.setSizePolicy(self.supported_label.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
        self.supported_label.setProperty('class',"MainUILable")
        
        # Action buttons (initially hidden)
        self.buttons_widget = QWidget()
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(20, 10, 20, 10)
        buttons_layout.setSpacing(15)
        
        # Set as Wallpaper button (appears after selecting collection/favorites)
        self.upload_btn = QPushButton(self.parent_app.lang["uploadSection"]["setAsWallpaperButton"])
        self.upload_btn.clicked.connect(self.set_as_wallpaper)
        self.upload_btn.setProperty("class", "primary")
        self.upload_btn.setMinimumHeight(35)
        self.upload_btn.setVisible(False)  # Hidden initially
        
        # Reset button (always visible when file is selected)
        self.reset_btn = QPushButton(self.parent_app.lang["settings"]["resetButton"])
        self.reset_btn.clicked.connect(self.reset_selection)
        self.reset_btn.setProperty("class", "ghost")
        self.reset_btn.setMinimumHeight(35)
        self.reset_btn.setVisible(False)  # Hidden initially

        buttons_layout.addWidget(self.upload_btn)
        buttons_layout.addWidget(self.reset_btn)
        
        self.buttons_widget.setLayout(buttons_layout)
        self.buttons_widget.hide()
        
        # Upload icon (initially visible)
        self.uploadIcon = QLabel()
        self.uploadIcon.setPixmap(QPixmap(":/icons/icons/upload.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.uploadIcon.setAlignment(Qt.AlignCenter)
        self.uploadIcon.setStyleSheet("padding:0px;")
        self.uploadIcon.setSizePolicy(self.uploadIcon.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)

        
        layout.addWidget(self.uploadIcon)
        layout.addWidget(self.upload_text)
        layout.addWidget(self.supported_label)
        layout.addWidget(self.buttons_widget)
        
        self.setLayout(layout)
        logging.debug("EnhancedDragDropWidget UI setup completed")
    
    def update_language(self):
        """Update UI text based on selected language"""
        logging.info("Updating EnhancedDragDropWidget language")
        self.upload_text.setText(self.parent_app.lang["uploadSection"]["dragDropInstruction"])
        self.supported_label.setText(self.parent_app.lang["uploadSection"]["supportedFormatsHint"])
        self.upload_btn.setText(self.parent_app.lang["uploadSection"]["setAsWallpaperButton"])
        self.reset_btn.setText(self.parent_app.lang["settings"]["resetButton"])


    def _create_file_path(self):
        """Add file to specified destination and show set as wallpaper option"""
        if not self.dropped_file_path:
            return
        
        source_path = Path(self.dropped_file_path)
        
        # Determine destination folder
        dest_folder = SAVES_DIR
        
        # Copy file with duplicate handling
        dest_path = SAVES_DIR / source_path.name
        counter = 1
        original_stem = source_path.stem
        while dest_path.exists():
            dest_path = dest_folder / f"{original_stem}_{counter}{source_path.suffix}"
            counter += 1
        
        shutil.copy2(source_path, dest_path)
        
        # Store the destination path for potential wallpaper setting
        self.destination_path = str(dest_path)


    def dragEnterEvent(self, event):
        """Check for valid file types when file enters the drop area"""
        logging.debug("Drag enter event in EnhancedDragDropWidget")
        
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                
                # Check if it's a valid wallpaper file type
                if self.is_valid_wallpaper_file(file_path):
                    event.acceptProposedAction()
                    
                    # Visual feedback that this area accepts drops
                    self.setStyleSheet(
                        "background-color: rgba(255, 255, 255, 0.1); border: 0px dashed #4CAF50; border-radius: 5px;")
                    logging.debug(f"Drag event accepted - valid file type: {file_path}")
                else:
                    event.ignore()
                    logging.debug(f"Drag event ignored - invalid file type: {file_path}")
            else:
                event.ignore()
                logging.debug("Drag event ignored - no valid file URLs")
        else:
            event.ignore()
            logging.debug("Drag event ignored - no URLs")

    def dragLeaveEvent(self, event):
        """Handle drag leave event"""
        logging.debug("Drag leave event in EnhancedDragDropWidget")
        # Remove visual feedback
        self.setStyleSheet("")
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        logging.debug("Drop event in EnhancedDragDropWidget")
        # Remove visual feedback
        self.setStyleSheet("")
        
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            logging.info(f"File dropped in drag & drop area: {file_path}")
            if self.is_valid_wallpaper_file(file_path):
                self.dropped_file_path = file_path
                filename = os.path.basename(file_path)
                file_type = "Video" if self.is_video_file(file_path) else "Image"
                
                # Update UI to show file is ready
                self.upload_text.setText(f" {file_type} Ready!\n\n{filename}")
                self.supported_label.hide()
                
                # Show buttons: Add to Collection, Add to Favorites, Reset
                self.toggle_buttons_visibility(True)
                self.uploadIcon.hide()
                
                # Show collection/favorites buttons, hide set as wallpaper initially
                self.upload_btn.show()  # Hidden until user selects destination
                self.reset_btn.show()   # Always show reset when file is selected
                
                logging.info(f"Valid {file_type.lower()} file selected: {filename}")
                
            else:
                self.upload_text.setText("Invalid file type!\nSupported: Images, Videos")
                self.upload_btn.setEnabled(False)
                logging.warning(f"Invalid file type dropped: {file_path}")
        
        event.acceptProposedAction()

    def set_as_wallpaper(self):
        """Set the added file as wallpaper"""
        logging.info("Set as Wallpaper button clicked")
        if hasattr(self, 'dropped_file_path') and self.dropped_file_path:
            try:
                self._create_file_path()
                # Store current wallpaper before setting new one
                if not hasattr(self, 'previous_wallpaper') or not self.previous_wallpaper:
                    self.previous_wallpaper = self.get_current_wallpaper()
                    logging.info(f"Stored original wallpaper: {self.previous_wallpaper}")
                
                # Update URL input field
                if hasattr(self.parent_app, 'ui') and hasattr(self.parent_app.ui, 'urlInput'):
                    self.parent_app.ui.urlInput.setText(self.destination_path)
                
                # Apply the wallpaper
                if self.is_video_file(self.destination_path):
                    logging.info(f"Setting video wallpaper: {self.destination_path}")
                    self.parent_app.controller.start_video(self.destination_path)
                else:
                    logging.info(f"Setting image wallpaper: {self.destination_path}")
                    self.parent_app.controller.start_image(self.destination_path)
                
                # Show success message
                self.upload_text.setText("Wallpaper set successfully!")
                
                # Update status
                if hasattr(self.parent_app, '_set_status'):
                    self.parent_app._set_status(f"Wallpaper set: {os.path.basename(self.destination_path)}")
                
                # Store in config
                self.parent_app.config.set_last_video(self.destination_path)
                logging.info(f"Wallpaper set successfully and saved to config: {os.path.basename(self.destination_path)}")
                
                # Hide buttons after successful set with delay
                QTimer.singleShot(1000, self.reset_selection)
                
            except Exception as e:
                logging.error(f"Failed to set wallpaper: {e}", exc_info=True)
                self.upload_text.setText("Failed to set wallpaper!")
                QMessageBox.critical(self, "Error", f"Failed to set wallpaper: {str(e)}")
        else:
            logging.warning("No destination path available for setting wallpaper")
            QMessageBox.warning(self, "Error", "No file available to set as wallpaper.")
    
    def reset_selection(self):
        """Reset to original selection state"""
        logging.info("Reset selection triggered")
        self.dropped_file_path = None
        if hasattr(self, 'destination_path'):
            delattr(self, 'destination_path')
        self.upload_text.setText(self.parent_app.lang["uploadSection"]["dragDropInstruction"])
        self.supported_label.show()
        self.toggle_buttons_visibility(False)
        self.reset_btn.hide()  # Hide reset when no file selected
        logging.debug("Drag drop widget reset to initial state")
    
    def is_video_file(self, file_path):
        """Check if file is a video"""
        video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
        return file_path.lower().endswith(video_extensions)

    def restore_original_wallpaper(self):
        """Restore the original wallpaper that was set before any changes"""
        logging.info("Restoring original wallpaper")
        if hasattr(self, 'previous_wallpaper') and self.previous_wallpaper:
            try:
                logging.info(f"Attempting to restore original wallpaper: {self.previous_wallpaper}")
                
                if os.path.exists(self.previous_wallpaper):
                    if self.is_video_file(self.previous_wallpaper):
                        logging.info("Restoring original video wallpaper")
                        self.parent_app.controller.start_video(self.previous_wallpaper)
                    else:
                        logging.info("Restoring original image wallpaper")
                        self.parent_app.controller.start_image(self.previous_wallpaper)
                    
                    if hasattr(self.parent_app, '_set_status'):
                        self.parent_app._set_status("Original wallpaper restored")
                    
                    # Update URL input
                    if hasattr(self.parent_app.ui, 'urlInput'):
                        self.parent_app.ui.urlInput.setText(self.previous_wallpaper)
                    
                    logging.info("Original wallpaper restored successfully")
                else:
                    logging.warning(f"Original wallpaper file not found: {self.previous_wallpaper}")
                    self.parent_app._set_status("Original wallpaper file not found")
                    
            except Exception as e:
                logging.error(f"Failed to restore original wallpaper: {e}", exc_info=True)
                self.parent_app._set_status("Failed to restore original wallpaper")
    
    def get_current_wallpaper(self):
        """Get the current system wallpaper path"""
        try:
            from utils.system_utils import get_current_desktop_wallpaper
            wallpaper = get_current_desktop_wallpaper()
            logging.info(f"Retrieved current wallpaper: {wallpaper}")
            return wallpaper
        except Exception as e:
            logging.error(f"Could not get current wallpaper: {e}", exc_info=True)
        return None
    
    def is_valid_wallpaper_file(self, file_path):
        """Check if file is a valid wallpaper type with comprehensive validation"""
        valid_extensions = (
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff',
            # Videos  
            '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'
        )

        if not file_path or not isinstance(file_path, str):
            logging.debug(f"Invalid file path: {file_path}")
            return False
        
        # Check extension
        file_ext = os.path.splitext(file_path)[1].lower()
        is_valid = file_ext in valid_extensions
        
        logging.debug(f"File validation for {file_path}: {is_valid} (extension: {file_ext})")
        return is_valid
    
