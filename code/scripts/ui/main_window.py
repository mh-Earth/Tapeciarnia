import os
import sys
import random
import logging
import logging
from pathlib import Path
import time
import webbrowser

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog,
    QSystemTrayIcon, QMenu, QVBoxLayout,
    QStyle, QSizePolicy,QSpacerItem
)
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtCore import QTimer, Qt, QEvent, QSize
from PySide6.QtWidgets import QMessageBox

from .widgets import EnhancedDragDropWidget,CustomMessageBox,ButtonCollection

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
from core.download_manager import VideoDownloadThread,ImageDownloadThread
from core.scheduler import UnifiedWallpaperScheduler
from core.login_handler import LoginWorker
from core.shuffler import Shuffler
# Import utilities
from utils.path_utils import SUPER_WALLPAPER_DIR,SAVES_DIR, FAVS_DIR, get_folder_for_range, get_folder_for_source, open_folder_in_explorer
from utils.system_utils import is_connected_to_internet, get_primary_screen_dimensions, resource_path,conver_bytes_to_tmp_path,gen_name_from_url,get_file_extension_from_url,isBundle
from utils.validators import validate_url_or_path, get_media_type,validate_tapeciarnia_url,is_tapeciarnia_redirect_url,extract_file_id_from_url
from utils.file_utils import cleanup_temp_marker
from utils.pathResolver import fast_resolve_tapeciarnia_redirect
from utils.singletons import get_config,get_language_controller
# Import models
from models.constants import RangeTypes,LoginPayload,WallpaperType,URIActions
# Import UI components
# from .dialogs import ShutdownProgressDialog



