import os
import sys
import random
import logging
import logging
from pathlib import Path
import webbrowser
import json

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, 
    QSystemTrayIcon, QMenu, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStyle, QSizePolicy, QDialog,QSpacerItem
)
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtCore import QTimer, Qt, QEvent, QSize,Signal, QThread
from .widgets import EnhancedDragDropWidget

current_dir = os.path.dirname(__file__)
ui_path = os.path.join(current_dir, 'mainUI.py')
sys.path.append(os.path.dirname(current_dir))

logger = logging.getLogger(__name__)

try:
    from ui.mainUI import Ui_MainWindow
    logging.info("Successfully imported Ui_MainWindow from ui.mainUI")
except ImportError as e:
    logging.error(f"UI import error: {e}")
    try:
        sys.path.append(current_dir)
        from mainUI import Ui_MainWindow
        logging.info("Successfully imported Ui_MainWindow from local directory")
    except ImportError:
        logging.critical("Cannot import Ui_MainWindow. Make sure mainUI.py exists in the ui folder.")
        raise ImportError("Cannot import Ui_MainWindow. Make sure mainUI.py exists in the ui folder.")

# Import core modules
from core.wallpaper_controller import WallpaperController
from core.download_manager import DirectDownloadThread,ImageDownloadThread
from core.scheduler import WallpaperScheduler
from  core.language_controller import LanguageController
from core.login_handler import LoginWorker
# Import utilities
from utils.path_utils import COLLECTION_DIR,SAVES_DIR, FAVS_DIR, get_folder_for_range, get_folder_for_source, open_folder_in_explorer
from utils.system_utils import get_current_desktop_wallpaper, is_connected_to_internet, get_primary_screen_dimensions, fetch_shuffled_wallpaper, resource_path
from utils.validators import validate_url_or_path, get_media_type,validate_tapeciarnia_url,is_tapeciarnia_redirect_url
from utils.file_utils import cleanup_temp_marker
from utils.pathResolver import fast_resolve_tapeciarnia_redirect
from utils.singletons import get_config
# Import models
from models.config import Config

# Import UI components
from .dialogs import ShutdownProgressDialog



