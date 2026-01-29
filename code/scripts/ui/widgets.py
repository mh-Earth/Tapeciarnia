from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QSizePolicy, QMessageBox
)
from PySide6.QtGui import  QPixmap,QCursor
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon


from utils.path_utils import SAVES_DIR
from utils.singletons import get_config
import logging
from pathlib import Path
import os
import shutil

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
        self.config = get_config()
    
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
        # make the cursor a pointing hand
        self.parent_app.ui.uploadArea.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        
        # Upload text
        self.upload_text = QLabel(self.parent_app.language_controller.get("uploadSection.dragDropInstruction"))
        self.upload_text.setAlignment(Qt.AlignCenter)
        self.upload_text.setAcceptDrops(True)
        self.upload_text.setSizePolicy(self.upload_text.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
        self.upload_text.setProperty('class',"MainUILable")
        
        # Supported formats label
        self.supported_label = QLabel(self.parent_app.language_controller.get("uploadSection.supportedFormatsHint"))
        self.supported_label.setAlignment(Qt.AlignCenter)
        self.supported_label.setSizePolicy(self.supported_label.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
        self.supported_label.setProperty('class',"MainUILable")
        
        # Action buttons (initially hidden)
        self.buttons_widget = QWidget()
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(20, 10, 20, 10)
        buttons_layout.setSpacing(15)
        
        # Set as Wallpaper button (appears after selecting collection/favorites)
        self.upload_btn = QPushButton(self.parent_app.language_controller.get("uploadSection.setAsWallpaperButton"))
        self.upload_btn.clicked.connect(self.set_as_wallpaper)
        self.upload_btn.setProperty("class", "primary")
        self.upload_btn.setMinimumHeight(35)
        self.upload_btn.setVisible(False)  # Hidden initially
        self.upload_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        
        # Reset button (always visible when file is selected)
        self.reset_btn = QPushButton(self.parent_app.language_controller.get("settings.resetButton"))
        self.reset_btn.clicked.connect(self.reset_selection)
        self.reset_btn.setProperty("class", "ghost")
        self.reset_btn.setMinimumHeight(35)
        self.reset_btn.setVisible(False)  # Hidden initially
        self.reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


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
        self.upload_text.setText(self.parent_app.language_controller.get("uploadSection.dragDropInstruction"))
        self.supported_label.setText(self.parent_app.language_controller.get("uploadSection.supportedFormatsHint"))
        self.upload_btn.setText(self.parent_app.language_controller.get("uploadSection.setAsWallpaperButton"))
        self.reset_btn.setText(self.parent_app.language_controller.get("settings.resetButton"))


    def _create_file_path(self):
        """Add a copy of the dropped file to specified destination and show set as wallpaper option"""
        if not self.dropped_file_path:
            return
        
        source_path = Path(self.dropped_file_path)
        
        # # Determine destination folder
        # dest_folder = SAVES_DIR
        
        # # Copy file with duplicate handling
        # dest_path = SAVES_DIR / source_path.name
        # counter = 1
        # original_stem = source_path.stem
        # while dest_path.exists():
        #     dest_path = dest_folder / f"{original_stem}_{counter}{source_path.suffix}"
        #     counter += 1
        
        # shutil.copy2(source_path, dest_path)
        
        # Store the destination path for potential wallpaper setting
        self.destination_path = str(source_path)


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
                    self.parent_app.ui.uploadArea.setStyleSheet(
                        "QFrame#uploadArea{background-color: rgba(255, 255, 255, 0.1);}"
                        )
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
        self.parent_app.ui.uploadArea.setStyleSheet("")
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        logging.debug("Drop event in EnhancedDragDropWidget")
        # Remove visual feedback
        self.parent_app.ui.uploadArea.setStyleSheet("")
        
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
                
                #  make the cursor a normal arrow 
                self.parent_app.ui.uploadArea.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                
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
                
                # stop scheduler if running
                if self.parent_app.scheduler.is_active():
                    self.parent_app._stop_scheduler()
                

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
                QTimer.singleShot(0, self.reset_selection)
                # make the cursor a pointing hand for the drop area
                self.parent_app.ui.uploadArea.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                
            except Exception as e:
                # make the cursor a normal arrow for the drop area
                self.parent_app.ui.uploadArea.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
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
        self.upload_text.setText(self.parent_app.language_controller.get("uploadSection.dragDropInstruction"))
        self.supported_label.show()
        self.toggle_buttons_visibility(False)
        self.reset_btn.hide()  # Hide reset when no file selected
        # make the cursor a pointing hand for the drop area
        self.parent_app.ui.uploadArea.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        logging.debug("Drag drop widget reset to initial state")
    
    def is_video_file(self, file_path):
        """Check if file is a video"""
        video_extensions = tuple(self.config.get_valid_video_extensions())
        return file_path.lower().endswith(video_extensions)

    def is_valid_wallpaper_file(self, file_path):
        """Check if file is a valid wallpaper type with comprehensive validation"""
        valid_extensions = self.config.get_all_valid_extensions()

        if not file_path or not isinstance(file_path, str):
            logging.debug(f"Invalid file path: {file_path}")
            return False
        
        # Check extension
        file_ext = os.path.splitext(file_path)[1].lower()
        is_valid = file_ext in valid_extensions
        
        logging.debug(f"File validation for {file_path}: {is_valid} (extension: {file_ext})")
        return is_valid
    




class ButtonCollection:
    """
    A reusable collection of ready-made buttons for your PySide6 application.
    This class provides factory methods that return styled QPushButtons.
    """

    def __init__(self,language_data:dict=None):
        self.lang = language_data  # Placeholder for language data if needed
        # Default styles you can customize
        self.default_style = """
            QPushButton {
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #555;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """

    # -----------------------------------------------------
    # GENERIC BUTTON CREATION
    # -----------------------------------------------------
    def create(self, text="", icon_path=None, style=None):
        match text:
            case "OK":
                text = self.lang["navigation"]["ok"] if self.lang else "Ok"
            case "Cancel":
                text = self.lang["navigation"]["cancel"] if self.lang else "Cancel"
            case "Yes":
                text = self.lang["navigation"]["yes"] if self.lang else "Yes"
            case "No":
                text = self.lang["navigation"]["no"] if self.lang else "No"
            case "Apply":
                text = self.lang["navigation"]["apply_button"] if self.lang else "Apply"
            case "Save":
                text = self.lang["navigation"]["save_button"] if self.lang else "Save"
            case "Delete":
                text = self.lang["navigation"]["delete_button"] if self.lang else "Delete"
            case "Browse...":
                text = self.lang["navigation"]["browse_button"] if self.lang else "Browse..."
            case "Next":
                text = self.lang["navigation"]["next_button"] if self.lang else "Next"
            case "Back":
                text = self.lang["navigation"]["back_button"] if self.lang else "Back"
            case "Refresh":
                text = self.lang["navigation"]["refresh_button"] if self.lang else "Refresh"
            case _:
                pass

        btn = QPushButton(text)

        if icon_path:
            btn.setIcon(QIcon(icon_path))

        btn.setStyleSheet(style or self.default_style)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return btn
    
    def _update_language(self,language_data:dict):
        self.lang = language_data

    # -----------------------------------------------------
    # PREDEFINED COMMON BUTTONS
    # -----------------------------------------------------
    def ok_button(self):
        return self.create("OK")

    def cancel_button(self):
        return self.create("Cancel")

    def yes_button(self):
        return self.create("Yes")

    def no_button(self):
        return self.create("No")

    def apply_button(self):
        return self.create("Apply")

    def save_button(self):
        return self.create("Save")

    def delete_button(self):
        return self.create("Delete")

    def browse_button(self):
        return self.create("Browse...")

    def next_button(self):
        return self.create("Next")

    def back_button(self):
        return self.create("Back")

    def refresh_button(self):
        return self.create("Refresh")

    # -----------------------------------------------------
    # ICON BUTTONS (optional)
    # -----------------------------------------------------
    def icon_ok(self, icon_path):
        return self.create("", icon_path)

    def icon_cancel(self, icon_path):
        return self.create("", icon_path)

    def icon_custom(self, icon_path):
        return self.create("", icon_path)

from PySide6.QtWidgets import QMessageBox


class CustomMessageBox:
    """
    Working custom MessageBox that correctly shows styled buttons.
    """

    def __init__(self, button_maker: ButtonCollection):
        self.button_maker = button_maker

    def _add_custom_button(self, box, button, role):
        """
        Converts a QPushButton into a QMessageBox-owned button
        so it can be shown properly.
        """
        qt_btn = box.addButton(button.text(), role)
        qt_btn.setStyleSheet(button.styleSheet())
        qt_btn.setCursor(button.cursor())

        # Copy icon if exists
        if not button.icon().isNull():
            qt_btn.setIcon(button.icon())

        return qt_btn

    def update_language(self,language_data:dict):
        self.button_maker._update_language(language_data)

    def _create_box(self, parent, icon, title, message,
                    show_ok=False, show_yes=False, show_no=False, show_cancel=False):

        box = QMessageBox(parent)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(message)

        # Custom buttons (now visible!)
        if show_ok:
            self._add_custom_button(box, self.button_maker.ok_button(), QMessageBox.AcceptRole)

        if show_yes:
            self._add_custom_button(box, self.button_maker.yes_button(), QMessageBox.YesRole)

        if show_no:
            self._add_custom_button(box, self.button_maker.no_button(), QMessageBox.NoRole)

        if show_cancel:
            self._add_custom_button(box, self.button_maker.cancel_button(), QMessageBox.RejectRole)

        return box

    def information(self, parent, title, message):
        return self._create_box(
            parent, QMessageBox.Information, title, message, show_ok=True
        ).exec()

    def warning(self, parent, title, message):
        return self._create_box(
            parent, QMessageBox.Warning, title, message, show_ok=True
        ).exec()

    def critical(self, parent, title, message):
        return self._create_box(
            parent, QMessageBox.Critical, title, message, show_ok=True
        ).exec()

    def question(self, parent, title, message):
        return self._create_box(
            parent, QMessageBox.Question, title, message,
            show_yes=True, show_no=True, show_cancel=True
        ).exec()
