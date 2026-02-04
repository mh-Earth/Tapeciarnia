import time
import os
from pathlib import Path
import logging

from PySide6.QtCore import QThread, Signal

from utils.path_utils import SAVES_DIR
from utils.singletons import get_language_controller
logger = logging.getLogger()



class VideoDownloadThread(QThread):
    progress = Signal(float, str)   # percent, status message
    done = Signal(str)              # path to downloaded file
    error = Signal(str)

    def __init__(self, url: str, file_path: str, parent=None):
        logging.info(f"Initializing VideoDownloadThread for URL: {url}")
        super().__init__(parent)
        self.url = url
        self.file_path = file_path
        self._cancelled = False
        self.traslator = get_language_controller()
        self.file_name = None
    
    # prevent running more then one intance of this class 

    def run(self):
        try:
            import requests
            logging.info(f"Starting direct download: {self.url} -> {self.file_path}")
            
            self.progress.emit(0, self.traslator.get("status.genaral.connecting_to_server"))
            
            # Stream download with progress
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            self.progress.emit(0, f"Downloading... (0%)")
            
            with open(self.file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancelled:
                        logging.info("Download cancelled by user")
                        if os.path.exists(self.file_path):
                            os.remove(self.file_path)
                        return
                    
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded_size / total_size) * 100
                            mb_downloaded = downloaded_size / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            
                            status = f"{self.traslator.get(('status.genaral.downloading_wallpaper'))} {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)"
                            self.progress.emit(percent, status)
                        else:
                            status = f"{downloaded_size / (1024 * 1024):.1f} MB"
                            self.progress.emit(0, status)
            
            # Verify download
            if os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
                self.progress.emit(100, "")
                logging.info(f"Direct download completed successfully: {self.file_path}")
                self.done.emit(self.file_path)
            else:
                error_msg = "Downloaded file is empty or missing"
                logging.error(error_msg)
                self.error.emit(error_msg)
                
        except Exception as e:
            error_msg = f"Direct download failed: {str(e)}"
            logging.error(error_msg, exc_info=True)
            
            # Clean up partial download
            if os.path.exists(self.file_path):
                try:
                    os.remove(self.file_path)
                except:
                    pass
                    
            self.error.emit(error_msg)

    def cancel(self):
        """Cancel the download"""
        self._cancelled = True
        logging.info("Download cancellation requested")


class ImageDownloadThread(QThread):
    progress = Signal(float, str)   # percent, status message
    done = Signal(str)              # path to downloaded file
    error = Signal(str)

    def __init__(self, url: str, download_path: str = None, parent=None):
        logging.info(f"Initializing ImageDownloadThread for URL: {url}")
        super().__init__(parent)
        self.url = url
        self.download_path = download_path
        self._cancelled = False
        self.traslator = get_language_controller()
        self.file_name:str = None
        self.image_id:int = None

    def run(self):
        try:
            import requests
            from urllib.parse import urlparse
            logging.info(f"Starting image download: {self.url}")
            
            self.progress.emit(0, self.traslator.get("status.genaral.connecting_to_server"))
            
            # Determine download path
            if self.download_path:
                download_path = Path(self.download_path)
            else:
                if not self.file_name:
                    # Get filename from URL
                    parsed_url = urlparse(self.url)
                    filename = os.path.basename(parsed_url.path)
                    if not filename or '.' not in filename:
                        filename = f"image_{int(time.time())}.jpeg"
                else:
                    filename = self.file_name
                # Sanitize filename
                filename = self._get_safe_filename(filename)
                download_path = SAVES_DIR / filename
            
            # Ensure destination directory exists
            download_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Stream download with progress
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            self.progress.emit(0, f"{self.traslator.get('status.genaral.downloading_wallpaper')}... (0%)")
            
            with open(download_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancelled:
                        logging.info("Image download cancelled by user")
                        if os.path.exists(download_path):
                            os.remove(download_path)
                        return
                    
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded_size / total_size) * 100
                            mb_downloaded = downloaded_size / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            
                            status = f"{self.traslator.get(('status.genaral.downloading_wallpaper'))} {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)"
                            self.progress.emit(percent, status)
                            
                        else:
                            status = f"{downloaded_size / 1024:.1f} KB"
                            self.progress.emit(0, status)
            
            # Verify download
            if os.path.exists(download_path) and os.path.getsize(download_path) > 0:
                # self.progress.emit(100, "Image download completed!")
                logging.info(f"Image download completed successfully: {download_path}")
                self.done.emit(str(download_path))
            else:
                error_msg = "Downloaded image file is empty or missing"
                logging.error(error_msg)
                self.error.emit(error_msg)
                
        except Exception as e:
            error_msg = f"Image download failed: {str(e)}"
            logging.error(error_msg, exc_info=True)
            
            # Clean up partial download
            if 'download_path' in locals() and os.path.exists(download_path):
                try:
                    os.remove(download_path)
                except:
                    pass
                    
            self.error.emit(error_msg)

    def _get_safe_filename(self, filename):
        """Remove invalid characters for both Windows and Linux"""
        invalid_chars = '<>:"|?*/\0'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename

    def cancel(self):
        """Cancel the download"""
        self._cancelled = True
        logging.info("Image download cancellation requested")