class TapeciarniaApp(QMainWindow):
    def __init__(self):
        logging.info("Initializing TapeciarniaApp")
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.x , self.y = get_primary_screen_dimensions()
        self.is_dowloading = False
        # Initialize controllers
        logging.debug("Initializing controllers")
        self.controller = WallpaperController()
        self.scheduler = WallpaperScheduler()
        self.language_controller = LanguageController()
        self.scheduler.set_change_callback(self._apply_wallpaper_from_path)
        self.config = get_config()

        self._set_lang()
        # connect to the language controller signals
        self.language_controller.language_changed.connect(self._update_lang)
        self.ui.uploadArea.mousePressEvent = self.upload_area_mousePressEvent

        # remove focuse from email input textEdit
        self.ui.emailInput.clearFocus()
        self.ui.card.setFocus()
        # Enhanced wallpaper state
        self.current_wallpaper_type = None
        self.auto_pause_process = None
        self.last_wallpaper_path = None
        self.current_shuffle_mode = None
        self.isLogin:bool = False # temporary


        # Enhanced drag & drop
        self.drag_drop_widget = EnhancedDragDropWidget(self)

        # State
        self.current_range = "all"
        self.previous_wallpaper = get_current_desktop_wallpaper()
        self.is_minimized_to_tray = False

        # Setup
        self._setup_ui()
        self._setup_tray()
        self._load_settings()
        self._setLogInState()
        

        logging.info("TapeciarniaApp initialization completed successfully")

    def _setLogInState(self):
        if self.isLogin:
            self.ui.emailInput.hide()
            self.ui.passwordInput.hide()
            self.ui.logInBnt.setText("Log out")
        else:
            self.ui.emailInput.show()
            self.ui.passwordInput.show()
            self.ui.logInBnt.setText("Log in")

        self.update()


    def upload_area_mousePressEvent(self, event):
            """
            This is the overridden method that captures the click event.
            """
            # Call the base class implementation first (important)
            super().mousePressEvent(event)
            logging.debug("Lanuching file browser...")
            
            # Check if the left mouse button was pressed
            if event.button() == Qt.MouseButton.LeftButton:

                path, _ = QFileDialog.getOpenFileName(
                    self, "Select video or image", str(Path.home()),
                    "Media (*.mp4 *.mkv *.webm *.avi *.mov *.jpg *.jpeg *.png)"
                )
                
                if path:
                    logging.info(f"File selected via browse: {path}")
                    
                    # Show the same interface as drag & drop
                    self._handle_browsed_file(path)
                else:
                    logging.debug("Browse dialog cancelled")


    def _update_lang(self, lang:dict):
        """Update UI language based on selected language"""
        self.lang = lang
        # 
        self.update_ui_language()
        self.drag_drop_widget.update_language()

    def _set_lang(self):
        logging.info("Eumarating all language options into combo box")
        self.language_controller.enumerate_languages(self.ui.langCombo)
        # Set initial language
        self.lang = self.language_controller.setup_initial_language(self.ui.langCombo)
        self.update_ui_language()

    def _make_icon(self,icon_name:QIcon,className:str ="primary") -> QIcon:
        if className == "primary":
            icon = QIcon()
            icon.addFile(f":/icons/icons/{icon_name}_blue.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
            return icon
        elif className == "ghost":
            icon = QIcon()
            icon.addFile(f":/icons/icons/{icon_name}.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
            return icon
        else:
            icon = QIcon()
            icon.addFile(f":/icons/icons/{icon_name}.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
            return icon
 


    def _set_status(self, message: str):
        """Update status label and ensure it's visible"""
        logging.debug(f"Setting status: {message}")
        if hasattr(self.ui, "statusLabel"):
            self.ui.statusLabel.setText(message)
            self.ui.statusLabel.setVisible(True)
        # Also ensure the parent frame is visible
        if hasattr(self.ui, "bottomFrame"):
            self.ui.bottomFrame.setVisible(True)

    def on_shuffle_animated(self):

        """Shuffle through animated wallpapers - try online first, fallback to local"""
        logging.info("Shuffle animated triggered - trying online first")
        self.current_shuffle_type = 'animated'
        self._update_shuffle_button_states('animated')
        # disable another button 
        self.ui.randomButton.setDisabled(True)
        self._set_status("Fetching online animated wallpaper...")
        
        # Update button states
        
        # Check internet connection first
        if not is_connected_to_internet():
            logging.warning("No internet connection, using local shuffle")
            self._set_status("No internet - using local animated wallpapers")
            self._fallback_to_local_shuffle(True)
            return
        
        try:
            # Try to fetch online wallpaper
            online_url = fetch_shuffled_wallpaper(self.x,self.y,True,self.language_controller.get_current_language())
            logging.debug(f"Online URl : {online_url}")
            if online_url:
                # Download and set online wallpaper
                self.download_and_set_online_wallpaper(online_url, is_animated=True)
            else:
                # Online fetch failed, use local
                self._fallback_to_local_shuffle(True)
                
        except Exception as e:
            logging.error(f"Online shuffle animated failed: {e}")
            self._fallback_to_local_shuffle(True)



    def on_shuffle_wallpaper(self):

        self.is_dowloading = True
        """Shuffle through static wallpapers - try online first, fallback to local"""
        logging.info("Shuffle wallpaper triggered - trying online first")
        self.current_shuffle_type = 'wallpaper'
        self._update_shuffle_button_states('wallpaper')
        self.ui.randomAnimButton.setDisabled(True)
        self._set_status("Fetching online wallpaper...")
        
        # Update button states
        
        # Check internet connection first
        if not is_connected_to_internet():
            logging.warning("No internet connection, using local shuffle")
            self._set_status("No internet - using local wallpapers")
            self._fallback_to_local_shuffle(False)
            return
        
        try:
            # Try to fetch online wallpaper
            online_url = fetch_shuffled_wallpaper(self.x,self.y,False,self.language_controller.get_current_language())
            logging.debug(f"Online URl : {online_url}")
            
            if online_url:
                # Download and set online wallpaper
                self.download_and_set_online_wallpaper(online_url, is_animated=False)
            else:
                # Online fetch failed, use local
                self._fallback_to_local_shuffle(False)
                
        except Exception as e:
            logging.error(f"Online shuffle wallpaper failed: {e}")
            self._fallback_to_local_shuffle(False)


    def _perform_reset(self):
        """Reset to default wallpaper WITHOUT confirmation but WITH success message"""
        logging.info("Performing reset without confirmation")
        self.controller.stop()
        self.scheduler.stop()
        self.set_buttons(True)
        # Reset enhanced state
        self.current_wallpaper_type = None
        self.last_wallpaper_path = None
        self.current_shuffle_mode = None
        
        # Reset shuffle button states
        if hasattr(self.ui, 'randomButton'):
            self.ui.randomButton.setChecked(False)
            self.ui.randomButton.setProperty("class", "ghost")
            self.ui.randomButton.setIcon(self._make_icon(self.ui.randomButton.property("icon_name"),className="ghost"))
            self.ui.randomButton.style().unpolish(self.ui.randomButton)
            self.ui.randomButton.style().polish(self.ui.randomButton)
        
        if hasattr(self.ui, 'randomAnimButton'):
            self.ui.randomAnimButton.setChecked(False)
            self.ui.randomAnimButton.setProperty("class", "ghost")
            self.ui.randomAnimButton.setIcon(self._make_icon(self.ui.randomAnimButton.property("icon_name"),className="ghost"))
            self.ui.randomAnimButton.style().unpolish(self.ui.randomAnimButton)
            self.ui.randomAnimButton.style().polish(self.ui.randomAnimButton)
        
        # Use the enhanced drag drop widget to restore original wallpaper
        if hasattr(self, 'drag_drop_widget'):
            self.drag_drop_widget.restore_original_wallpaper()
        elif self.previous_wallpaper:
            self.controller.start_image(self.previous_wallpaper)
            self._set_status("Restored previous wallpaper")
        else:
            self._set_status("Reset complete (no previous wallpaper)")
        
        # Clear URL input
        if hasattr(self.ui, 'urlInput'):
            self.ui.urlInput.clear()
        
        self._set_status("Reset completed")
        logging.info("Reset completed successfully")
        
        # Show success confirmation
        QTimer.singleShot(500, self._show_reset_success_message)

    def _show_reset_success_message(self):
        """Show success confirmation dialog after reset"""
        logging.info("Showing reset success confirmation")
        
        # Create a custom dialog for better UX
        success_dialog = QMessageBox(self)
        success_dialog.setWindowTitle(self.lang["dialog"]["reset_success_title"])
        success_dialog.setText(self.lang["dialog"]["reset_success_message"])
        success_dialog.setIcon(QMessageBox.Icon.Information)
        success_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Show the dialog
        success_dialog.exec()
        logging.info("Reset success confirmation shown")

    def cleanup(self):
        """Enhanced cleanup on app close"""
        logging.info("Performing application cleanup")
        self.controller.stop()
        self.stop_auto_pause_process()
        logging.info("Application cleanup completed")

    # Rest of your existing methods remain the same...
    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized() and not self.is_minimized_to_tray:
                logging.debug("Window minimize event detected, hiding to tray")
                event.ignore()
                self.hide_to_tray()
        super().changeEvent(event)

    def closeEvent(self, event):
        """
        Handle window close event - Show confirmation dialog before closing
        """
        logging.info("Close event triggered")
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to exit Tapeciarnia?\n\nThis will stop all wallpapers and background processes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logging.info("User confirmed exit")
            # Show shutdown progress dialog
            self._show_shutdown_progress(event)
        else:
            logging.info("User cancelled exit")
            event.ignore()

    def _show_shutdown_progress(self, event):
        """Show shutdown progress and perform cleanup"""
        logging.info("Starting shutdown process with enhanced progress dialog")
        
        # Create and show shutdown progress dialog
        self.shutdown_dialog = ShutdownProgressDialog(self)
        self.shutdown_dialog.show()
        
        # Start the actual shutdown process after dialog is shown
        QTimer.singleShot(200, lambda: self._perform_shutdown(event))

    def _perform_shutdown(self, event):
        """Perform shutdown with coordinated progress updates"""
        try:
            logging.info("Performing coordinated shutdown sequence")
            
            # Step 1: Stop wallpaper processes (25%)
            self.shutdown_dialog.update_progress(25, "Stopping wallpaper processes...")
            self.controller.stop()
            QApplication.processEvents()
            
            # Step 2: Stop scheduler (50%)
            self.shutdown_dialog.update_progress(50, "Stopping scheduler...")
            self.scheduler.stop()
            QApplication.processEvents()
            
            # Step 3: Cleanup resources (75%)
            self.shutdown_dialog.update_progress(75, "Cleaning up resources...")
            try:
                if hasattr(self, 'stop_auto_pause_process'):
                    self.stop_auto_pause_process()
            except Exception as e:
                logging.warning(f"Error stopping auto-pause process: {e}")
            QApplication.processEvents()
            
            # Step 4: Save settings (90%)
            self.shutdown_dialog.update_progress(90, "Saving settings...")
            # Add any final settings save operations here
            QApplication.processEvents()
            
            # Step 5: Complete (100%)
            self.shutdown_dialog.update_progress(100, "Shutdown complete!")
            QApplication.processEvents()
            
            # Wait a moment to show completion, then finalize
            QTimer.singleShot(800, lambda: self._finalize_shutdown(event))
            
        except Exception as e:
            logging.error(f"Error during shutdown: {e}", exc_info=True)
            # Even if there's an error, try to finalize
            self._finalize_shutdown(event)

    def _finalize_shutdown(self, event):
        """Finalize the shutdown process - FIXED for deleted event"""
        try:
            # Hide tray icon
            if hasattr(self, 'tray'):
                self.tray.hide()
            
            # Close shutdown dialog
            if hasattr(self, 'shutdown_dialog'):
                self.shutdown_dialog.close()
            
            # Don't try to use event if it's already deleted
            try:
                if event and hasattr(event, 'accept'):
                    event.accept()
            except RuntimeError:
                logging.debug("Close event already deleted, continuing shutdown")
            
            # Quit application
            QApplication.quit()
            
            logging.info("Application quit initiated successfully")
            
        except Exception as e:
            logging.error(f"Error finalizing shutdown: {e}", exc_info=True)
            # Force quit if graceful shutdown fails
            QApplication.quit()

    def _show_shutdown_progress_from_tray(self):
        """Show shutdown progress when exiting from tray"""
        logging.info("Starting shutdown process from tray with progress dialog")
        
        # Create and show shutdown progress dialog
        self.shutdown_dialog = ShutdownProgressDialog(self)
        self.shutdown_dialog.show()
        
        # Start shutdown process
        QTimer.singleShot(200, self._perform_shutdown_from_tray)

    def _perform_shutdown_from_tray(self):
        """Perform shutdown from tray with progress updates"""
        try:
            logging.info("Performing shutdown sequence from tray")
            
            # Step 1: Stop wallpaper processes (25%)
            self.shutdown_dialog.update_progress(25, "Stopping wallpaper processes...")
            self.controller.stop()
            QApplication.processEvents()
            
            # Step 2: Stop scheduler (50%)
            self.shutdown_dialog.update_progress(50, "Stopping scheduler...")
            self.scheduler.stop()
            QApplication.processEvents()
            
            # Step 3: Cleanup (75%)
            self.shutdown_dialog.update_progress(75, "Cleaning up resources...")
            try:
                if hasattr(self, 'stop_auto_pause_process'):
                    self.stop_auto_pause_process()
            except Exception as e:
                logging.warning(f"Error stopping auto-pause process: {e}")
            QApplication.processEvents()
            
            # Step 4: Save settings (90%)
            self.shutdown_dialog.update_progress(90, "Saving settings...")
            QApplication.processEvents()
            
            # Step 5: Complete (100%)
            self.shutdown_dialog.update_progress(100, "Shutdown complete!")
            QApplication.processEvents()
            
            # Wait a moment to show completion
            QTimer.singleShot(800, self._finalize_shutdown_from_tray)
            
        except Exception as e:
            logging.error(f"Error during tray shutdown: {e}", exc_info=True)
            self._finalize_shutdown_from_tray()

    def _finalize_shutdown_from_tray(self):
        """Finalize shutdown from tray"""
        try:
            # Hide tray icon
            if hasattr(self, 'tray'):
                self.tray.hide()
            
            # Close shutdown dialog
            if hasattr(self, 'shutdown_dialog'):
                self.shutdown_dialog.close()
            
            # Quit application
            QApplication.quit()
            logging.info("Application quit from tray completed successfully")
            
        except Exception as e:
            logging.error(f"Error finalizing tray shutdown: {e}", exc_info=True)
            QApplication.quit()

    def stop_auto_pause_process(self):
        """Stop any auto-pause background processes"""
        logging.info("Stopping auto-pause processes")
        try:
            if hasattr(self, 'auto_pause_process') and self.auto_pause_process:
                try:
                    self.auto_pause_process.terminate()
                    self.auto_pause_process.wait(2000)  # Wait up to 2 seconds
                    logging.debug("Auto-pause process terminated successfully")
                except Exception as e:
                    logging.warning(f"Could not terminate auto-pause process gracefully: {e}")
                    try:
                        self.auto_pause_process.kill()
                        logging.debug("Auto-pause process killed")
                    except Exception as kill_error:
                        logging.error(f"Could not kill auto-pause process: {kill_error}")
                finally:
                    self.auto_pause_process = None
        except Exception as e:
            logging.warning(f"Error stopping auto-pause process: {e}")

    def hide_to_tray(self):
        logging.info("Hiding window to system tray")
        self.hide()
        self.is_minimized_to_tray = True
        if hasattr(self, 'tray'):
            self.tray.showMessage(
                self.lang["dialog"]["icon_tray_title"],
                self.lang["dialog"]["icon_tray_message"],
                QSystemTrayIcon.Information,
                3000
            )
        logging.debug("Window hidden to tray")

    def show_from_tray(self):
        logging.info("Showing window from system tray")
        self.show()
        self.raise_()
        self.activateWindow()
        if self.isMinimized():
            self.showNormal()
        self.is_minimized_to_tray = False
        logging.debug("Window restored from tray")


    def _setup_ui(self):
        """Setup UI connections and initial state"""
        logging.debug("Setting up UI")
        self.setAcceptDrops(True)
        
        # Replace the upload area with enhanced drag & drop - FIXED VERSION
        if hasattr(self.ui, 'uploadArea'):
            logging.debug("Replacing upload area with enhanced drag drop widget")
            # Clear existing upload area safely without setParent
            existing_layout = self.ui.uploadArea.layout()
            if existing_layout:
                # Use deleteLater() instead of setParent(None) for thread safety
                for i in reversed(range(existing_layout.count())):
                    layout_item = existing_layout.itemAt(i)
                    if layout_item:
                        widget = layout_item.widget()
                        if widget:
                            widget.deleteLater()  # Thread-safe deletion
                        else:
                            # If it's a layout item without widget, remove it
                            existing_layout.removeItem(layout_item)
            
            # Create new layout if needed
            if not self.ui.uploadArea.layout():
                existing_layout = QVBoxLayout(self.ui.uploadArea)
            
            # Add our enhanced widget
            existing_layout.addWidget(self.drag_drop_widget)
            logging.debug("Enhanced drag drop widget added to upload area")
        
        
        # Connect signals
        self._bind_ui_controls()
        
        # Initial UI state
        self._update_scheduler_ui_state()
        logging.debug("UI setup completed")

    def on_source_double_clicked(self, source_type):
        """Handle double-click on source buttons to open corresponding folder"""
        logging.info(f"Double-click detected on source: {source_type}")
        folder_path = get_folder_for_source(source_type)
        
        if folder_path.exists():
            success = open_folder_in_explorer(folder_path)
            if success:
                self._set_status(f"Opened {source_type} folder")
                logging.info(f"Successfully opened folder: {folder_path}")
            else:
                self._set_status(f"Failed to open {source_type} folder")
                logging.error(f"Failed to open folder: {folder_path}")
        else:
            logging.warning(f"Folder does not exist: {folder_path}")
            QMessageBox.warning(self, "Folder Not Found", 
                            f"The {source_type} folder does not exist:\n{folder_path}")

    def on_range_double_clicked(self, range_type):
        """Handle double-click on range buttons to open corresponding folder"""
        logging.info(f"Double-click detected on range: {range_type}")
        folder_path = get_folder_for_range(range_type)
        
        if folder_path.exists():
            success = open_folder_in_explorer(folder_path)
            if success:
                self._set_status(f"Opened {range_type} range folder")
                logging.info(f"Successfully opened folder: {folder_path}")
            else:
                self._set_status(f"Failed to open {range_type} folder")
                logging.error(f"Failed to open folder: {folder_path}")
        else:
            logging.warning(f"Folder does not exist: {folder_path}")
            QMessageBox.warning(self, "Folder Not Found", 
                            f"The {range_type} folder does not exist:\n{folder_path}")

    def _bind_ui_controls(self):
        """Bind UI controls to their handlers"""
        logging.debug("Binding UI controls")
        # Main controls
        if hasattr(self.ui, "loadUrlButton"):
            self.ui.loadUrlButton.clicked.connect(self.on_apply_clicked)
            logging.debug("Load URL button connected")
        
        if hasattr(self.ui, "urlInput"):
            self.ui.urlInput.returnPressed.connect(self.on_apply_clicked)
            logging.debug("URL input return pressed connected")

        # Start/Reset buttons (now in Range section)
        if hasattr(self.ui, "startButton"):
            self.ui.startButton.clicked.connect(self.on_start_clicked)
            logging.debug("Start button connected")
        
        if hasattr(self.ui, "resetButton"):
            # Use the version WITH confirmation
            self.ui.resetButton.clicked.connect(self._perform_reset_with_confirmation)
            logging.debug("Reset button connected with confirmation")

        # Browse button
        if hasattr(self.ui, "browseButton"):
            self.ui.browseButton.clicked.connect(self.on_browse_clicked)
            logging.debug("Browse button connected")

        if hasattr(self.ui, "randomAnimButton"):
            self.ui.randomAnimButton.clicked.connect(self.on_shuffle_animated)
            logging.debug("Shuffle animated button connected")
        
        if hasattr(self.ui, "randomButton"):
            self.ui.randomButton.clicked.connect(self.on_shuffle_wallpaper)
            logging.debug("Shuffle wallpaper button connected")

        # Source buttons - with double-click support
        if hasattr(self.ui, "super_wallpaper_btn"):
            self.ui.super_wallpaper_btn.clicked.connect(self.on_super_wallpaper)
            # self.ui.super_wallpaper_btn.mouseDoubleClickEvent = lambda e: self.on_source_double_clicked("super")
            # logging.debug("Super wallpaper button connected")
        
        if hasattr(self.ui, "fvrt_wallpapers_btn"):
            self.ui.fvrt_wallpapers_btn.clicked.connect(self.on_favorite_wallpapers)
            self.ui.fvrt_wallpapers_btn.mouseDoubleClickEvent = lambda e: self.on_source_double_clicked("favorites")
            logging.debug("Favorite wallpapers button connected")
        
        if hasattr(self.ui, "added_wallpaper_btn"):
            self.ui.added_wallpaper_btn.clicked.connect(self.on_added_wallpapers)
            self.ui.added_wallpaper_btn.mouseDoubleClickEvent = lambda e: self.on_source_double_clicked("added")
            logging.debug("Added wallpapers button connected")

        # Range buttons - with double-click support
        if hasattr(self.ui, "range_all_bnt"):
            self.ui.range_all_bnt.clicked.connect(lambda: self.on_range_changed("all"))
            self.ui.range_all_bnt.mouseDoubleClickEvent = lambda e: self.on_range_double_clicked("all")
            logging.debug("Range all button connected")
        
        if hasattr(self.ui, "range_wallpaper_bnt"):
            self.ui.range_wallpaper_bnt.clicked.connect(lambda: self.on_range_changed("wallpaper"))
            self.ui.range_wallpaper_bnt.mouseDoubleClickEvent = lambda e: self.on_range_double_clicked("wallpaper")
            logging.debug("Range wallpaper button connected")
        
        if hasattr(self.ui, "range_mp4_bnt"):
            self.ui.range_mp4_bnt.clicked.connect(lambda: self.on_range_changed("mp4"))
            self.ui.range_mp4_bnt.mouseDoubleClickEvent = lambda e: self.on_range_double_clicked("mp4")
            logging.debug("Range MP4 button connected")

        # Scheduler controls
        if hasattr(self.ui, "enabledCheck"):
            self.ui.enabledCheck.toggled.connect(self.on_scheduler_toggled)
            logging.debug("Scheduler enabled checkbox connected")
        
        if hasattr(self.ui, "interval_spinBox"):
            self.ui.interval_spinBox.valueChanged.connect(self._on_interval_changed)
            logging.debug("Interval spinbox connected")
        
        # connect language combo box
        if hasattr(self.ui, "langCombo"):
            logging.debug("Language combo box connected")
            self.ui.langCombo.currentTextChanged.connect(self.language_controller.on_language_changed)

        if hasattr(self.ui, "logInBnt"):
            self.ui.logInBnt.clicked.connect(self.on_login_clicked)
            logging.debug("Login button connected")

        logging.debug("All UI controls bound successfully")

    def _update_scheduler_ui_state(self):
        """Show/hide interval, range, and start button based on scheduler state"""
        enabled = hasattr(self.ui, "enabledCheck") and self.ui.enabledCheck.isChecked()
        logging.debug(f"Updating scheduler UI state: enabled={enabled}")
        
        # Show/hide interval and range controls
        if hasattr(self.ui, "source_n_interval_frame"):
            self.ui.source_n_interval_frame.setVisible(enabled)
        if hasattr(self.ui, "range_frame"):
            self.ui.range_frame.setVisible(enabled)
        # insert a spacer  between them

        if enabled:
            # Remove the spacer only if it exists
            if hasattr(self, "lowestVerticalSpacer") and self.lowestVerticalSpacer:
                self.ui.cardLayout.removeItem(self.lowestVerticalSpacer)
                self.lowestVerticalSpacer = None
                logging.debug("Removing the spacer")

        else:
            # Create and insert spacer only if not already created
            if not hasattr(self, "lowestVerticalSpacer") or self.lowestVerticalSpacer is None:
                self.lowestVerticalSpacer = QSpacerItem(
                    20, 40,
                    QSizePolicy.Policy.Minimum,
                    QSizePolicy.Policy.Expanding
                )
                index = self.ui.cardLayout.indexOf(self.ui.bottomFrame)
                self.ui.cardLayout.insertItem(index, self.lowestVerticalSpacer)
                logging.debug("Inserting spacer")

        # Show/hide start button
        if hasattr(self.ui, "startButton"):
            self.ui.startButton.setVisible(enabled)
            logging.debug(f"Start button visibility: {enabled}")
        
        logging.debug(f"Scheduler UI controls set to visible: {enabled}")

    # Main application methods
    def on_apply_clicked(self):
        self.ui.loadUrlButton.setDisabled(True)
        """Handle apply/load button click"""
        logging.info("Apply/Load button clicked")
        if not hasattr(self.ui, "urlInput"):
            logging.error("No URL input field available in UI")
            QMessageBox.warning(self, "Error", "No input field available in UI")
            return
        
        url = self.ui.urlInput.text().strip()
        if not url:
            logging.warning("No URL/path provided for apply")
            QMessageBox.warning(self, "Error", "No URL/path provided")
            return
        
        logging.info(f"Applying input string: {url}")
        self._apply_input_string(url)

    def on_start_clicked(self):
        """Start the scheduler with selected settings and random wallpaper"""
        logging.info("Start button clicked - starting scheduler with current settings")
        
        # Check if scheduler is enabled
        if hasattr(self.ui, 'enabledCheck') and not self.ui.enabledCheck.isChecked():
            logging.warning("Scheduler not enabled, enabling it first")
            self.ui.enabledCheck.setChecked(True)
        
        # Get interval from UI
        interval = 30  # default
        if hasattr(self.ui, 'interval_spinBox'):
            interval = self.ui.interval_spinBox.value()
        
        # Get current source and range
        source = self.scheduler.source
        if not source:
            source = str(COLLECTION_DIR)  # default to collection
            self.scheduler.source = source
        
        range_type = self.current_range
        self.scheduler.set_range(range_type)
        
        # Check if there are any files matching the current settings
        logging.info(f"Checking for files with source: {source}, range: {range_type}")
        available_files = self.scheduler._get_media_files()
        
        if not available_files:
            # No files found for current settings - show error popup
            logging.warning(f"No files found for source: {source}, range: {range_type}")
            
            # Determine the error message based on settings
            if source == str(FAVS_DIR):
                if range_type == "mp4":
                    error_msg = "No videos found in your favorites collection!\n\nPlease add some videos to your favorites first."
                elif range_type == "wallpaper":
                    error_msg = "No images found in your favorites collection!\n\nPlease add some images to your favorites first."
                else:  # all
                    error_msg = "No wallpapers found in your favorites collection!\n\nPlease add some wallpapers to your favorites first."
            elif source == str(COLLECTION_DIR):
                if range_type == "mp4":
                    error_msg = "No videos found in your collection!\n\nPlease download or add some videos first."
                elif range_type == "wallpaper":
                    error_msg = "No images found in your collection!\n\nPlease download or add some images first."
                else:  # all
                    error_msg = "No wallpapers found in your collection!\n\nPlease download or add some wallpapers first."
            else:
                error_msg = f"No wallpapers found for current settings!\n\nSource: {source}\nRange: {range_type}"
            
            QMessageBox.warning(
                self,
                "No Wallpapers Found",
                error_msg,
                QMessageBox.StandardButton.Ok
            )
            self._set_status("Scheduler failed - no matching wallpapers")
            return
        
        # Files available - start the scheduler
        logging.info(f"Found {len(available_files)} files for scheduler, starting...")
        self.scheduler.start(source, interval)
        
        # Apply a random wallpaper immediately from the available files
        try:
            random_wallpaper = random.choice(available_files)
            logging.info(f"Applying random wallpaper: {random_wallpaper.name}")
            self._apply_wallpaper_from_path(random_wallpaper)
            self._set_status(f"Scheduler started - {len(available_files)} wallpapers, changing every {interval} minutes")
            
            # Show success message
            QMessageBox.information(
                self,
                "Scheduler Started",
                f"Scheduler started successfully!\n\n"
                f"• Source: {self._get_source_display_name(source)}\n"
                f"• Range: {self._get_range_display_name()}\n"
                f"• Interval: {interval} minutes\n"
                f"• Available wallpapers: {len(available_files)}\n\n"
                f"First wallpaper: {random_wallpaper.name}",
                QMessageBox.StandardButton.Ok
            )
            
        except Exception as e:
            logging.error(f"Failed to apply random wallpaper: {e}")
            self._set_status("Scheduler started but failed to apply first wallpaper")
            QMessageBox.warning(
                self,
                "Scheduler Started with Warning",
                f"Scheduler started but there was an issue applying the first wallpaper:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )
    
    def _get_source_display_name(self, source):
        """Get display name for source"""
        source_names = {
            str(FAVS_DIR): "Favorite Wallpapers",
            str(COLLECTION_DIR): "My Collection",
            "super": "Super Wallpaper"
        }
        return source_names.get(source, "Custom Source")

    def on_browse_clicked(self):
        """Browse web for wallpapers"""
        logging.info("Browse button clicked")
        webbrowser.open_new_tab("https://www.tapeciarnia.pl/")
        logging.debug("Opening tapeciarnia")

    def _handle_browsed_file(self, file_path: str):
        """Handle browsed file with destination selection"""
        logging.info(f"Handling browsed file: {file_path}")
        
        if not os.path.exists(file_path):
            logging.error(f"Browsed file does not exist: {file_path}")
            QMessageBox.warning(self, "Error", "Selected file does not exist.")
            return
        
        # Update URL input
        if hasattr(self.ui, 'urlInput'):
            self.ui.urlInput.setText(file_path)
        
        # Show the same interface as drag & drop area
        if hasattr(self, 'drag_drop_widget'):
            # Simulate a file drop in the drag & drop area
            self.drag_drop_widget.dropped_file_path = file_path
            filename = os.path.basename(file_path)
            file_type = "Video" if self.drag_drop_widget.is_video_file(file_path) else "Image"
            
            # Update UI to show file is ready
            self.drag_drop_widget.upload_text.setText(f" {file_type} Ready!\n\n{filename}")
            self.drag_drop_widget.supported_label.hide()
            
            # Show buttons: Add to Collection, Add to Favorites, Reset
            self.drag_drop_widget.toggle_buttons_visibility(True)
            self.drag_drop_widget.uploadIcon.hide()
            
            # Show collection/favorites buttons, hide set as wallpaper initially
            self.drag_drop_widget.upload_btn.show()  # 
            self.drag_drop_widget.reset_btn.show()   # Always show reset when file is selected
            
            logging.info(f"Browsed file ready for destination selection: {filename}")


    def _update_shuffle_button_states(self, active_type):
        """Update shuffle button states - only one can be active"""
        logging.info(f"Updating shuffle button states: {active_type}")
        if hasattr(self.ui, "randomAnimButton"):
            if active_type == 'animated':
                self.ui.randomAnimButton.setDisabled(True)
                self.ui.randomAnimButton.setProperty("class", "primary")
                self.ui.randomAnimButton.setIcon(self._make_icon(self.ui.randomAnimButton.property("icon_name"),className="primary"))
            else:
                self.ui.randomAnimButton.setDisabled(False)
                self.ui.randomAnimButton.setProperty("class", "ghost")
                self.ui.randomAnimButton.setIcon(self._make_icon(self.ui.randomAnimButton.property("icon_name"),className="ghost"))
            self.ui.randomAnimButton.style().unpolish(self.ui.randomAnimButton)
            self.ui.randomAnimButton.style().polish(self.ui.randomAnimButton)
        
        if hasattr(self.ui, "randomButton"):
            if active_type == 'wallpaper':
                self.ui.randomButton.setDisabled(True)
                self.ui.randomButton.setProperty("class", "primary")
                self.ui.randomButton.setIcon(self._make_icon(self.ui.randomButton.property("icon_name"),className="primary"))
            else:
                self.ui.randomButton.setDisabled(False)
                self.ui.randomButton.setProperty("class", "ghost")
                self.ui.randomButton.setIcon(self._make_icon(self.ui.randomButton.property("icon_name"),className="ghost"))
            self.ui.randomButton.style().unpolish(self.ui.randomButton)
            self.ui.randomButton.style().polish(self.ui.randomButton)
        
        if active_type == None:
                
            if hasattr(self.ui, "randomAnimButton"):
                self.ui.randomAnimButton.setDisabled(False)
                self.ui.randomAnimButton.setProperty("class", "ghost")
                self.ui.randomAnimButton.setIcon(self._make_icon(self.ui.randomAnimButton.property("icon_name"),className="ghost"))
                self.ui.randomAnimButton.style().unpolish(self.ui.randomAnimButton)
                self.ui.randomAnimButton.style().polish(self.ui.randomAnimButton)

            if hasattr(self.ui, "randomButton"):
                self.ui.randomButton.setDisabled(False)
                self.ui.randomButton.setProperty("class", "ghost")
                self.ui.randomButton.setIcon(self._make_icon(self.ui.randomButton.property("icon_name"),className="ghost"))
                self.ui.randomButton.style().unpolish(self.ui.randomButton)
                self.ui.randomButton.style().polish(self.ui.randomButton)

        self.update()
        logging.debug(f"Shuffle button states updated for: {active_type}")

    # Source selection
    def on_super_wallpaper(self):
        # """Super Wallpaper source"""
        # logging.info("Super Wallpaper source selected")
        # self._set_status("Super Wallpaper source selected")
        QMessageBox.information(self, "Super Wallpaper", 
                            "Super Wallpaper feature - Premium curated wallpapers coming soon!")

    def on_favorite_wallpapers(self):
        QMessageBox.information(
            self,
            "Favorites — Coming Soon",
            "The Favorites feature is currently under development.\n\n"
            "You will be able to save and manage your favorite wallpapers in a future update. "
            "Thank you for your patience and for using Tapeciarnia.",
            QMessageBox.StandardButton.Ok
        )

    def on_added_wallpapers(self):
        """My Collection source - includes ALL folders"""
        logging.info("My Collection source selected")
        self._set_status("My Collection source selected")
        
        # has_favorites = FAVS_DIR.exists() and any(FAVS_DIR.iterdir())
        has_saves = SAVES_DIR.exists() and any(SAVES_DIR.iterdir())
        
        if not (has_saves):
            logging.warning("Empty collection - no wallpapers found")
            QMessageBox.information(self, "Empty Collection", 
                                "No wallpapers found in your collection. Download or add some wallpapers first.")
            return
        
        # Set scheduler to use ALL collection folders
        self.scheduler.source = str(SAVES_DIR)
        self._set_status("Scheduler set to use entire collection")
        self._update_source_buttons_active("added")
        logging.info("Scheduler set to use entire collection")

    # Range selection
    def on_range_changed(self, range_type):
        """Handle range selection with validation"""
        logging.info(f"Range changed to: {range_type}")
        self.current_range = range_type
        self.scheduler.set_range(range_type)

        # Check if current source + range combination has files
        if self.scheduler.source:
            available_files = self.scheduler._get_media_files()
            if not available_files:
                # Warn user but don't prevent the change
                logging.warning(f"No files found for source: {self.scheduler.source}, range: {range_type}")
                self._set_status(f"Range set to {range_type} (no files found)")
            else:
                self._set_status(f"Range set to: {range_type} ({len(available_files)} files)")
        else:
            self._set_status(f"Range set to: {range_type}")

        self._update_range_buttons_active(range_type)
        self.config.set_range_preference(range_type)
        logging.debug(f"Range preference saved: {range_type}")

    # Scheduler controls
    def on_scheduler_toggled(self, enabled):
        """Handle scheduler enable/disable"""
        logging.info(f"Scheduler toggled: {enabled}")
        # Update UI visibility
        self._update_scheduler_ui_state()
        
        if enabled:
            if not self.scheduler.source:
                self.scheduler.source = str(COLLECTION_DIR)
                self._set_status("Scheduler enabled - using entire collection")
            
            interval = self.scheduler.interval_minutes
            if hasattr(self.ui, "interval_spinBox"):
                interval = self.ui.interval_spinBox.value()
            
            self.scheduler.start(self.scheduler.source, interval)
            self._set_status(f"Scheduler started - changing every {interval} minutes")
            logging.info(f"Scheduler started with interval: {interval} minutes")
        else:
            self.scheduler.stop()
            self._set_status("Scheduler stopped")
            logging.info("Scheduler stopped")

    def _on_interval_changed(self, val):
        """Handle interval change"""
        logging.info(f"Interval changed to: {val} minutes")
        self.scheduler.interval_minutes = val
        if self.scheduler.is_active():
            self.scheduler.stop()
            self.scheduler.start(self.scheduler.source, val)
        self._set_status(f"Scheduler interval: {val} min")
    
    def update_ui_language(self):
        self.ui.emailInput.setPlaceholderText(f"{self.lang['auth']['emailPlaceholder']}")
        self.ui.passwordInput.setPlaceholderText(f"{self.lang['auth']['passwordPlaceholder']}")
        self.ui.logInBnt.setText(f"{self.lang['auth']['logInButton']}")
        # main controls
        self.ui.randomAnimButton.setText(f"  {self.lang['navigation']['shuffleAnimatedButton']}")
        self.ui.randomButton.setText(f"  {self.lang['navigation']['shuffleWallpaperButton']}")
        self.ui.browseButton.setText(f"  {self.lang['navigation']['browseWallpapersButton']}")
        # uploadSection
        self.ui.add_file_label.setText(f"  {self.lang['uploadSection']['addFilesHeader']}")
        # self.ui.uploadText.setText(self.lang["uploadSection"]["dragDropInstruction"]) 
        # self.ui.uploadSupported.setText(self.lang["uploadSection"]["supportedFormatsHint"])
        # url loader
        self.ui.url_loader_text_label.setText(f"  {self.lang['uploadSection']['imagesOrVideoURLHeader']}")
        self.ui.loadUrlButton.setText(f"{self.lang['uploadSection']['loadButton']}")
        self.ui.url_helper_text_label.setText(f"  {self.lang['uploadSection']['urlHelperText']}")
        # settings
        self.ui.autoLabel.setText(f"  {self.lang['settings']['autoChangeHeader']}")
        self.ui.enabledCheck.setText(f"  {self.lang['settings']['enabledLabel']}")
        self.ui.inverval_lable.setText(f"  {self.lang['settings']['intervalLabel']}")
        self.ui.wallpaper_source_lable.setText(f"  {self.lang['settings']['wallpaperSourceLabel']}")
        self.ui.super_wallpaper_btn.setText(f"  {self.lang['settings']['superWallpaperButton']}")
        self.ui.fvrt_wallpapers_btn.setText(f"  {self.lang['settings']['favoriteWallpapersButton']}")
        self.ui.added_wallpaper_btn.setText(f"  {self.lang['settings']['myCollectionButton']}")
        self.ui.range_lable.setText(f"  {self.lang['settings']['rangeHeader']}")
        self.ui.range_all_bnt.setText(f"  {self.lang['settings']['rangeAllButton']}")
        self.ui.range_wallpaper_bnt.setText(f"  {self.lang['settings']['rangeWallpaperButton']}")
        self.ui.range_mp4_bnt.setText(f"  {self.lang['settings']['rangeMp4Button']}")
        self.ui.startButton.setText(f"  {self.lang['settings']['startButton']}")
        self.ui.resetButton.setText(f"  {self.lang['settings']['resetButton']}")

    def set_buttons(self,enabled: bool):
        self.ui.randomButton.setDisabled(not enabled)
        self.ui.randomAnimButton.setDisabled(not enabled)
        self.ui.loadUrlButton.setDisabled(not enabled)
        self.ui.logInBnt.setEnabled(not enabled)
        self.ui.resetButton.setEnabled(not enabled)
        self.ui.startButton.setEnabled(not enabled)


    def _apply_input_string(self, text: str):
        """Main method to apply wallpaper from URL or file path."""

        if not is_connected_to_internet:
            self._set_status("Unable to connect to the server.Please check your connection")
            return
        # Disable buttons during processing
        self.set_buttons(False)

        text = (text or "").strip()
        logging.info(f"Applying input: {text}")

        if not text:
            QMessageBox.warning(self, "Warning", "Please enter a valid URL or file path.")
            self.set_buttons(True)
            return
        


        validated = validate_url_or_path(text)
        if not validated:
            logging.warning(f"Input not recognized: {text}")
            QMessageBox.warning(self, "Error", f"Input not recognized: {text}")
            self.set_buttons(True)

        if is_tapeciarnia_redirect_url(validated):
            logging.info(f"Tapeciarnia redirect url found: {validated}")
            validated = fast_resolve_tapeciarnia_redirect(validated)
            if not validated:
                QMessageBox.warning(self, "Unsupported URL",
                    "The URL doesn't appear to be a supported image or video.")
                return            

        p = Path(validated)
        if p.exists():
            logging.info(f"Handling local file: {p}")
            self._handle_local_file(p)
            return

        # -------- Handle Remote URL --------
        if validate_tapeciarnia_url(validated):
            logging.info(f"Processing remote URL: {validated}")

            media_type = get_media_type(validated)
            logging.debug(f"Detected media type: {media_type}")

            if media_type == "image":
                self._handle_remote_image(validated)
            elif media_type == "video":
                self._handle_remote_video(validated)
            else:
                QMessageBox.warning(self, "Unsupported URL",
                                    "The URL doesn't appear to be a supported image or video.")
            self.set_buttons(True)
            return
    
        else:

            # -------- Fallback --------
            logging.warning(f"Unsupported input type: {text}")
            QMessageBox.warning(self, "Unsupported URL", "The URL doesn't appear to be a supported image or video.")
            self.set_buttons(True)


    def _handle_local_file(self, file_path: Path):
        """Handle local file application"""
        logging.info(f"Processing local file: {file_path}")
        if file_path.suffix.lower() in self.config.get_valid_video_extensions():
            logging.debug("Local file is video, copying to videos directory")
            self._apply_video(str(file_path))
        elif file_path.suffix.lower() in self.config.get_valid_image_extensions():
            logging.debug("Local file is image, copying to images directory")
            self._apply_image(str(file_path))
        else:
            logging.warning(f"Unsupported local file type: {file_path.suffix}")
            QMessageBox.warning(self, "Unsupported", "Unsupported local file type.")


    def _handle_remote_image(self, url: str):
        """Handle remote image download and application with progress window"""
        logging.info(f"Downloading remote image: {url}")
        
        try:
            # Create progress dialog for image download
            
            # Start download in a thread to show progress
            self.image_download_thread = ImageDownloadThread(url)
            self.image_download_thread.progress.connect(
                lambda percent, status: (
                    self._set_status(status)
                )
            )
            self.image_download_thread.error.connect(self._on_download_error)
            self.image_download_thread.done.connect(self._on_image_download_done)
            
            self.image_download_thread.start()
            logging.info("Image download thread started")
            
        except Exception as e:
            logging.error(f"Image download setup failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Image download setup failed: {e}")

    def _on_image_download_done(self, file_path: str):
        """Handle completion of image download"""
        logging.info(f"Image download completed: {file_path}")
        self._safe_process_file(Path(file_path))

    def _handle_remote_video(self, url: str):
        """Handle remote video download - for direct video links"""
        logging.info(f"Downloading remote video: {url}")
        self._set_status("Downloading video...")
        cleanup_temp_marker()
        self._handle_direct_video_download(url)


    def _handle_direct_video_download(self, url: str):
        """Handle direct video file downloads (not YouTube/streaming)"""
        try:
            logging.info(f"Starting direct video download: {url}")
            
            # Sanitize filename
            filename = url.split("/")[-1]
            filename = self._get_safe_filename(filename)
            download_path = SAVES_DIR / filename
            
            logging.info(f"Downloading to: {download_path}")
            
            # Start download in a thread to avoid blocking UI
            self.direct_download_thread = DirectDownloadThread(url, str(download_path))
            self.direct_download_thread.progress.connect(
                lambda percent, status: (
                    self._set_status(status)
                )
            )
            self.direct_download_thread.error.connect(self._on_download_error)
            self.direct_download_thread.done.connect(self._on_direct_video_download_done)
            
            self.direct_download_thread.start()
            logging.info("Direct download thread started")
            
        except Exception as e:
            logging.error(f"Direct download setup failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Download setup failed: {e}")

    def _on_direct_video_download_done(self, file_path: str):
        """Handle completion of direct video download - FIXED to not set wallpaper on failure"""
        logging.info(f"Direct download completed: {file_path}")
        self._safe_process_file(Path(file_path))



    def _get_safe_filename(self, filename):
        """Remove invalid characters for both Windows and Linux"""
        logging.debug(f"Sanitizing filename: {filename}")
        # Characters invalid on Windows: < > : " | ? *
        # Characters to avoid on Linux: / and null bytes
        invalid_chars = '<>:"|?*/\0'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        logging.debug(f"Sanitized filename: {filename}")
        return filename


    def _validate_downloaded_file(self, path: str) -> bool:
        """Thoroughly validate the downloaded file"""
        if not path or not isinstance(path, str):
            logging.error("Invalid path provided")
            return False
        
        try:
            p = Path(path)
            
            # Check if file exists
            if not p.exists():
                logging.error(f"Downloaded file does not exist: {path}")
                return False
            
            # Check file size
            file_size = p.stat().st_size
            if file_size == 0:
                logging.error(f"Downloaded file is empty: {path}")
                return False
            
            # Check if file is readable
            if not os.access(p, os.R_OK):
                logging.error(f"Downloaded file is not readable: {path}")
                return False
            
            # Additional checks for video files
            if p.suffix.lower() in ('.mp4', '.mkv', '.webm', '.avi', '.mov'):
                # Quick check if it might be a valid video file
                if file_size < 1024:  # Less than 1KB is suspicious for a video
                    logging.warning(f"Video file seems too small: {file_size} bytes")
                    # Don't fail here, just warn
            
            logging.info(f"File validation passed: {p.name} ({file_size} bytes)")
            return True
            
        except Exception as e:
            logging.error(f"File validation error: {e}")
            return False


    def _safe_process_file(self, downloaded_file_path: Path,):
        """Safely process destination with comprehensive error handling"""
        try:
            # Final validation before processing
            if not downloaded_file_path.exists():
                logging.error("File disappeared during destination selection")
                QMessageBox.critical(
                    self,
                    "File Error", 
                    "The file is no longer available. Operation cancelled.",
                    QMessageBox.StandardButton.Ok
                )
                return
            
            self._process_download_file(downloaded_file_path)
            
        except Exception as e:
            logging.error(f"Error processing destination: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to process file: {str(e)}",
                QMessageBox.StandardButton.Ok
            )


    def _process_download_file(self, downloaded_file_path: Path):

        try:

            self._apply_wallpaper_from_path(downloaded_file_path)

            logging.info(f"Downloaded file saved to {SAVES_DIR}: {downloaded_file_path}")

        except Exception as e:
            logging.error(f"Failed to process downloaded file: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add file: {str(e)}")


    def _apply_wallpaper_from_path(self, file_path: Path):
        """Apply wallpaper from file path - OPTIMIZED to avoid unnecessary stops"""
        logging.info(f"Applying wallpaper from path: {file_path}")
        current_is_video = self.controller.current_is_video
        new_is_video = file_path.suffix.lower() in (".mp4", ".mkv", ".webm", ".avi", ".mov")
        
        # Only stop if necessary (video to video, video to image, or image to video)
        needs_stop = (current_is_video and new_is_video) or (current_is_video and not new_is_video) or (not current_is_video and new_is_video)
        
        if new_is_video:
            self._apply_video(str(file_path))
        else:
            self._apply_image(str(file_path))

    def _apply_video(self, video_path: str):
        """Apply video wallpaper"""
        try:
            self.set_buttons(False)
            logging.info(f"Applying video wallpaper: {video_path}")
            self.controller.start_video(video_path)
            self.config.set_last_video(video_path)
            self._set_status(f"Playing video: {Path(video_path).name}")
            self._update_url_input(video_path)
            logging.info(f"Video wallpaper applied successfully: {Path(video_path).name}")
            self.set_buttons(True)
        except Exception as e:
            self.set_buttons(True)
            logging.error(f"Failed to play video: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to play video: {e}")

    def _apply_image(self, image_path: str):
        """Apply image wallpaper with fade effect - FIXED for null pixmap"""
        try:
            self.set_buttons(False)
            logging.info(f"Applying image wallpaper with fade: {image_path}")
            
            # Check if image file exists and is valid
            if not os.path.exists(image_path):
                logging.error(f"Image file does not exist: {image_path}")
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Load the new pixmap first
            new_pix = QPixmap(image_path)
            if new_pix.isNull():
                logging.error(f"Failed to load image: {image_path}")
                raise ValueError(f"Invalid image file: {image_path}")
            
            
            # Apply wallpaper
            self.controller.start_image(image_path)
            self.config.set_last_video(image_path)
            
            self._set_status(f"Image applied: {Path(image_path).name}")
            self._update_url_input(image_path)
            logging.info(f"Image wallpaper applied: {Path(image_path).name}")
            self.set_buttons(True)
            
        except Exception as e:
            logging.error(f"Fade apply failed: {e}", exc_info=True)
            # Fallback to direct application without fade
            try:
                self.set_buttons(True)
                logging.info("Attempting direct image application without fade")
                self.controller.start_image(image_path)
                self.config.set_last_video(image_path)
                self._set_status(f"Image applied (no fade): {Path(image_path).name}")
                self._update_url_input(image_path)
            except Exception as fallback_error:
                logging.error(f"Fallback image application also failed: {fallback_error}")
                QMessageBox.warning(self, "Error", f"Failed to apply image: {fallback_error}")

    # Utility methods - FIXED: Proper media type separation
    def _get_media_files(self, media_type="all"):
        """Get media files based on current range and media type - FIXED LOGIC"""
        logging.debug(f"Getting media files - type: {media_type}, range: {self.current_range}")
        files = []
        
        # Define search folders based on CURRENT SOURCE (not just range)
        if hasattr(self, 'scheduler') and self.scheduler.source:
            if self.scheduler.source == str(FAVS_DIR):
                search_folders = [FAVS_DIR]
                source_type = "favorites"
            elif self.scheduler.source == str(SAVES_DIR):
                search_folders = [SAVES_DIR]
                source_type = "collection"
            else:
                search_folders = [Path(self.scheduler.source)]
                source_type = "custom"
        else:
            # Fallback to range-based selection
            search_folders = [SAVES_DIR]
            source_type = "range-based"
        
        logging.debug(f"Using source: {source_type}, folders: {[str(f) for f in search_folders]}")
        
        # Define extensions based on media type
        if media_type == "mp4":
            extensions = ('.mp4', '.mkv', '.webm', '.avi', '.mov')
        elif media_type == "wallpaper":
            extensions = ('.jpg', '.jpeg', '.png', '.gif')
        else:
            extensions = ('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mkv', '.webm', '.avi', '.mov')
        
        for folder in search_folders:
            if folder.exists():
                folder_files = [
                    f for f in folder.iterdir() 
                    if f.is_file() and f.suffix.lower() in extensions
                ]
                files.extend(folder_files)
                logging.debug(f"Found {len(folder_files)} files in {folder}")
        
        logging.debug(f"Total media files found: {len(files)} from {source_type}")
        return files

    def _get_range_display_name(self):
        range_names = {"all": "All", "wallpaper": "Wallpaper", "mp4": "MP4"}
        display_name = range_names.get(self.current_range, "All")
        logging.debug(f"Range display name: {display_name}")
        return display_name

    def _update_url_input(self, text: str):
        """Update URL input field"""
        logging.debug(f"Updating URL input field: {text}")
        if hasattr(self.ui, "urlInput"):
            self.ui.urlInput.setText(text)

    def _update_source_buttons_active(self, active_source):
        """Update source button styles"""
        logging.debug(f"Updating source button styles for: {active_source}")
        sources = {
            # "super": getattr(self.ui, "super_wallpaper_btn", None),
            # "favorites": getattr(self.ui, "fvrt_wallpapers_btn", None),
            "added": getattr(self.ui, "added_wallpaper_btn", None)
        }
        
        for btn in sources.values():
            if btn:
                btn.setProperty("class", "ghost")
                btn.setIcon(self._make_icon(btn.property("icon_name"),className="ghost"))
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        
        if active_source in sources and sources[active_source]:
            sources[active_source].setProperty("class", "primary")
            sources[active_source].setIcon(self._make_icon(sources[active_source].property("icon_name"),className="primary"))
            sources[active_source].style().unpolish(sources[active_source])
            sources[active_source].style().polish(sources[active_source])
        
        logging.debug(f"Source button {active_source} set to active")

    def _update_range_buttons_active(self, active_range):
        """Update range button styles"""
        logging.debug(f"Updating range button styles for: {active_range}")
        range_buttons = {
            "all": getattr(self.ui, "range_all_bnt", None),
            "wallpaper": getattr(self.ui, "range_wallpaper_bnt", None),
            "mp4": getattr(self.ui, "range_mp4_bnt", None)
        }
        
        for btn in range_buttons.values():
            if btn:
                btn.setProperty("class", "ghost")
                btn.setIcon(self._make_icon(btn.property("icon_name"),className="ghost"))
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        
        if active_range in range_buttons and range_buttons[active_range]:
            range_buttons[active_range].setProperty("class", "primary")
            range_buttons[active_range].setIcon(self._make_icon(range_buttons[active_range].property("icon_name"),className="primary"))
            range_buttons[active_range].style().unpolish(range_buttons[active_range])
            range_buttons[active_range].style().polish(range_buttons[active_range])
        
        logging.debug(f"Range button {active_range} set to active")

    def _perform_reset_with_confirmation(self):
        """Reset to default wallpaper WITH confirmation"""
        logging.info("Reset with confirmation triggered")
        reply = QMessageBox.question(
            self,
            self.lang["dialog"]["confirm_reset_title"],
            self.lang["dialog"]["confirm_reset_dia"],
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logging.info("User confirmed reset")
            self._perform_reset()
            self._set_status("Reset completed successfully")
        else:
            logging.info("User cancelled reset")
            self._set_status("Reset cancelled")
    

    def download_and_set_online_wallpaper(self, url: str, is_animated: bool):
        """
        Download online wallpaper and set it with progress tracking
        """
        try:
            logging.info(f"Downloading online wallpaper: {url}")
            
            # Create progress dialog
            
            # Determine destination folder and filename
            if is_animated:
                dest_folder = SAVES_DIR
            else:
                dest_folder = SAVES_DIR
            
            # Generate unique filename
            # timestamp = int(time.time())
            filename = f"{url.split("/")[-1]}"
            download_path = dest_folder / filename
            
            # Start download thread
            if is_animated:
                self.download_thread = DirectDownloadThread(url, str(download_path))
            else:
                self.download_thread = ImageDownloadThread(url, str(download_path))
            
            # Connect signals
            self.download_thread.progress.connect(
                lambda percent, status: (
                    self._set_status(status)
                )
            )
            self.download_thread.error.connect(self._on_online_download_error)
            self.download_thread.done.connect(
                lambda path: self._on_online_download_done(path, is_animated)
            )
            
            self.download_thread.start()
            logging.info("Online wallpaper download started")
            
        except Exception as e:
            logging.error(f"Online download setup failed: {e}", exc_info=True)
            self._fallback_to_local_shuffle(is_animated)

    def _on_online_download_done(self, file_path: str, is_animated: bool):
        """
        Handle successful online wallpaper download
        """
        logging.info(f"Online download completed: {file_path}")
        self._update_shuffle_button_states(None)
        self.ui.randomButton.setDisabled(False)
        self.ui.randomAnimButton.setDisabled(False)
        self.ui.loadUrlButton.setDisabled(False)
        
        # Close progress dialog
        
        # Validate downloaded file
        if not self._validate_downloaded_file(file_path):
            logging.error("Online wallpaper download validation failed")
            self._fallback_to_local_shuffle(is_animated)
            return
        
        # Update URL input
        if hasattr(self.ui, 'urlInput'):
            self.ui.urlInput.setText(file_path)
        
        # Set as wallpaper immediately (no confirmation for online shuffle)
        try:
            logging.info(f"Setting online wallpaper: {file_path}")
            self._apply_wallpaper_from_path(Path(file_path))
            self._set_status(f"Online {'animated' if is_animated else 'static'} wallpaper set")
            
            # Show success message
            # QMessageBox.information(
            #     self,
            #     "Online Wallpaper Set",
            #     f"Successfully set online {'animated' if is_animated else 'static'} wallpaper!",
            #     QMessageBox.StandardButton.Ok
            # )
            
            logging.info("Online wallpaper set successfully")
            
        except Exception as e:
            logging.error(f"Failed to set online wallpaper: {e}")
            self._fallback_to_local_shuffle(is_animated)

    def _on_online_download_error(self, error_msg: str):
        """
        Handle online download errors
        """
        logging.error(f"Online download error: {error_msg}")
        
        
        # Extract is_animated from error context or use fallback
        is_animated = "animated" in error_msg.lower() or "video" in error_msg.lower()
        self._fallback_to_local_shuffle(is_animated)

    def _fallback_to_local_shuffle(self, is_animated: bool):
        """
        Fallback to local shuffle when online fails
        """
        logging.warning(f"Falling back to local shuffle for {'animated' if is_animated else 'static'}")
        
        # Show warning message
        QMessageBox.warning(
            self,
            "Online Unavailable",
            "Could not fetch online wallpaper. Using local collection instead.",
            QMessageBox.StandardButton.Ok
        )
        
        # Use local shuffle
        if is_animated:
            self._perform_local_animated_shuffle()
        else:
            self._perform_local_static_shuffle()

    def _perform_local_animated_shuffle(self):
        """
        Perform local animated shuffle (existing functionality)
        """
        logging.info("Performing local animated shuffle")
        video_files = self._get_media_files(media_type="mp4")
        
        if not video_files:
            logging.warning("No local animated wallpapers found")
            QMessageBox.information(
                self, 
                "No Videos", 
                "No animated wallpapers found in your local collection."
            )
            self._update_shuffle_button_states(None)
            self.current_shuffle_type = None
            return
        
        selected = random.choice(video_files)
        logging.info(f"Selected local animated wallpaper: {selected.name}")
        self._apply_wallpaper_from_path(selected)
        self._update_url_input(str(selected))
        self._update_shuffle_button_states(None)

        # enable the buttons
        self.ui.randomButton.setDisabled(False)
        self.ui.randomAnimButton.setDisabled(False)
        self.ui.loadUrlButton.setDisabled(False)


    def _perform_local_static_shuffle(self):
        """
        Perform local static shuffle (existing functionality)
        """
        logging.info("Performing local static shuffle")
        image_files = self._get_media_files(media_type="wallpaper")
        
        if not image_files:
            logging.warning("No local static wallpapers found")
            QMessageBox.information(
                self, 
                "No Images", 
                "No wallpapers found in your local collection."
            )
            self._update_shuffle_button_states(None)
            self.current_shuffle_type = None
            return
        
        selected = random.choice(image_files)
        logging.info(f"Selected local static wallpaper: {selected.name}")
        self._apply_wallpaper_from_path(selected)
        self._update_url_input(str(selected))
        self._update_shuffle_button_states(None)

        # enable the buttons
        self.ui.randomButton.setDisabled(False)
        self.ui.randomAnimButton.setDisabled(False)
        self.ui.loadUrlButton.setDisabled(False)


    def _on_download_error(self, error_msg: str):
        """Handle download errors"""
        logging.error(f"Download error: {error_msg}")
        QMessageBox.critical(self, "Download Error", error_msg)
        self._set_status(f"Download failed: {error_msg}")
        self.set_buttons(True)

    # Settings management
    def _load_settings(self):
        """Load saved settings"""
        logging.info("Loading saved settings")
        # Load last video
        # last_video = self.config.get_last_video()
        # if last_video and hasattr(self.ui, "urlInput"):
        #     self.ui.urlInput.setText(last_video)
        #     logging.info(f"Loaded last video from config: {last_video}")

        # Load range preference
        self.current_range = self.config.get_range_preference()
        self.scheduler.set_range(self.current_range)
        self._update_range_buttons_active(self.current_range)
        logging.info(f"Loaded range preference: {self.current_range}")

        # Load scheduler settings
        source, interval, enabled = self.config.get_scheduler_settings()
        self.scheduler.source = source
        self.scheduler.interval_minutes = interval
        
        if hasattr(self.ui, "interval_spinBox"):
            self.ui.interval_spinBox.setValue(interval)
        
        if hasattr(self.ui, "enabledCheck"):
            self.ui.enabledCheck.setChecked(enabled)
            if enabled and source:
                self.scheduler.start(self.scheduler.source, interval)
        
        logging.info(f"Loaded scheduler settings - source: {source}, interval: {interval}, enabled: {enabled}")
        
        # Update UI state based on scheduler
        self._update_scheduler_ui_state()
        logging.info("Settings loaded successfully")

    # System tray
    def _setup_tray(self):
        logging.debug("Setting up system tray")
        # Don't quit when last window is closed
        QApplication.setQuitOnLastWindowClosed(False)
        
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logging.error("System tray is not available on this system")
            QMessageBox.critical(None, "System Tray", "System tray is not available on this system.")
            return
        
        # Create tray icon
        self.tray = QSystemTrayIcon(self)
        
        # Set icon
        icon = QIcon()
        cand = resource_path("bin/media/icon.ico")
        if cand.exists():
            icon = QIcon(str(cand))
            logging.debug("Using custom tray icon")
        else:
            # Fallback to standard icon
            icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
            logging.debug("Using fallback system tray icon")
        
        self.tray.setIcon(icon)
        self.tray.setToolTip("Tapeciarnia - Live Wallpaper Manager")
        
        # Create context menu
        tray_menu = QMenu()
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_from_tray)
        
        hide_action = QAction("Hide to Tray", self)
        hide_action.triggered.connect(self.hide_to_tray)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._exit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)
        
        self.tray.setContextMenu(tray_menu)
        
        # Connect tray icon activation
        self.tray.activated.connect(self._on_tray_activated)
        
        # Show the tray icon
        self.tray.show()
        self.tray.setVisible(True)
        logging.info("System tray setup completed")

    def _on_tray_activated(self, reason):
        """Handle tray icon clicks"""
        logging.debug(f"Tray icon activated with reason: {reason}")
        if reason == QSystemTrayIcon.DoubleClick:
            # Double-click toggles window visibility
            logging.debug("Tray icon double-clicked")
            if self.isVisible():
                self.hide_to_tray()
            else:
                self.show_from_tray()
        elif reason == QSystemTrayIcon.Trigger:
            # Single click also toggles window
            logging.debug("Tray icon single-clicked")
            if self.isVisible():
                self.hide_to_tray()
            else:
                self.show_from_tray()
    
    def on_login_clicked(self):
        """Handle login button click - show Coming Soon message"""
        logging.info("Login button clicked")
        self.ui.logInBnt.setEnabled(False)  
        if not self.isLogin:
            email = self.ui.emailInput.text().strip()
            password = self.ui.passwordInput.text().strip()

            if email and password:
                url = "https://tapeciarnia.pl/program/login_2025.php"
                payload = {
                "login": email, # aka username
                "key": password, # aka password
                "lang": self.config.get_language()
                }

                logging.debug(payload)
                login = LoginWorker(url=url, payload=payload,method="GET")
                login.success.connect(self._on_login_success)
                login.failed.connect(lambda e: self._on_login_failed(data=e,login_worker=login))
                login.start()

            else:
                self.ui.logInBnt.setEnabled(True)  
                QMessageBox.information(
                    self,
                    "Invalid credential",
                    "Please enter valid credentials",
                    QMessageBox.StandardButton.Ok
                )

        else:
            self.handle_log_out()

    
    def _on_login_success(self,data:dict):
        self.ui.logInBnt.setEnabled(True)
        if data.get("is_ok") == True:
            self.isLogin = True
            self._setLogInState()
            self.config.set_login_status(self.isLogin)

            self.ui.passwordInput.clear()
            self.ui.emailInput.clear()

            self.config.set_login_key(data.get("key"))
            self.config.set_login(data.get("login"))

            QMessageBox.information(
                self,
                "Log in successfull",
                str(data),
                QMessageBox.StandardButton.Ok
            )
            logging.info("Logging in success")

            # hide the input areas and change the text on log in bnt to log out
        
        else:
            QMessageBox.information(
                self,
                "Log in faild",
                str(data),
                QMessageBox.StandardButton.Ok
            )
            logging.info("Logging failed")

        

    
    def _on_login_failed(self,data,login_worker:LoginWorker):
        self.ui.logInBnt.setEnabled(True)
        QMessageBox.information(
            self,
            "Log in faild",
            str(data),
            QMessageBox.StandardButton.Ok
        )
        logging.info("Logging failed")
        login_worker.stop()
        logging.warning(f"Logging in failed: {data}")

    def handle_log_out(self):
        self.ui.logInBnt.setEnabled(True)
        self.isLogin = False
        self.config.set_login_status(self.isLogin)
        self.config.clear_session()
        self._setLogInState()
        self.ui.urlInput.clear()
        self.ui.passwordInput.clear()

    def _exit_app(self):
        """Properly quit the application from tray menu with confirmation and progress"""
        logging.info("Exit from tray menu triggered")
        reply = QMessageBox.question(
            self,
            self.lang["dialog"]["confirm_exit_title"],
            self.lang["dialog"]["confirm_exit_dialog"],
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            logging.info("User confirmed exit from tray")
            # Show shutdown progress for tray exit too
            self._show_shutdown_progress_from_tray()
        else:
            logging.info("User cancelled exit from tray")

    def handle_startup_uri(self, action, params):
            """
            Processes the URI command received upon application launch, handling both
            standard (setwallpaper) and custom (set_url_default, mp4_url ,id) formats.
            
            Args:
                action (str): The primary command (e.g., 'setwallpaper', 'mp4_url').
                params (dict): Dictionary of query parameters (must contain 'url' for most actions).
            """
            
            logging.info(f"Handling startup URI. Action: {action}, Params: {params}")

            # Check for the required 'url' parameter for most actions
            wallpaper_url = params.get('url')
            
            if action == "setwallpaper":
            # Handles: tapeciarnia://setwallpaper?url=... (Standard action)
                if wallpaper_url:
                    logging.info(f"Executing standard setwallpaper command for URL: {wallpaper_url}")
                    
                    # Show a confirmation message to the user
                    reply = QMessageBox.question(
                        self,
                        "Confirm Wallpaper Change",
                        f"Do you want to set the wallpaper from this URI?\n\n{wallpaper_url}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    # FIX: Add the missing execution logic (same as other actions)
                    confirmed = reply == QMessageBox.StandardButton.Yes
                    self.last_uri_command = {
                        "action": action,
                        "url": wallpaper_url,
                        "confirmed": confirmed
                    }
                    logging.info(f"URI command confirmation stored: {self.last_uri_command}")

                    # FIX: Add the missing action logic
                    if confirmed:
                        try:
                            self.ui.urlInput.setText(wallpaper_url)
                            self._set_status("Applying wallpaper from URI...")
                            self._apply_input_string(wallpaper_url)
                        except Exception as e:
                            logging.error(f"Failed to apply wallpaper from URI: {e}", exc_info=True)
                            QMessageBox.critical(self, "Error", f"Failed to apply wallpaper: {e}")
                    else:
                        self._set_status("Wallpaper change from URI was cancelled by user")
                else:
                    logging.error("setwallpaper action received, but 'url' parameter is missing.")
                    QMessageBox.warning(self, "URI Error", "The 'setwallpaper' command is missing the required URL parameter.")


            elif action == "mp4_url":
                # Handles: tapeciarnia:mp4_url:https://video.mp4 (Custom action for video wallpaper)
                if wallpaper_url:
                    logging.info(f"Executing mp4_url command for URL: {wallpaper_url}")
                    
                    # --- CORE LOGIC DISPATCH: Video Wallpaper ---
                    # This handles video URLs and triggers the video handler logic.
                    # e.g., self.controller.start_video_wallpaper(wallpaper_url)
                    
                    self.ui.urlInput.setText(wallpaper_url)
                    reply = QMessageBox.question(
                        self,
                        "Confirm Wallpaper Change",
                        f"Do you want to set the wallpaper from this URI?\n\n{wallpaper_url}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )

                    # store the user's decision for later inspection or logging
                    confirmed = reply == QMessageBox.StandardButton.Yes
                    self.last_uri_command = {
                        "action": action,
                        "url": wallpaper_url,
                        "confirmed": confirmed
                    }
                    logging.info(f"URI command confirmation stored: {self.last_uri_command}")

                    # act on the user's choice
                    if confirmed:
                        # proceed to apply the wallpaper (reuse existing input handling)
                        try:
                            self.ui.urlInput.setText(wallpaper_url)
                            self._set_status("Applying wallpaper from URI...")
                            self._apply_input_string(wallpaper_url)
                        except Exception as e:
                            logging.error(f"Failed to apply wallpaper from URI: {e}", exc_info=True)
                            QMessageBox.critical(self, "Error", f"Failed to apply wallpaper: {e}")
                    else:
                        self._set_status("Wallpaper change from URI was cancelled by user")

            elif action == "set_url_default":
                # Handles: tapeciarnia:https://image.jpg (Custom default action for static image)
                if wallpaper_url:
                    logging.info(f"Executing default set_url_default command for URL: {wallpaper_url}")
                    
                    # --- CORE LOGIC DISPATCH: Default/Static Wallpaper ---
                    # This handles the simple image URLs (e.g., .jpg, .png)
                    # e.g., self.controller.download_and_set_static_wallpaper(wallpaper_url)
                    
                    reply = QMessageBox.question(
                        self,
                        "Confirm Wallpaper Change",
                        f"Do you want to set the wallpaper from this URI?\n\n{wallpaper_url}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    # Store the user's decision
                    confirmed = reply == QMessageBox.StandardButton.Yes
                    self.last_uri_command = {
                        "action": action,
                        "url": wallpaper_url,
                        "confirmed": confirmed
                    }
                    logging.info(f"URI command confirmation stored: {self.last_uri_command}")
                    
                    # Act on user's choice
                    if confirmed:
                        try:
                            self.ui.urlInput.setText(wallpaper_url)
                            self._set_status("Applying static wallpaper from URI...")
                            self._apply_input_string(wallpaper_url)
                        except Exception as e:
                            logging.error(f"Failed to apply wallpaper from URI: {e}", exc_info=True)
                            QMessageBox.critical(self, "Error", f"Failed to apply wallpaper: {e}")
                    else:
                        self._set_status("Wallpaper change from URI was cancelled by user")
                        
                else:
                    logging.error("set_url_default action received, but 'url' parameter is missing.")
                    QMessageBox.warning(self, "URI Error", "The 'set_url_default' command is missing the required URL parameter.")

            elif action == "openfavorites":
                logging.info("Executing openfavorites command.")
                try:
                    folder = get_folder_for_source("favorites")
                    if not folder.exists():
                        logging.warning(f"Favorites folder does not exist: {folder}")
                        QMessageBox.warning(self, "Folder Not Found", f"The favorites folder does not exist:\n{folder}")
                    else:
                        success = open_folder_in_explorer(folder)
                        if success:
                            self._set_status("Opened Favorites folder")
                            QMessageBox.information(self, "Opened Favorites", f"Opened favorites folder:\n{folder}")
                        else:
                            logging.error(f"Failed to open favorites folder in explorer: {folder}")
                            QMessageBox.warning(self, "Open Failed", f"Could not open folder in file explorer:\n{folder}")
                except Exception as e:
                    logging.error(f"Failed to open favorites folder: {e}", exc_info=True)
                    QMessageBox.critical(self, "Error", f"Failed to open favorites folder: {e}")
            
            elif action == "id":
                
                image_id = params.get('id')
                if image_id: 

                    wallpaper_url = f"https://tapeciarnia.pl/program/pobierz_jpeg_v2.php?id={image_id}"


                    logging.info(f"Executing default set_url_default command for URL: {wallpaper_url}")
                    
                    # --- CORE LOGIC DISPATCH: Default/Static Wallpaper ---
                    # This handles the simple image URLs (e.g., .jpg, .png)
                    # e.g., self.controller.download_and_set_static_wallpaper(wallpaper_url)
                    
                    reply = QMessageBox.question(
                        self,
                        "Confirm Wallpaper Change",
                        f"Do you want to set the wallpaper from this URI?\n\ntapeciarnia:{image_id}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    # Store the user's decision
                    confirmed = reply == QMessageBox.StandardButton.Yes
                    self.last_uri_command = {
                        "action": action,
                        "url": wallpaper_url,
                        "confirmed": confirmed
                    }
                    logging.info(f"URI command confirmation stored: {self.last_uri_command}")
                    
                    # Act on user's choice
                    if confirmed:
                        try:
                            self.ui.urlInput.setText(f"tapeciarnia:{image_id}")
                            self._set_status("Applying static wallpaper from URI...")
                            self._apply_input_string(wallpaper_url)
                        except Exception as e:
                            logging.error(f"Failed to apply wallpaper from URI: {e}", exc_info=True)
                            QMessageBox.critical(self, "Error", f"Failed to apply wallpaper: {e}")
                    else:
                        self._set_status("Wallpaper change from URI was cancelled by user")
                        
                else:
                    logging.error("set_url_default action received, but 'url' parameter is missing.")
                    QMessageBox.warning(self, "URI Error", "The 'set_url_default' command is missing the required URL parameter.")



            else:
                logging.warning(f"Unknown URI action received: {action}")
                QMessageBox.warning(self, "URI Error", f"Unknown command: '{action}'.")