class TapeciarniaApp(QMainWindow):
    def __init__(self):
        logging.info("Initializing TapeciarniaApp")
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.x , self.y = get_primary_screen_dimensions()
        self.is_dowloading = False
        self.isLogin:bool = False # temporary

        # Initialize controllers
        logging.debug("Initializing controllers")
        self.controller = WallpaperController()
        self.controller.status_callback = self._set_status
        self.controller.video_success_callback = self.wallpaper_set_success
        self.controller.btn_update_callback = self._update_start_btn 
        self.scheduler = UnifiedWallpaperScheduler()
        self.language_controller = get_language_controller()
        self.scheduler.set_change_callback(self._apply_wallpaper_from_scheduler)
        # Load configuration
        logging.debug("Loading configuration")
        self.config = get_config()
        # Initial language setup
        logging.debug("Setting up initial language")
        self._set_lang()
        # connect to the language controller signals
        logging.debug("Connecting language change signal")
        self.language_controller.language_changed.connect(self._update_lang)
        self.ui.uploadArea.mousePressEvent = self.upload_area_mousePressEvent
        # remove focuse from email input textEdit
        self.ui.emailInput.clearFocus()
        self.ui.card.setFocus()
        # loing setup
        self.user_name:str|None = None
        # scheduler setup
        self.scheduler.status_callback = self._set_status
        # Enhanced drag & drop
        self.drag_drop_widget = EnhancedDragDropWidget(self)
        # Setup
        logging.debug("Setting up UI and application state")
        self._setup_ui()
        self._setup_tray()
        self._load_settings()
        self._setLogInState()
        # Custom message box
        logging.debug("Initializing custom message box")
        self.customMessageBox = CustomMessageBox(ButtonCollection(language_data=self.language_controller.lang))
        # ========================================================================

        logging.info("TapeciarniaApp initialization completed successfully")

    def _setLogInState(self):
        '''
        Hide email and password imput area. And toggle text on LohInBnt
        '''
        if self.isLogin:
            self.ui.emailInput.hide()
            self.ui.passwordInput.hide()
            self.ui.logInBnt.setText(self.language_controller.get("auth.logOutButton"))
        else:
            self.ui.emailInput.show()
            self.ui.passwordInput.show()
            self.ui.logInBnt.setText(self.language_controller.get("auth.logInButton"))

        self.update()


    def upload_area_mousePressEvent(self, event):
            """
            This is the overridden method that captures the click event.
            """
            # Call the base class implementation first (important)
            if self.drag_drop_widget.dropped_file_path:
                logging.debug("File already dropped, ignoring browse click")
                return
            
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


    def _update_lang(self):
        """Update UI language based on selected language"""
        self.current_lang =  self.language_controller.lang
        # 
        self.update_ui_language()
        self.drag_drop_widget.update_language()
        self._update_status_label_language()
        self.customMessageBox.update_language(self.current_lang)
        # restore status to empty
        self._set_status(self.language_controller.get("status.genaral.language_changed",default=f"Language change to {self.config.get_language()}").format(self.config.get_language())) #

    def _set_lang(self):
        logging.info("Eumarating all language options into combo box")
        self.language_controller.enumerate_languages(self.ui.langCombo)
        # Set initial language
        self.language_controller.setup_initial_language(self.ui.langCombo)
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
 
    # update status label on language change
    def _update_status_label_language(self):
        """Update status label text based on current status message and language"""
        self._set_status(self.language_controller.get("status.genaral.language_changed").format(self.config.get_language()))

    def _set_status(self, message: str):
        """Update status label and ensure it's visible"""
        logging.debug(f"Setting status: {message}")
        if hasattr(self.ui, "statusLabel"):
            self.ui.statusLabel.setVisible(True)
            self.ui.statusLabel.setText(message)

        if hasattr(self.ui, "bottomFrame"):
            self.ui.bottomFrame.setVisible(True)

    def on_shuffle_animated(self):

        """Shuffle through animated wallpapers - try online first, fallback to local"""
        logging.info("Shuffle animated triggered - trying online first")
        self.current_shuffle_type = 'animated'

        # Update button states
        self._set_status(self.language_controller.get("status.genaral.fetching_online_wallpaper")) #
        self._update_shuffle_button_states('animated')
        self.active_buttons(False)
        
        # stopping scheduler
        if self.scheduler.is_active():
            self._stop_scheduler()
        

        # Try to fetch online wallpaper
        fetch_online_url = Shuffler(animated=True)
        fetch_online_url.success.connect(lambda e: self.download_and_set_online_wallpaper(e,is_animated=True))
        fetch_online_url.failed.connect(lambda e: self._fallback_to_local_shuffle(is_animated=True,fallback_reason=e))
        fetch_online_url.run()




    def on_shuffle_wallpaper(self):

        self.is_dowloading = True
        """Shuffle through static wallpapers - try online first, fallback to local"""
        logging.info("Shuffle wallpaper triggered - trying online first")
        self.current_shuffle_type = 'wallpaper'
        
        # Update button states
        self._set_status(self.language_controller.get("status.genaral.fetching_online_wallpaper")) #
        self._update_shuffle_button_states('wallpaper')
        self.active_buttons(False)

        # stopping scheduler
        if self.scheduler.is_active():
            self._stop_scheduler()
        

        # Try to fetch online wallpaper
        animated = False
        fetch_online_url = Shuffler(animated=animated)
        fetch_online_url.success.connect(lambda e: self.download_and_set_online_wallpaper(e,is_animated=animated))
        fetch_online_url.failed.connect(lambda e: self._fallback_to_local_shuffle(is_animated=animated,fallback_reason=e))
        fetch_online_url.run()


    def _perform_reset(self):
        """Reset to default wallpaper WITHOUT confirmation but WITH success message"""
        logging.info("Performing reset without confirmation")
        self.controller.stop()
        self._stop_scheduler()
        self.active_buttons(True)
        # Reset enhanced state

        # reset scheduler state
        if self.config.get_scheduler_enabled():
            self.scheduler.reset()
            self._update_range_buttons_active(None)
            self._update_source_buttons_active(None)
        
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
            self.drag_drop_widget.reset_selection()
        
        # Clear URL input
        if hasattr(self.ui, 'urlInput'):
            self.ui.urlInput.clear()
        
        self._set_status(self.language_controller.get("status.genaral.reset_completed_successfully"))
        logging.info("Reset completed successfully")
        
        # Show success confirmation
        # QTimer.singleShot(0, self._show_reset_success_message)

    def _show_reset_success_message(self):
        """Show success confirmation dialog after reset"""
        logging.info("Showing reset success confirmation")
        
        # Create a custom dialog for better UX
        self.customMessageBox.information(
            None,
            self.language_controller.get("dialog.info.reset_success_title"),
            self.language_controller.get("dialog.info.reset_success_message")

        )
        
        # Show the dialog
        # success_dialog.exec()
        logging.info("Reset success confirmation shown")


    # # Rest of your existing methods remain the same...
    # def changeEvent(self, event):
    #     if event.type() == QEvent.WindowStateChange:
    #         if self.isMinimized() and not self.is_minimized_to_tray:
    #             logging.debug("Window minimize event detected, hiding to tray")
    #             event.ignore()
    #             self.hide_to_tray()
    #     super().changeEvent(event)

    def closeEvent(self, event):
        """
        Handle window close event - hide the window to tray instead of exiting
        """
        if isBundle():
            logging.info("Close event triggered, hiding to tray instead of exiting")
            self.hide()
            self.is_minimized_to_tray = True
            logging.debug("Window hidden to tray")
            event.ignore()
        else:
            logging.info("Close event triggered, performing full shutdown")
            self._perform_shutdown(event)

    def _perform_shutdown(self, event):
        """Perform shutdown with coordinated progress updates"""
        try:
            logging.info("Performing shutdown sequence")
            
            self.controller.stop()
            
            self._stop_scheduler()
            
            QTimer.singleShot(100, lambda: self._finalize_shutdown(event))
            
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
            
            # Don't try to use event if it's already deleted
            try:
                if event and hasattr(event, 'accept'):
                    event.accept()
            except RuntimeError:
                logging.debug("Close event already deleted, continuing shutdown")
            
            # Quit application
            QApplication.quit()
            
        except Exception as e:
            logging.error(f"Error finalizing shutdown: {e}", exc_info=True)
            # Force quit if graceful shutdown fails
            QApplication.quit()

    def hide_to_tray(self):
        logging.info("Hiding window to system tray")
        self.hide()
        if hasattr(self, 'tray'):
            self.tray.showMessage(
                self.language_controller.get("dialog.info.icon_tray_title"),
                self.language_controller.get("dialog.info.icon_tray_message"),
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
        logging.debug("Window restored from tray")

    def _open_tapeciarnia_website(self):
        """Open the Tapeciarnia website in the default browser"""
        logging.info("Opening Tapeciarnia website in default browser")
        webbrowser.open("https://tapeciarnia.pl")

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
        
        if hasattr(self.ui, "user_name_label"):
            self.ui.user_name_label.setVisible(False)
            self.ui.user_name_label.mousePressEvent = self._handel_mouse_press_username

        if hasattr(self.ui, "logoLabel"):
            self.ui.logoLabel.mousePressEvent = self._handel_mouse_press_logo
        
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
                # self._set_status(self.language_controller.get("status.genaral.opened_range_type_range_folder").format() folder")
                logging.info(f"Successfully opened folder: {folder_path}")
            else:
                # self._set_status(f"Failed to open {source_type} folder")
                logging.error(f"Failed to open folder: {folder_path}")
        else:
            logging.warning(f"Folder does not exist: {folder_path}")
            self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.folder_not_found_title"), 
                            self.language_controller.get("dialog.warning.file_not_found_message").format(source_type=source_type) + f"\n{folder_path}") #

    def on_range_double_clicked(self, range_type):
        """Handle double-click on range buttons to open corresponding folder"""
        logging.info(f"Double-click detected on range: {range_type}")
        folder_path = get_folder_for_range(range_type)
        
        if folder_path.exists():
            success = open_folder_in_explorer(folder_path)
            if success:
                self._set_status(self.language_controller.get("status.genaral.opened_range_type_range_folder").format(range_type=range_type)) #
                logging.info(f"Successfully opened folder: {folder_path}")
            else:
                self._set_status(self.language_controller.get("status.genaral.failed_to_open_range_type_folder").format(range_type=range_type)) #
                logging.error(f"Failed to open folder: {folder_path}")
        else:
            logging.warning(f"Folder does not exist: {folder_path}")
            self.customMessageBox.warning(self, "Folder Not Found", 
                            f"The {range_type} folder does not exist:\n{folder_path}") #

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
            self.ui.range_all_bnt.clicked.connect(lambda: self.on_range_changed(RangeTypes.ALL))
            self.ui.range_all_bnt.mouseDoubleClickEvent = lambda e: self.on_range_double_clicked(RangeTypes.ALL)
            logging.debug("Range all button connected")
        
        if hasattr(self.ui, "range_wallpaper_bnt"):
            self.ui.range_wallpaper_bnt.clicked.connect(lambda: self.on_range_changed(RangeTypes.STATIC))
            self.ui.range_wallpaper_bnt.mouseDoubleClickEvent = lambda e: self.on_range_double_clicked(RangeTypes.STATIC)
            logging.debug("Range wallpaper button connected")
        
        if hasattr(self.ui, "range_mp4_bnt"):
            self.ui.range_mp4_bnt.clicked.connect(lambda: self.on_range_changed(RangeTypes.ANIMATED))
            self.ui.range_mp4_bnt.mouseDoubleClickEvent = lambda e: self.on_range_double_clicked(RangeTypes.ANIMATED)
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
            self.ui.emailInput.returnPressed.connect(self.on_login_clicked)
            self.ui.passwordInput.returnPressed.connect(self.on_login_clicked)

            logging.debug("Login button connected")

        logging.debug("All UI controls bound successfully")

    def _update_scheduler_ui_state(self):
        """Show/hide interval, range, and start button based on scheduler state"""

        enabled = self.config.get_scheduler_enabled()

        logging.debug(f"Updating scheduler UI state: enabled={enabled}")
        logging.info(f"Toggling scheduler visibility: {enabled}")

        # ------------------------------------------------------------------
        if hasattr(self.ui, "enabledCheck"):
            self.ui.enabledCheck.setChecked(enabled)

        # Show/hide interval and range controls
        if hasattr(self.ui, "source_n_interval_frame"):
            self.ui.source_n_interval_frame.setVisible(enabled)
        if hasattr(self.ui, "range_frame"):
            self.ui.range_frame.setVisible(enabled)

        # Spacer logic
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
            # self.customMessageBox.warning(self, "Error", "No input field available in UI")
            self.ui.loadUrlButton.setDisabled(False)

            return
        
        url = self.ui.urlInput.text().strip()
        if not url:
            logging.warning("No URL/path provided for apply")
            self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.empty_url_field_title",""), self.language_controller.get("dialog.warning.empty_url_field_message","")) #
            self.ui.loadUrlButton.setDisabled(False)
            return
        
        logging.info(f"Applying input string: {url}")
        # validate if the url is from tapeciarnia.pl or not

        if url.endswith(('.jpg', '.jpeg', '.png', '.mp4', '.webm', '.avi', '.mkv', '.mov')):
            logging.info("Input detected as direct URL")
            self._apply_wallpaper_from_input_area(text=url)
        else:
            logging.info("Input detected as indirect URL")
            file_id,file_type = extract_file_id_from_url(url)
            if file_id and file_type:
                logging.info(f"Extracted file ID: {file_id}, type: {file_type} from URL")
                self.apply_wallpaper_from_uris(file_id,file_type,{"id":file_id})
            else:
                logging.warning("Failed to extract file ID from URL")
                self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.invalid_url_title",""), self.language_controller.get("dialog.warning.invalid_url_message","")) #


    def on_start_clicked(self):

        if not self.scheduler.is_active():
            """Start the scheduler with selected settings and random wallpaper"""
            logging.info("Start button clicked - starting scheduler with current settings")
            
            # Check if scheduler is enabled
            if hasattr(self.ui, 'enabledCheck') and not self.ui.enabledCheck.isChecked():
                logging.warning("Scheduler not enabled, enabling it first")
                self.ui.enabledCheck.setChecked(True)
            
            # Get interval from UI
            if hasattr(self.ui, 'interval_spinBox'):
                interval = self.ui.interval_spinBox.value()
            
            # Get current source and range
            source = self.scheduler.source
            # if not source:
            #     self.scheduler.source = source
            
            range_type = self.current_range


            if self.scheduler.source == str(SAVES_DIR):
                try:
                    self.config.set_scheduler_settings(enabled=True, source=source,interval=interval,range_type=range_type)
                    # Check if there are any files matching the current settings
                    logging.info(f"Checking for files with source: {source}, range: {range_type}")
                    available_files = self.scheduler._get_media_files()
                    
                    if not available_files:
                        # No files found for current settings - show error popup
                        logging.warning(f"No files found for source: {source}, range: {range_type}")
                        
                        # Determine the error message based on settings
                        if range_type == RangeTypes.ANIMATED:
                            error_msg = self.language_controller.get("dialog.warning.no_wallpaper_found_for_scheduler_messges.no_mp4")
                        elif range_type == RangeTypes.STATIC:
                            error_msg = self.language_controller.get("dialog.warning.no_wallpaper_found_for_scheduler_messges.no_wallpapers")
                        else:  # all
                            error_msg = self.language_controller.get("dialog.warning.no_wallpaper_found_for_scheduler_messges.all")
                        
                        self.customMessageBox.warning(
                            self,
                            self.language_controller.get("dialog.warning.no_wallpaper_found_for_scheduler_title"),
                            error_msg,

                        ) #
                        self._set_status(self.language_controller.get("status.genaral.scheduler_failed_no_matching_wallpapers")) #
                        return
                    
                    # Files available - start the scheduler
                    logging.info(f"{len(available_files)} files found for scheduler, starting...")
                    self.scheduler.start(source,range_type, interval)
                    # self.scheduler.online_worker.sendStopSignal.connect(self._stop_scheduler)
                    self._update_start_btn()

                
                except Exception as e:
                    logging.error(f"Failed to apply random wallpaper: {e}")
                    self._set_status(self.language_controller.get("status.genarel.scheduler_started_but_failed")) #
                    self.customMessageBox.warning(
                        self,
                        "Scheduler Started with Warning",
                        f"Scheduler started but there was an issue applying the first wallpaper:\n{str(e)}",
                        
                    ) # no need

                # # Apply a random wallpaper immediately from the available files
                # try:
                #     random_wallpaper = random.choice(available_files)
                #     logging.info(f"Applying random wallpaper: {random_wallpaper.name}")
                #     # self._apply_wallpaper_from_path(random_wallpaper)
                #     self._set_status(self.language_controller.get("status.genaral.scheduler_started").format(available_files=len(available_files),interval=interval)) #
                    

            elif self.scheduler.source == str(FAVS_DIR):
                self.config.set_scheduler_settings(enabled=True, source=source,interval=interval,range_type=range_type)

                self.scheduler.start(source,range_type, interval)
                self.scheduler.online_worker.sendStopSignal.connect(self._stop_scheduler)

                self._update_start_btn()

            elif self.scheduler.source == str(SUPER_WALLPAPER_DIR):
                self.config.set_scheduler_settings(enabled=True, source=source,interval=interval,range_type=range_type)

                self.scheduler.start(source,range_type, interval)
                self.scheduler.online_worker.sendStopSignal.connect(self._stop_scheduler)

                self._update_start_btn()

            else:
                self.customMessageBox.warning(
                    self,
                    self.language_controller.get("dialog.warning.sheduler_error_title"),
                    self.language_controller.get("dialog.warning.sheduler_error_message"),
                ) #
                logging.error("Scheduler start failed - invalid source")
                
        else:
            self._stop_scheduler()                

    def _stop_scheduler(self,msg:str=None):
        # logging.info("Stopping scheduler")
        self.config.set_scheduler_settings(enabled=True,source=self.scheduler.source,interval=self.scheduler.interval_minutes,range_type=self.scheduler.range_type)
        self.scheduler.stop()
        self._update_start_btn()
        if msg:
            self._set_status(msg)
        else:
            self._set_status(self.language_controller.get("status.genaral.scheduler_stopped")) #


    def _update_start_btn(self):
        if self.scheduler.is_active():
            self.ui.startButton.setText(self.language_controller.get("settings.stopButton"))
            self.ui.startButton.setProperty("class", "primary")
            self.ui.startButton.style().unpolish(self.ui.startButton)
            self.ui.startButton.style().polish(self.ui.startButton)
        
        else:
            self.ui.startButton.setText(self.language_controller.get("settings.startButton"))
            self.ui.startButton.setProperty("class", "ghost")
            self.ui.startButton.style().unpolish(self.ui.startButton)
            self.ui.startButton.style().polish(self.ui.startButton)
        

    
    def _get_source_display_name(self, source):
        """Get display name for source"""
        source_names = {
            str(FAVS_DIR): self.language_controller.get("settings.favoriteWallpapersButton"),
            str(SAVES_DIR): self.language_controller.get("settings.myCollectionButton"),
            str(SUPER_WALLPAPER_DIR):  self.language_controller.get("settings.superWallpaperButton")
        }
        return source_names.get(source, "Custom Source")

    def on_browse_clicked(self):
        """Browse web for wallpapers"""
        logging.info("Browse button clicked")
        webbrowser.open_new_tab("https://www.tapeciarnia.pl")
        logging.debug("Opening tapeciarnia")

    def _handle_browsed_file(self, file_path: str):
        """Handle browsed file with destination selection"""
        logging.info(f"Handling browsed file: {file_path}")
        
        if not os.path.exists(file_path):
            logging.error(f"Browsed file does not exist: {file_path}")
            self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.file_not_exist_title"), self.language_controller.get("dialog.warning.file_not_exist_message")) #
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
        # self.customMessageBox.information(self, self.language_controller.get("dialog.info.super_wallpaper_title"), self.language_controller.get("dialog.info.super_wallpaper_message") ) #
        # set scheduler source to FAVS_DIR
        logging.info("Super/Best Wallpapers source selected")
        self.scheduler.source = str(SUPER_WALLPAPER_DIR)
        # update source buttons active state (super wallpaper)
        self._update_source_buttons_active(self.scheduler.source)
        # update status
        self._set_status(self.language_controller.get("status.genaral.scheduler_set_for_super_collection")) #
        # updating range to wallpaper by default
        if not self.scheduler.range_type:
            self.active_ranges(RangeTypes.ALL)

    def on_favorite_wallpapers(self):
        if not self.isLogin:

            self.customMessageBox.information(
                self,
                self.language_controller.get("dialog.info.no_login_fvrt_title"),
                self.language_controller.get("dialog.info.no_login_fvrt_message"),
                
            ) #
            return
        
        else:
            # set scheduler source to FAVS_DIR
            logging.info("Favorite Wallpapers source selected")
            self.scheduler.source = str(FAVS_DIR)
            self.scheduler.set_api_url(self.config.get_frvt_wallpaper_url())
            # update source buttons active state (fvorites)
            self._update_source_buttons_active(self.scheduler.source)
            # update status
            self._set_status(self.language_controller.get("status.genaral.scheduler_set_for_favorite_collection")) #

            # updating range to wallpaper by default if no range is selected
            if not self.scheduler.range_type:
                self.active_ranges(RangeTypes.ALL)
    
    def _disable_other_range(self):
        '''
        Disable other range (all,MP4) when scheduler is set to online as online only give static images.

        '''
        self._update_range_buttons_active(RangeTypes.STATIC)
        self.ui.range_all_bnt.setEnabled(False)
        self.ui.range_mp4_bnt.setEnabled(False)
    
    def _enable_other_range(self):
        '''
        Disable other range (all,MP4) when scheduler is set to online as online only give static images.

        '''
        # self._update_range_buttons_active(RangeTypes.STATIC)
        self.ui.range_all_bnt.setEnabled(True)
        self.ui.range_mp4_bnt.setEnabled(True)
    



    def on_added_wallpapers(self):
        """My Collection source - includes ALL folders"""
        logging.info("My Collection source selected")
        
        # has_favorites = FAVS_DIR.exists() and any(FAVS_DIR.iterdir())
        has_saves = SAVES_DIR.exists() and any(SAVES_DIR.iterdir())
        
        if not (has_saves):
            logging.warning("Empty collection - no wallpapers found")
            self.customMessageBox.information(self, self.language_controller.get("dialog.info.collection_empty_title"),
                                    self.language_controller.get("dialog.info.collection_empty_message")) #
            return
        
        # Set scheduler source to SAVES_DIR
        self.scheduler.source = str(SAVES_DIR)
        self._update_source_buttons_active(self.scheduler.source)
        # updating range to all by default
        if not self.scheduler.range_type:
            self.active_ranges(RangeTypes.ALL)
        # upate status
        self._set_status(self.language_controller.get("status.genaral.scheduler_set_to_use_entire_collection")) #
        logging.info("Scheduler set to use entire collection")

    def get_range_button_text_by_type(self, range_type):
        """Get range button text by type"""
        range_texts = {
            RangeTypes.ALL: self.language_controller.get("settings.rangeAllButton"),
            RangeTypes.STATIC: self.language_controller.get("settings.rangeWallpaperButton"),
            RangeTypes.ANIMATED: self.language_controller.get("settings.rangeMp4Button"),
        }
        return range_texts.get(range_type, "Unknown Range")

    # Range selection
    def on_range_changed(self, range_type):
        """Handle range selection with validation"""
        logging.info(f"Range changed to: {range_type}")
        self.current_range = range_type
        self.scheduler.set_range(range_type)

        # Check if current source + range combination has files
        if self.scheduler.source == str(SAVES_DIR):
            available_files = self.scheduler._get_media_files()
            if not available_files:
                # Warn user but don't prevent the change
                logging.warning(f"No files found for source: {self.scheduler.source}, range: {self.get_range_button_text_by_type(range_type)}")
                self._set_status(self.language_controller.get("status.genaral.range").format(range_type=self.get_range_button_text_by_type(range_type))) #
            else:
                self._set_status(self.language_controller.get("status.genaral.range_with_file").format(self.get_range_button_text_by_type(range_type),len(available_files))) #
        else:
            self._set_status(self.language_controller.get("status.genaral.range_with_range_type").format(range_type=self.get_range_button_text_by_type(range_type))) #


        self.active_ranges(range_type=range_type)
        logging.debug(f"Range preference saved: {range_type}")

    def on_scheduler_toggled(self):
        """Handle scheduler enable/disable"""

        if self.scheduler.is_active():
            logging.info("Scheduler is active, toggle ignored")

            title = self.language_controller.get("dialog.info.scheduler_active_title")
            message = self.language_controller.get("dialog.info.scheduler_active_message")

            self.ui.enabledCheck.blockSignals(True)
            self.ui.enabledCheck.setChecked(True)
            self.ui.enabledCheck.blockSignals(False)

            self.customMessageBox.information(self, title, message)
            return

        # User clicked the checkbox
        isEnabled = self.ui.enabledCheck.isChecked()
        self.config.set_scheduler_enabled(isEnabled)

        # THIS was causing the second popup — now safe
        self._update_scheduler_ui_state()
        # update status
        if isEnabled:
            self._set_status(self.language_controller.get("status.genaral.scheduler_enabled")) #
        else:
            self._set_status(self.language_controller.get("status.genaral.scheduler_disabled")) #

    def _on_interval_changed(self, val):
        """Handle interval change"""
        logging.info(f"Interval changed to: {val} minutes")
        self.scheduler.interval_minutes = val
    
    def set_interval(self,interval:int):
        self.ui.interval_spinBox.setValue(interval)

    def update_ui_language(self):
        self.ui.emailInput.setPlaceholderText(f"{self.language_controller.get("auth.emailPlaceholder")}")
        self.ui.passwordInput.setPlaceholderText(f"{self.language_controller.get("auth.passwordPlaceholder")}")
        
        if self.isLogin:
            self.ui.logInBnt.setText(f"{self.language_controller.get("auth.logOutButton")}")
        else:
            self.ui.logInBnt.setText(f"{self.language_controller.get("auth.logInButton")}")
            
        if self.scheduler.is_active():
            self.ui.startButton.setText(f"{self.language_controller.get("settings.stopButton")}")
        else:
            self.ui.startButton.setText(f"{self.language_controller.get("settings.startButton")}")
            
        # main controls
        self.ui.randomAnimButton.setText(f" {self.language_controller.get("navigation.shuffleAnimatedButton")}")
        self.ui.randomButton.setText(f" {self.language_controller.get("navigation.shuffleWallpaperButton")}")
        self.ui.browseButton.setText(f" {self.language_controller.get("navigation.browseWallpapersButton")}")
        # uploadSection
        self.ui.add_file_label.setText(f" {self.language_controller.get("uploadSection.addFilesHeader")}")
        # self.ui.uploadText.setText(self.language_controller.get("uploadSection.dragDropInstruction")) 
        # self.ui.uploadSupported.setText(self.language_controller.get("uploadSection.supportedFormatsHint"))
        # url loader
        self.ui.url_loader_text_label.setText(f" {self.language_controller.get("uploadSection.imagesOrVideoURLHeader")}")
        self.ui.loadUrlButton.setText(f"{self.language_controller.get("uploadSection.loadButton")}")
        self.ui.url_helper_text_label.setText(f" {self.language_controller.get("uploadSection.urlHelperText")}")
        # settings
        self.ui.autoLabel.setText(f" {self.language_controller.get("settings.autoChangeHeader")}")
        self.ui.enabledCheck.setText(f" {self.language_controller.get("settings.enabledLabel")}")
        self.ui.inverval_lable.setText(f" {self.language_controller.get("settings.intervalLabel")}")
        self.ui.wallpaper_source_lable.setText(f" {self.language_controller.get("settings.wallpaperSourceLabel")}")
        self.ui.super_wallpaper_btn.setText(f" {self.language_controller.get("settings.superWallpaperButton")}")
        self.ui.fvrt_wallpapers_btn.setText(f" {self.language_controller.get("settings.favoriteWallpapersButton")}")
        self.ui.added_wallpaper_btn.setText(f" {self.language_controller.get("settings.myCollectionButton")}")
        self.ui.range_lable.setText(f" {self.language_controller.get("settings.rangeHeader")}")
        self.ui.range_all_bnt.setText(f" {self.language_controller.get("settings.rangeAllButton")}")
        self.ui.range_wallpaper_bnt.setText(f" {self.language_controller.get("settings.rangeWallpaperButton")}")
        self.ui.range_mp4_bnt.setText(f" {self.language_controller.get("settings.rangeMp4Button")}")
        self.ui.resetButton.setText(f" {self.language_controller.get("settings.resetButton")}")
        

    def active_buttons(self,enabled: bool):
        logging.debug(f"Toggleing buttons: {enabled}")
        self.ui.randomButton.setDisabled(not enabled)
        self.ui.randomAnimButton.setDisabled(not enabled)
        # self.ui.browseButton.setDisabled(not enabled)
        self.ui.loadUrlButton.setDisabled(not enabled)
        self.ui.logInBnt.setDisabled(not enabled)
        self.ui.resetButton.setDisabled(not enabled)
        self.ui.startButton.setDisabled(not enabled)
        self.ui.urlInput.clearFocus()


    def _apply_wallpaper_from_input_area(self, text: str):
        """Main method to apply wallpaper from URL or file path."""

        # stopping scheduler
        if self.scheduler.is_active():
            self._stop_scheduler()

        if not is_connected_to_internet:
            self._set_status(self.language_controller.get("status.genaral.unable_to_connect")) #
            return
        # Disable buttons during processing
        self.active_buttons(False)

        text = (text or "").strip()
        logging.info(f"Applying input: {text}")

        if not text:
            self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.invalid_path_title"), self.language_controller.get("dialog.warning.invalid_path_message")) #
            self.active_buttons(True)
            return
        


        validated = validate_url_or_path(text)
        if not validated:
            logging.warning(f"Input not recognized: {text}")
            self.customMessageBox.warning(self, "Error", f"Input not recognized: {text}") #
            self.active_buttons(True)

        if is_tapeciarnia_redirect_url(validated):
            logging.info(f"Tapeciarnia redirect url found: {validated}")
            validated = fast_resolve_tapeciarnia_redirect(validated)
            if not validated:
                self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.unsupported_url_title"),
                    self.language_controller.get("dialog.warning.unsupported_url_message")) #
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
                self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.unsupported_url_title"),
                    self.language_controller.get("dialog.warning.unsupported_url_message")) #
            self.active_buttons(True)
            
    
        else:
            logging.warning(f"Unsupported input type: {text}")
            media_type = get_media_type(validated)
            logging.debug(f"Detected media type for unsupported input: {media_type}")
            if media_type == "image":
                self._handle_remote_image(validated)
            elif media_type == "video":
                self._handle_remote_video(validated)
            else:
                self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.unsupported_url_title"),
                    self.language_controller.get("dialog.warning.unsupported_url_message")) #

            # -------- Fallback --------
            # logging.warning(f"Unsupported input type: {text}")
            # self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.unsupported_url_title"),
            #         self.language_controller.get("dialog.warning.unsupported_url_message")) #
            # self.active_buttons(True)


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
            self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.unsupported_file_title"),
                    self.language_controller.get("dialog.warning.unsupported_file_message")) #
    def _handle_remote_image(self, url: str,file_name:str=None):
        """Handle remote image download and application"""
        self._direct_image_downloader(url,file_name=file_name)


    def _direct_image_downloader(self, url: str,file_name:str = None):
        """
        Handle remote image download and application with progress window.
        This method manages the download of images from remote URLs and displays
        progress information to the user. It creates a separate thread to perform
        the download operation asynchronously, preventing UI blocking.
        Args:
            url (str): The complete URL of the remote image to download.
            file_name (str, optional): Custom file name for the downloaded image.
                If not provided, the file name will be derived from the URL or
                use a default naming scheme. Defaults to None.
        Raises:
            Exception: If the image download thread setup fails, the error is logged
                and displayed to the user via a critical message box.
        Signals Connected:
            - progress: Emits download progress percentage and status messages
            - error: Triggered if an error occurs during download
            - done: Triggered when the download completes successfully
        Note:
            The actual download operation runs in a separate ImageDownloadThread
            to maintain UI responsiveness. Status updates are displayed to the user
            via the _set_status method.
        """
        """Handle remote image download and application with progress window"""
        logging.info(f"Downloading remote image: {url}")
        
        try:
            # Create progress dialog for image download
            
            # Start download in a thread to show progress
            self.image_download_thread = ImageDownloadThread(url)
            self.image_download_thread.file_name = file_name
            
            self.image_download_thread.progress.connect(
                lambda percent, status: (
                    self._set_status(f"Downloading...{percent}% - {status}")
                )
            )
            self.image_download_thread.error.connect(self._on_download_error)
            self.image_download_thread.done.connect(self._on_image_download_done)
            
            self.image_download_thread.start()
            logging.info("Image download thread started")
            
        except Exception as e:
            logging.error(f"Image download setup failed: {e}", exc_info=True)
            self.customMessageBox.critical(self, "Error", f"Image download setup failed: {e}") #


    def _on_image_download_done(self, file_path: str):
        """Handle completion of image download (used in _handle_remote_image)"""
        logging.info(f"Image download completed: {file_path}")
        self._safe_process_file(Path(file_path))

    def _handle_remote_video(self, url: str,file_name:str=None):
        """Handle remote video downloads"""
        logging.info(f"Downloading remote video: {url}")
        # self._set_status(self.language_controller.get("status.genaral.downloading_video")) #
        cleanup_temp_marker()
        self._direct_video_downloader(url,file_name=file_name)


    def _direct_video_downloader(self, url: str,file_name:str=None):
        """
        Handle direct video file downloads (not YouTube/streaming services).
        This method sets up and initiates a download for video files from direct URLs.
        It creates a separate thread to manage the download process without blocking the UI.
        The download progress is tracked and displayed to the user via status messages.
        Parameters:
            url (str): The direct URL of the video file to download.
            file_name (str, optional): The desired filename for the downloaded video.
                If not provided, the filename is extracted from the URL.
                Defaults to None.
        Returns:
            None
        Raises:
            Exception: If the download setup fails, an error message is displayed
                to the user via a critical message box and logged.
        Note:
            - If no filename is provided, it is automatically sanitized and a .mp4
              extension is added if the extracted filename lacks a valid video extension.
            - The download runs asynchronously in a separate thread (VideoDownloadThread)
              to prevent UI blocking.
            - Download progress, errors, and completion are handled via signal connections.
        """
        """Handle direct video file downloads (not YouTube/streaming)"""
        try:
            logging.info(f"Starting direct video download: {url}")
            
            if not file_name:
                # Sanitize filename for the first time
                file_name = url.split("/")[-1]
                file_name = self._get_safe_filename(file_name)
                # check for extrantion of the filename at the end
                if not any(file_name.lower().endswith(ext) for ext in self.config.get_valid_video_extensions()):
                    file_name += ".mp4"  # default to .mp4 if no valid extension
                
            download_path = SAVES_DIR / file_name
            
            logging.info(f"Downloading to: {download_path}")
            
            # Start download in a thread to avoid blocking UI
            self.direct_download_thread = VideoDownloadThread(url, str(download_path))
            self.direct_download_thread.progress.connect(
                lambda percent, status: (
                    self._set_status(f"Downloading...{percent}% - {status}")
                )
            )
            self.direct_download_thread.error.connect(self._on_download_error)
            self.direct_download_thread.done.connect(self._on_direct_video_download_done)
            
            self.direct_download_thread.start()
            logging.info("Direct download thread started")
            
        except Exception as e:
            logging.error(f"Direct download setup failed: {e}", exc_info=True)
            self.customMessageBox.critical(self, "Error", f"Download setup failed: {e}") #

    def _on_direct_video_download_done(self, file_path: str):
        """Handle completion of direct video download - FIXED to not set wallpaper on failure"""
        logging.info(f"Direct download completed: {file_path}")
        self._safe_process_file(Path(file_path))



    def _get_safe_filename(self, raw_name):
        """Remove invalid characters for both Windows and Linux"""
        logging.debug(f"Sanitizing filename: {raw_name}")
        # Characters invalid on Windows: < > : " | ? *
        # Characters to avoid on Linux: / and null bytes
        invalid_chars = '=<>:"|?*/\0'
        for char in invalid_chars:
            raw_name = raw_name.replace(char, '_')
        logging.debug(f"Sanitized filename: {raw_name}")
        return raw_name


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
                self.customMessageBox.critical(
                    self,
                    "File Error", 
                    "The file is no longer available. Operation cancelled.",
                    
                ) #
                return
            
            self._process_download_file(downloaded_file_path)
            
        except Exception as e:
            logging.error(f"Error processing destination: {e}")
            self.customMessageBox.critical(
                self,
                "Error",
                f"Failed to process file: {str(e)}",
                
            ) #no need


    def _process_download_file(self, downloaded_file_path: Path):

        try:

            self._apply_wallpaper_from_path(downloaded_file_path)

            logging.info(f"Downloaded file saved to {SAVES_DIR}: {downloaded_file_path}")

        except Exception as e:
            logging.error(f"Failed to process downloaded file: {e}")
            logger.error(f"Failed to add file: {str(e)}")
            # self.customMessageBox.critical(self, "Error", f"Failed to add file: {str(e)}")


    def _apply_wallpaper_from_path(self, file_path: Path):
        """Apply wallpaper from file path - OPTIMIZED to avoid unnecessary stops"""
        logging.info(f"Applying wallpaper from path: {file_path}")
        new_is_video = file_path.suffix.lower() in self.config.get_valid_video_extensions()
        # time.sleep(0.5) # idk why bt this this a bug        
        if new_is_video:
            logging.debug("New wallpaper is animated")
            self._apply_video(str(file_path))
        else:
            logging.debug("New wallpaper is static")
            self._apply_image(str(file_path))

    def _apply_wallpaper_from_scheduler(self,file_path:Path=None,image_data:list[str,bytes]=None):
        # This method is only called by the scheduler to change the the wallpaper
        logging.info("Wallpaper change callback called from scheduler")
        if self.scheduler.source == str(SAVES_DIR):
            if file_path:
                logging.debug("Wallpaper change callback called from scheduler with source 'My collection'")
                self._apply_wallpaper_from_path(file_path=file_path)
                
        elif self.scheduler.source == str(FAVS_DIR):
            logging.debug("Wallpaper change callback called from scheduler with source 'Frvt'")
            if image_data:
                url = image_data.get("url")
                ext = get_file_extension_from_url(url)
                if ext == ".mp4":
                    path = conver_bytes_to_tmp_path(image_data.get("data"),ext=ext)
                    self.controller.start_video(path)

                elif ext == ".jpg":

                    path = conver_bytes_to_tmp_path(image_data.get("data"),ext=ext)
                    self.controller.start_image(path)
                
                else:
                    logging.critical("Invalide file type recived from sheduler. Wallpaper cannot be started")

                self._set_status(self.language_controller.get("status.genaral.image_applied").format(gen_name_from_url(image_data.get("url")))) #
                self._update_url_input(image_data.get("url"))

            else:
                logging.warning("No Image data recevied from scheduler")

        elif self.scheduler.source == str(SUPER_WALLPAPER_DIR):
            
            logging.debug("Wallpaper change callback called from scheduler with source 'Super collection'")
            if image_data:
                url = image_data.get("url")
                ext = get_file_extension_from_url(url)
                
                if ext == ".mp4":
                    path = conver_bytes_to_tmp_path(image_data.get("data"),ext=ext)
                    self.controller.start_video(path)

                elif ext == ".jpg":
                    path = conver_bytes_to_tmp_path(image_data.get("data"),ext=ext)
                    self.controller.start_image(path)
                else:
                    logging.critical("Invalide file type recived from sheduler. Wallpaper cannot be started")


                self._set_status(self.language_controller.get("status.genaral.image_applied").format(gen_name_from_url(image_data.get("url")))) #
                self._update_url_input(image_data.get("url"))

            else:
                logging.warning("No Image data recevied from scheduler")
        else:
            logging.error("Unknown source selected for sheduler!!")


    def wallpaper_set_success(self,**kw):
        # 
        #    
        video_path = kw.get("video_path","")
        success = kw.get("success")
        logging.debug(f"Video success callback called with {success}")
        if success:
            self.config.set_last_video(video_path)
            self._set_status(self.language_controller.get("status.genaral.playing_video").format(Path(video_path).name)) #
            self._update_url_input(video_path)
            logging.info(f"Video wallpaper applied successfully: {Path(video_path).name}")
            self.active_buttons(True)

        else:
            self._set_status(self.language_controller.get("status.genaral.failed_to_change_wallpaper")) #
            self.active_buttons(True)



    def _apply_video(self, video_path: str):
        """Apply video wallpaper"""
        try:
            # time.sleep(2)
            self.active_buttons(False)
            logging.info(f"Applying video wallpaper: {video_path}")
            self.controller.start_video(video_path)
        except Exception as e:
            self.active_buttons(True)
            logging.error(f"Failed to play video: {e}", exc_info=True)
            self.customMessageBox.critical(self, "Error", f"Failed to play video: {e}") #

    def _apply_image(self, image_path: str):
        """Apply image wallpaper with fade effect - FIXED for null pixmap"""
        try:
            self.active_buttons(False)
            logging.info(f"Applying image wallpaper: {image_path}")
            
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
            
            self._set_status(self.language_controller.get("status.genaral.image_applied").format(Path(image_path).name)) #

            self._update_url_input(image_path)
            logging.info(f"Image wallpaper applied: {Path(image_path).name}")
            self.active_buttons(True)
            
        except Exception as e:
            logging.error(f"Failed to apply image: {e}", exc_info=True)
            # Fallback to direct application without fade
            try:
                self.active_buttons(True)
                logging.info("Attempting direct image application without fade")
                self.controller.start_image(image_path)
                self.config.set_last_video(image_path)
                self._set_status(self.language_controller.get("status.genaral.image_applied").format(Path(image_path).name)) #
                self._update_url_input(image_path)
            except Exception as fallback_error:
                logging.error(f"Fallback image application also failed: {fallback_error}")
                self.customMessageBox.critical(self, "Error", f"Failed to apply image: {fallback_error}") #

    # Utility methods - FIXED: Proper media type separation
    def _get_media_files(self, media_type=RangeTypes.ALL):
        """Get media files based on current range and media type - FIXED LOGIC"""
        logging.debug(f"Getting media files - type: {media_type}, range: {self.current_range}")
        files = []
        
        # Define search folders based on CURRENT SOURCE (not just range)
        if hasattr(self, 'scheduler') and self.scheduler.source:
            if self.scheduler.source == str(FAVS_DIR):
                search_folders = [FAVS_DIR]
                source_type = "frvt"
            elif self.scheduler.source == str(SAVES_DIR):
                search_folders = [SAVES_DIR]
                source_type = "save"
            else:
                search_folders = [SAVES_DIR]
                source_type = "save"

        else:
            # Fallback to range-based selection
            search_folders = [SAVES_DIR]
            source_type = "range-based"
        
        logging.debug(f"Using source: {source_type}, folders: {[str(f) for f in search_folders]}")
        
        # Define extensions based on media type
        if media_type == RangeTypes.ANIMATED:
            extensions = tuple(self.config.get_valid_video_extensions())
        elif media_type == RangeTypes.STATIC:
            extensions = tuple(self.config.get_valid_image_extensions())
        else:
            extensions = tuple(self.config.get_all_valid_extensions())
        
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
        range_names = {RangeTypes.ALL: RangeTypes.ALL, RangeTypes.STATIC: RangeTypes.STATIC, RangeTypes.ANIMATED: RangeTypes.ANIMATED}
        display_name = range_names.get(self.current_range, RangeTypes.ALL)
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
            str(SUPER_WALLPAPER_DIR): getattr(self.ui, "super_wallpaper_btn", None),
            str(FAVS_DIR): getattr(self.ui, "fvrt_wallpapers_btn", None),
            str(SAVES_DIR): getattr(self.ui, "added_wallpaper_btn", None)
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
            RangeTypes.ALL: getattr(self.ui, "range_all_bnt", None),
            RangeTypes.STATIC: getattr(self.ui, "range_wallpaper_bnt", None),
            RangeTypes.ANIMATED: getattr(self.ui, "range_mp4_bnt", None)
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
        reply = self.customMessageBox.question(
            self,
            self.language_controller.get("dialog.qustions.confirm_reset_title"),
            self.language_controller.get("dialog.qustions.confirm_reset_dia"),
        )
        
        if reply == QMessageBox.YesRole:
            logging.info("User confirmed reset")
            self._perform_reset()
            self._set_status(self.language_controller.get("status.genaral.reset_completed_successfully"))
            
        else:
            logging.info("User cancelled reset")
            self._set_status(self.language_controller.get("status.genaral.reset_cancelled"))

    

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
                self.download_thread = VideoDownloadThread(url, str(download_path))
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
        self.active_buttons(True)        
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

            self._set_status(self.language_controller.get("status.genaral.online_wallpaper_set").format(Path(file_path).name)) #
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

    def _fallback_to_local_shuffle(self, is_animated: bool,fallback_reason:str=None):

        """
        Fallback to local shuffle when online fails
        """
        if fallback_reason:
            logging.warning(fallback_reason)

        logging.warning(f"Falling back to local shuffle for {'animated' if is_animated else 'static'}")
        
        # Show warning message
        self.customMessageBox.warning(
            self,
            self.language_controller.get("dialog.warning.offile_shuffle_title"),
            self.language_controller.get("dialog.warning.offile_shuffle_message")
        ) #
        
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
        video_files = self._get_media_files(media_type=RangeTypes.ANIMATED)
        
        if not video_files:
            self._set_status(self.language_controller.get("dialog.info.no_video_found_in_local_message"))
            logging.warning("No local animated wallpapers found")
            self.customMessageBox.information(
                self, 
                self.language_controller.get("dialog.info.no_video_found_in_local_title"),
                self.language_controller.get("dialog.info.no_video_found_in_local_message")
            ) #
            self._update_shuffle_button_states(None)
            self.current_shuffle_type = None
            return
        
        selected = random.choice(video_files)
        logging.info(f"Selected local animated wallpaper: {selected.name}")
        self._apply_wallpaper_from_path(selected)
        self._update_url_input(str(selected))
        self._update_shuffle_button_states(None)

        # enable the buttons
        self.active_buttons(True)


    def _perform_local_static_shuffle(self):
        """
        Perform local static shuffle (existing functionality)
        """
        logging.info("Performing local static shuffle")
        image_files = self._get_media_files(media_type=RangeTypes.STATIC)
        
        if not image_files:
            self._set_status(self.language_controller.get("dialog.info.no_wallpaper_found_in_local_message"))
            logging.warning("No local static wallpapers found")
            self.customMessageBox.information(
                self, 
                self.language_controller.get("dialog.info.no_wallpaper_found_in_local_title"),
                self.language_controller.get("dialog.info.no_wallpaper_found_in_local_message")
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
        self.active_buttons(True)


    def _on_download_error(self, error_msg: str):
        """Handle download errors (used in both image and video downloads)"""
        logging.error(f"Download error: {error_msg}")
        self.customMessageBox.critical(self, "Download Error", error_msg) #
        self._set_status(self.language_controller.get("status.genaral.download_failed")) #
        self.active_buttons(True)

    def active_ranges(self,range_type:RangeTypes):
        '''
        It actives the range (upadate the UI and set api accoding to the selected source)
        '''
        if range_type == RangeTypes.STATIC:
            self._active_range_wallpaper()
        elif range_type == RangeTypes.ANIMATED:
            self._active_range_mp4()
        elif range_type == RangeTypes.ALL:
            self._active_range_all()
        else:
            logging.error("")

    def _active_range_all(self):
        self._update_range_buttons_active(RangeTypes.ALL)
        self.config.set_range_preference(RangeTypes.ALL)
        self.scheduler.set_range(RangeTypes.ALL)
        if self.scheduler.source == str(SUPER_WALLPAPER_DIR) :
            self.scheduler.set_api_url(self.config.get_super_wallpaper_url(RangeTypes.ALL))

    def _active_range_wallpaper(self):
        self._update_range_buttons_active(RangeTypes.STATIC)
        self.config.set_range_preference(RangeTypes.STATIC)
        self.scheduler.set_range(RangeTypes.STATIC)
        if self.scheduler.source == str(SUPER_WALLPAPER_DIR) :
            self.scheduler.set_api_url(self.config.get_super_wallpaper_url(RangeTypes.STATIC))

    def _active_range_mp4(self):
        self._update_range_buttons_active(RangeTypes.ANIMATED)
        self.config.set_range_preference(RangeTypes.ANIMATED)
        self.scheduler.set_range(RangeTypes.ANIMATED)
        if self.scheduler.source == str(SUPER_WALLPAPER_DIR) :
            self.scheduler.set_api_url(self.config.get_super_wallpaper_url(RangeTypes.ANIMATED))

            


    # Settings management
    def _load_settings(self):
        """Load saved settings"""
        logging.info("Loading saved settings")
        # Load last video
        # last_video = self.config.get_last_video()
        # if last_video and hasattr(self.ui, "urlInput"):
        #     self.ui.urlInput.setText(last_video)
        #     logging.info(f"Loaded last video from config: {last_video}")

        # Load scheduler settings
        enabled ,source, interval, range_type = self.config.get_scheduler_settings()

        # Load range preference
        logging.info(f"loaded sheduler settings source: {source} interval:{interval} range:{range_type}")
        self.scheduler.set_range(range_type)
        self._update_range_buttons_active(range_type)
        self.current_range = range_type
        # Load interval and enabled state
        enabled = self.config.get_scheduler_enabled()
        self.ui.enabledCheck.setChecked(enabled)
    
        self.scheduler.interval_minutes = interval
        self.scheduler.range_type = range_type
        self.scheduler.source = source

        if hasattr(self.ui, "interval_spinBox"):
            self.ui.interval_spinBox.setValue(interval)

        # if hasattr(self.ui, "enabledCheck"):
        #     self.ui.enabledCheck.setChecked(True)

        # souce can be none or path

        if source != None:
            # Set the collection button
            if source == str(SAVES_DIR):
                self._update_source_buttons_active(source)

            elif source == str(SUPER_WALLPAPER_DIR):
                # 
                self.scheduler.source = str(SUPER_WALLPAPER_DIR)
                self._update_source_buttons_active(source)
                # 
                if not range_type:
                    self._update_range_buttons_active(RangeTypes.ALL)
                    self.scheduler.set_range(RangeTypes.ALL)
                    range_type = RangeTypes.ALL
                    self.scheduler.set_api_url(self.config.get_super_wallpaper_url(RangeTypes.ALL))
                else:
                    self._update_range_buttons_active(range_type)
                    self.scheduler.set_range(range_type)
                    self.scheduler.set_api_url(self.config.get_super_wallpaper_url(range_type))


            elif source == str(FAVS_DIR):
                if self.isLogin:
                    self._update_source_buttons_active(source)
                    # self.scheduler.set_api_url(self.config.set_fvrt_wallpaper_url(self.user_name))
                else:
                    self.scheduler.source = str(SUPER_WALLPAPER_DIR)
                    self._update_source_buttons_active(self.scheduler.source)
                    self.active_ranges(RangeTypes.ALL)
                    self.set_interval(5)

            else:
                logger.warning(f"Unknown scheduler source: {source}, defaulting to None")
                self._update_source_buttons_active(None)
                
        else:
            # set the source to super range all interval to 5 min
            self.scheduler.source = str(SUPER_WALLPAPER_DIR)
            self._update_source_buttons_active(self.scheduler.source)
            self.active_ranges(RangeTypes.ALL)
            self.scheduler.set_api_url(self.config.get_super_wallpaper_url(RangeTypes.ALL))
            self.set_interval(5)
            logging.info("No scheduler source set, changing to default (source: super range: all interval: 5 min)")
            
        
        logging.info(f"Loaded scheduler settings - source: {source}, range: {range_type}, interval: {interval}, enabled: {enabled}")
        
        # Update UI state based on scheduler
        self._update_scheduler_ui_state()
        # load start button state
        self._update_start_btn()
        logging.info(f"Settings loaded successfully")

    # System tray
    def _setup_tray(self):
        logging.debug("Setting up system tray")
        # Don't quit when last window is closed
        QApplication.setQuitOnLastWindowClosed(False)
        
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logging.error("System tray is not available on this system")
            self.customMessageBox.critical(None, self.language_controller.get("dialog.critical.sytsem_tray_unavailable_title"), self.language_controller.get("dialog.critical.sytsem_tray_unavailable_message")) #
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

        open_tapeciarnia_website_action = QAction("Open Tapeciarnia", self)
        open_tapeciarnia_website_action.triggered.connect(self._open_tapeciarnia_website)

        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_from_tray)
        
        hide_action = QAction("Hide to Tray", self)
        hide_action.triggered.connect(self.hide_to_tray)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._exit_app)

        shuffle_static_action = QAction("Shuffle Static Wallpaper", self)
        shuffle_static_action.triggered.connect(self._perform_local_static_shuffle)

        shuffle_animated_action = QAction("Shuffle Animated Wallpaper", self)
        shuffle_animated_action.triggered.connect(self._perform_local_animated_shuffle)

        reset_action = QAction("Reset to Default Wallpaper", self)
        reset_action.triggered.connect(self._perform_reset_with_confirmation)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(open_tapeciarnia_website_action)
        # tray_menu.addAction(hide_action)
        tray_menu.addAction(shuffle_static_action)
        tray_menu.addAction(shuffle_animated_action)
        tray_menu.addSeparator()
        tray_menu.addAction(reset_action)
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
                url = self.config.get_loging_url()
                
                payload = LoginPayload(username=email,password=password,language=self.config.get_language()).payload()
                logging.debug(f"Login payload: {payload}")
                login = LoginWorker(url=url, payload=payload,method="GET")
                login.success.connect(self._on_login_success)
                login.failed.connect(lambda e: self._on_login_failed(data=e,login_worker=login))
                self._set_status(self.language_controller.get("status.genaral.logging_in")) #
                login.start()

            else:
                self._set_status(self.language_controller.get("status.genaral.invalid_credential")) #
                self.ui.logInBnt.setEnabled(True)  
                self.customMessageBox.information(
                    self,
                    self.language_controller.get("dialog.info.invalide_login_info_title"),
                    self.language_controller.get("dialog.info.invalide_login_info_message"),
                ) #

        else:
            self.handle_log_out()

    
    def _on_login_success(self,data:dict):
        self.ui.logInBnt.setEnabled(True)
        if data.get("is_ok") == True:
            # made username globle to make it available for future user
            self.user_name:str = data.get("login","Unkonw")
            self.handle_username()
            self.ui.user_name_label.setText(self.user_name)
            self.isLogin = True
            self._setLogInState()
            self.config.set_login_status(self.isLogin)
            

            self.ui.passwordInput.clear()
            self.ui.emailInput.clear()

            self.config.set_login_key(data.get("key"))
            self.config.set_login(data.get("login"))
            self._set_status(self.language_controller.get("status.genaral.login_successfull")) #
            self.customMessageBox.information(
                self,
                self.language_controller.get("dialog.info.login_successfull_title"),
                f"{self.language_controller.get("dialog.info.login_successfull_message")} {self.user_name}",
                # str(data),
            ) #
            logging.info("Login successfull")
            self.config.set_fvrt_wallpaper_url(user_name=self.user_name)
            self.scheduler.set_api_url(self.config.get_frvt_wallpaper_url())


            # hide the input areas and change the text on log in bnt to log out
        
        else:
            self._set_status(self.language_controller.get("status.genaral.login_failed")) #
            self.customMessageBox.information(
                self,
                self.language_controller.get("dialog.info.login_failed_title"),
                self.language_controller.get("dialog.info.login_failed_message"),
            ) #
            logging.info("Login failed")

    

    
    def _on_login_failed(self,data,login_worker:LoginWorker):
        self.ui.logInBnt.setEnabled(True)
        self.customMessageBox.information(
            self,
            "Log in faild",
            str(data),

        ) #
        logging.info("Logging failed")
        login_worker.stop()
        self._set_status(self.language_controller.get("status.genaral.login_failed")) #
        logging.warning(f"Logging in failed: {data}")

    def handle_log_out(self):
        # reset username lable
        self.user_name = None
        self.handle_username()
        # -------------------------
        self.ui.logInBnt.setEnabled(True)
        self.isLogin = False
        self.config.set_login_status(self.isLogin)
        self.config.clear_session()
        self._setLogInState()
        self.ui.urlInput.clear()
        self._set_status(self.language_controller.get("status.genaral.logout_successfull")) #
        self.ui.passwordInput.clear()

        if self.scheduler.is_active() and self.scheduler.source == str(FAVS_DIR):
            self._stop_scheduler()
            logging.info("User logged out successfully")    
            # Switch source to SAVES_DIR
            self.scheduler.source = str(SAVES_DIR)
            self._update_source_buttons_active(str(SAVES_DIR))
            # reset range to all
            self.scheduler.range_type = RangeTypes.ALL
            self._update_range_buttons_active(RangeTypes.ALL)
            self.config.set_scheduler_settings(enabled=True,source=self.scheduler.source,interval=self.scheduler.interval_minutes,range_type=self.scheduler.range_type)
            


    def _handel_mouse_press_username(self,e):
        if self.user_name:
            webbrowser.open_new_tab(f"https://www.tapeciarnia.pl/user_{self.user_name}")
    def _handel_mouse_press_logo(self,e):
        webbrowser.open_new_tab(f"https://www.tapeciarnia.pl")

    def handle_username(self) -> None:
        if self.user_name:
            self.ui.user_name_label.setVisible(True)
            self.ui.user_name_label.setText(self.user_name)
            
        else:
            self.ui.user_name_label.setVisible(False)



    def _exit_app(self, event):
        """Properly quit the application from tray menu with confirmation and progress"""
        logging.info("Exit from tray menu triggered")

        reply = self.customMessageBox.question(
            self,
            self.language_controller.get("dialog.qustions.confirm_exit_title"),
            self.language_controller.get("dialog.qustions.confirm_exit_dialog"),
        )

        if reply == QMessageBox.YesRole:
            logging.info("User confirmed exit")
            self._perform_shutdown(event)
            QApplication.quit()

        elif reply == QMessageBox.NoRole:
            logging.info("User chose No – do nothing")

        elif reply == QMessageBox.RejectRole:
            logging.info("User cancelled exit")
        
        else:
            logging.warning(f"Unknown response from exit confirmation dialog: {reply}")

    def apply_wallpaper_from_uris(self,url:str,file_type:WallpaperType,params:dict):
        """Main method to apply wallpaper from URI."""

        # stopping scheduler
        if self.scheduler.is_active():
            self._stop_scheduler()

        if not is_connected_to_internet:
            self._set_status(self.language_controller.get("status.genaral.unable_to_connect")) #
            return
        # Disable buttons during processing
        self.active_buttons(False)

        url = (url or "").strip()
        logging.info(f"Applying command: {url}")

        if not url:
            self.customMessageBox.warning(self, self.language_controller.get("dialog.warning.invalid_path_title"), self.language_controller.get("dialog.warning.invalid_path_message")) #
            self.active_buttons(True)
            return
        
        # -------- Handle Remote URL --------
        if not validate_tapeciarnia_url(url):
            logging.error(f"Invalid Tapeciarnia URL: {url}")
            return
            
        
        if file_type == WallpaperType.STATIC:

            self._handle_remote_image(url,file_name=f"{params.get('id', time.time())}.jpg")


        elif file_type == WallpaperType.ANIMATED:

            self._handle_remote_video(url,file_name=f"{params.get('id', time.time())}.mp4")



    def handle_startup_uri(self, action, params):
            """
            Processes the URI command received upon application launch, handling both
            standard (setwallpaper) and custom (set_url_default, mp4_url ,id) formats.
            
            Args:
                action (str): The primary command (e.g., 'setwallpaper', 'mp4_url').
                params (dict): Dictionary of query parameters (must contain 'url' for most actions).
            """
            
            logging.info(f"Handling URI. Action: {action}, Params: {params}")

            if action not in URIActions.allowed():
                logging.warning(f"Unsupported URI action received: {action}")
                return # Ignore unsupported actions

            # If the app is not hidden in icon tray, show the main window to indicate action processing
            if self.isVisible():
                self.show()
                self.raise_()
                self.activateWindow()
                
            # pop up a notification to inform user about the received command if the app is already hidden in icon tray
            if not self.isVisible() and hasattr(self, 'tray'):
                self.tray.showMessage(
                    self.language_controller.get("appName"),
                    self.language_controller.get("status.genaral.downloading_wallpaper"),
                    QSystemTrayIcon.Information,
                    1500
                )


            # Check for the required 'url' parameter for most actions
            wallpaper_url = params.get('url')
        

            if action == URIActions.ID.value:
                
                image_id = params.get('id')
                if image_id: 

                    wallpaper_url = self.config.get_uri_image_url().format(wallpaper_id=image_id)


                    logging.info(f"Executing default set_url_default command for URL: {wallpaper_url}")
                    
                    confirmed = True 
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
                            self._set_status(self.language_controller.get("status.genaral.applying_wallpaper_from_URI")) #
                            self.apply_wallpaper_from_uris(wallpaper_url,file_type=WallpaperType.STATIC,params=params)
                        except Exception as e:
                            logging.error(f"Failed to apply wallpaper from URI: {e}", exc_info=True)
                            # self.customMessageBox.critical(self, "Error", f"Failed to apply wallpaper: {e}")
                    else:
                        self._set_status(self.language_controller.get("status.genaral.wallpaper_cancelled_by_user")) #
                        
                else:
                    logging.error("id action received, but 'id' parameter is missing.")
                    # self.customMessageBox.warning(self, "URI Error", "The 'set_url_default' command is missing the required URL parameter.")
            
            elif action == URIActions.MP4_ID.value:
                image_id = params.get('id')
                if image_id: 

                    wallpaper_url = self.config.get_uri_video_url().format(wallpaper_id=image_id)


                    logging.info(f"Executing default set_url_default command for URL: {wallpaper_url}")
                    
                    confirmed = True 
                    self.last_uri_command = {
                        "action": action,
                        "url": wallpaper_url,
                        "confirmed": confirmed
                    }
                    logging.info(f"URI command confirmation stored: {self.last_uri_command}")
                    
                    # Act on user's choice
                    if confirmed:
                        try:
                            self.ui.urlInput.setText(f"tapeciarnia:id-mp4/{image_id}")
                            self._set_status(self.language_controller.get("status.genaral.applying_wallpaper_from_URI")) #
                            self.apply_wallpaper_from_uris(wallpaper_url,file_type=WallpaperType.ANIMATED,params=params)
                        except Exception as e:
                            logging.error(f"Failed to apply wallpaper from URI: {e}", exc_info=True)
                            # self.customMessageBox.critical(self, "Error", f"Failed to apply wallpaper: {e}")
                    else:
                        self._set_status(self.language_controller.get("status.genaral.wallpaper_cancelled_by_user")) #
                        
                else:
                    logging.error("mp4_id action received, but 'id' parameter is missing.")
                    # self.customMessageBox.warning(self, "URI Error", "The 'set_url_default' command is missing the required URL parameter.")

            else:
                logging.warning(f"Unknown URI action received: {action}")
                # self.customMessageBox.warning(self, "URI Error", f"Unknown command: '{action}'.")