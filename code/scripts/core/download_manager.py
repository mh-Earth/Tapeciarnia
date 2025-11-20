import time
import os
import platform
import yt_dlp
from pathlib import Path
from typing import Optional
import logging

from PySide6.QtCore import QThread, Signal

from utils.path_utils import SAVES_DIR

logger = logging.getLogger()


class DownloaderThread(QThread):
    progress = Signal(float, str)   # percent, status message
    done = Signal(str)              # path to downloaded file
    error = Signal(str)

    def __init__(self, url: str, parent=None):
        logger.info(f"Initializing DownloaderThread for URL: {url}")
        super().__init__(parent)
        self.url = url
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure directories exist and are writable on both platforms"""
        logger.debug("Ensuring video directory exists and is writable")
        try:
            SAVES_DIR.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Video directory ensured: {SAVES_DIR}")
            
            # On Linux, ensure proper permissions
            if platform.system() != "Windows":
                try:
                    os.chmod(SAVES_DIR, 0o755)
                    logger.debug("Set directory permissions on Linux")
                except Exception as e:
                    logger.warning(f"Could not set directory permissions: {e}")
                    # Permission changes might fail, but that's usually OK
                    
        except Exception as e:
            logger.error(f"Directory setup failed: {e}", exc_info=True)
            self.error.emit(f"Directory setup failed: {e}")

    def run(self):
        """Main download thread with improved error handling"""
        logging.info(f"Starting download thread for URL: {self.url}")
        
        try:
            # Configure yt-dlp with better error handling
            ydl_opts = {
                'outtmpl': str(SAVES_DIR / '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'noplaylist': True,
                'continuedl': True,
                'noprogress': True,  # We handle progress ourselves
                'nooverwrites': True,
                'writethumbnail': False,
                'ignoreerrors': False,  # Don't ignore errors
                'socket_timeout': 30,
                'retries': 3,
                'restrictfilenames': True,  # Restrict to safe filenames
            }
            
            # Custom progress hook
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d and d['total_bytes']:
                        percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                        speed = d.get('speed', 0)
                        speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "Unknown speed"
                        status = f"Downloading... {percent:.1f}% ({speed_str})"
                        self.progress.emit(percent, status)
                    else:
                        status = f"Downloading... {d.get('_percent_str', '0%')}"
                        self.progress.emit(0, status)
                
                elif d['status'] == 'finished':
                    self.progress.emit(100, "Download completed! Processing...")
                    logging.info(f"Download finished: {d.get('filename', 'Unknown')}")
                
                elif d['status'] == 'error':
                    logging.error(f"Download error in progress hook: {d}")
                    self.progress.emit(0, f"Error: {d.get('error', 'Unknown error')}")
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logging.info("Starting yt-dlp download")
                self.progress.emit(0, "Starting download...")
                
                # Extract info first to validate
                info = ydl.extract_info(self.url, download=False)
                if not info:
                    raise Exception("Could not extract video information")
                
                logging.info(f"Video info extracted: {info.get('title', 'Unknown')}")
                self.progress.emit(5, f"Preparing: {info.get('title', 'Video')}")
                
                # Start download
                result = ydl.download([self.url])
                logging.info(f"Download process completed with result: {result}")
                
                # Find the actual downloaded file
                downloaded_file = self._find_downloaded_file(info.get('title'))
                if downloaded_file and downloaded_file.exists():
                    self.progress.emit(100, "Download completed successfully!")
                    logging.info(f"Download successful: {downloaded_file}")
                    self.done.emit(str(downloaded_file))
                else:
                    raise Exception("Downloaded file not found after completion")
                    
        except yt_dlp.utils.DownloadError as e:
            error_msg = f"Download failed: {str(e)}"
            logging.error(error_msg)
            self.error.emit(error_msg)
        except yt_dlp.utils.ExtractorError as e:
            error_msg = f"Extraction failed: {str(e)}"
            logging.error(error_msg)
            self.error.emit(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
        finally:
            logging.info("Download thread finished")

    def _find_downloaded_file(self, title):
        """Find the actual downloaded file after completion"""
        if not title:
            return None
        
        # Look for files that match the title pattern
        possible_patterns = [
            f"{title}.mp4",
            f"{title}.mkv", 
            f"{title}.webm",
            f"{title}.*"
        ]
        
        for pattern in possible_patterns:
            for file_path in SAVES_DIR.glob(pattern):
                if file_path.exists() and file_path.stat().st_size > 0:
                    logging.info(f"Found downloaded file: {file_path}")
                    return file_path
        
        # If no exact match, look for recent files in download directory
        recent_files = sorted(SAVES_DIR.glob("*"), key=os.path.getmtime, reverse=True)
        for file_path in recent_files[:5]:  # Check 5 most recent files
            if file_path.exists() and file_path.stat().st_size > 0:
                logging.info(f"Found recent file as download: {file_path}")
                return file_path
        
        logging.warning("No downloaded file found")
        return 
    

class DirectDownloadThread(QThread):
    progress = Signal(float, str)   # percent, status message
    done = Signal(str)              # path to downloaded file
    error = Signal(str)

    def __init__(self, url: str, file_path: str, parent=None):
        logging.info(f"Initializing DirectDownloadThread for URL: {url}")
        super().__init__(parent)
        self.url = url
        self.file_path = file_path
        self._cancelled = False
    
    # prevent running more then one intance of this class 

    def run(self):
        try:
            import requests
            logging.info(f"Starting direct download: {self.url} -> {self.file_path}")
            
            self.progress.emit(0, "Connecting...")
            
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
                            
                            status = f"Downloading... {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)"
                            self.progress.emit(percent, status)
                        else:
                            status = f"Downloading... {downloaded_size / (1024 * 1024):.1f} MB"
                            self.progress.emit(0, status)
            
            # Verify download
            if os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
                self.progress.emit(100, "Download completed!")
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

    def run(self):
        try:
            import requests
            from urllib.parse import urlparse
            logging.info(f"Starting image download: {self.url}")
            
            self.progress.emit(0, "Connecting to image source...")
            
            # Determine download path
            if self.download_path:
                download_path = Path(self.download_path)
            else:
                # Get filename from URL
                parsed_url = urlparse(self.url)
                filename = os.path.basename(parsed_url.path)
                if not filename or '.' not in filename:
                    filename = f"image_{int(time.time())}.jpg"
                
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
            
            self.progress.emit(0, f"Downloading image... (0%)")
            
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
                            status = f"Downloading image... {percent:.1f}%"
                            self.progress.emit(percent, status)
                        else:
                            status = f"Downloading image... {downloaded_size / 1024:.1f} KB"
                            self.progress.emit(0, status)
            
            # Verify download
            if os.path.exists(download_path) and os.path.getsize(download_path) > 0:
                self.progress.emit(100, "Image download completed!")
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
