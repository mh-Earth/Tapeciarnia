import shutil
import requests
import re
import logging
from pathlib import Path
from typing import Optional

from .path_utils import SAVES_DIR, TMP_DOWNLOAD_FILE



def download_image(url: str) -> str:
    """Download image from URL and return local path"""
    logging.info(f"Starting image download from: {url}")
    
    try:
        logging.debug("Making HTTP GET request with streaming")
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        logging.debug(f"HTTP request successful - status: {r.status_code}, content-type: {r.headers.get('content-type', 'unknown')}")
        
        # Determine file extension
        ext = Path(url).suffix 
        if not ext or ext.lower() not in ('.jpg', '.jpeg', '.png',  '.gif'):
            ext = '.jpg'
            logging.debug(f"No valid extension in URL, defaulting to: {ext}")
        else:
            logging.debug(f"Using extension from URL: {ext}")
        
        # Create safe filename
        original_stem = Path(url).stem
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", original_stem)[:60]
        dest = SAVES_DIR / f"{safe}{ext}"
        logging.debug(f"Original filename: {original_stem}, Safe filename: {safe}{ext}")
        
        # Ensure directory exists
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        logging.debug(f"Ensured directory exists: {SAVES_DIR}")
        
        # Download and save file
        file_size = 0
        chunk_count = 0
        logging.info(f"Downloading image to: {dest}")
        
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
                    file_size += len(chunk)
                    chunk_count += 1
                    
                    # Log progress for large files
                    if chunk_count % 100 == 0:  # Log every ~800KB
                        logging.debug(f"Download progress: {file_size} bytes received, {chunk_count} chunks")
        
        logging.info(f"Image download completed - File: {dest.name}, Size: {file_size} bytes, Chunks: {chunk_count}")
        return str(dest)
        
    except requests.exceptions.Timeout:
        logging.error(f"Image download timed out: {url}")
        raise
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error downloading image: {e} - URL: {url}")
        logging.error(f"HTTP status: {e.response.status_code if e.response else 'unknown'}")
        raise
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection error downloading image: {url}")
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"Request exception downloading image: {e} - URL: {url}")
        raise
    except IOError as e:
        logging.error(f"File I/O error saving downloaded image: {e} - Destination: {dest}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error downloading image: {e} - URL: {url}", exc_info=True)
        raise


def copy_to_collection(file_path: Path, dest_folder: Path) -> Path:
    """Copy file to collection folder and return destination path"""
    logging.info(f"Copying file to collection - Source: {file_path}, Destination: {dest_folder}")
    
    if not file_path.exists():
        logging.error(f"Source file does not exist: {file_path}")
        raise FileNotFoundError(f"Source file not found: {file_path}")
    
    try:
        # Get file info before copy
        file_size = file_path.stat().st_size
        logging.debug(f"Source file info - Size: {file_size} bytes, Exists: {file_path.exists()}")
        
        # Ensure destination directory exists
        dest_folder.mkdir(parents=True, exist_ok=True)
        logging.debug(f"Ensured destination directory exists: {dest_folder}")
        
        dest = dest_folder / file_path.name
        logging.debug(f"Destination path: {dest}")
        
        if dest.exists():
            dest_size = dest.stat().st_size
            logging.warning(f"Destination file already exists - Path: {dest}, Size: {dest_size} bytes")
            logging.info("Skipping copy as file already exists in collection")
        else:
            logging.debug("Starting file copy operation")
            shutil.copy2(file_path, dest)  # copy2 preserves metadata
            
            # Verify copy was successful
            if dest.exists():
                copied_size = dest.stat().st_size
                logging.info(f"File copied successfully - Source: {file_path.name}, Destination: {dest}, Size: {copied_size} bytes")
                
                if copied_size != file_size:
                    logging.warning(f"File size mismatch after copy - Source: {file_size} bytes, Copied: {copied_size} bytes")
            else:
                logging.error(f"Copy operation failed - destination file not created: {dest}")
                raise IOError(f"Failed to copy file to {dest}")
        
        return dest
        
    except PermissionError as e:
        logging.error(f"Permission error copying file: {e} - Source: {file_path}, Dest: {dest_folder}")
        raise
    except shutil.SameFileError:
        logging.warning(f"Source and destination are the same file: {file_path}")
        return file_path
    except OSError as e:
        logging.error(f"OS error copying file: {e} - Source: {file_path}, Dest: {dest_folder}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error copying file: {e} - Source: {file_path}, Dest: {dest_folder}", exc_info=True)
        raise


def cleanup_temp_marker():
    """Remove temporary download marker"""
    logging.debug("Cleaning up temporary download marker")
    
    if TMP_DOWNLOAD_FILE.exists():
        try:
            file_size = TMP_DOWNLOAD_FILE.stat().st_size
            logging.debug(f"Temporary marker exists - Path: {TMP_DOWNLOAD_FILE}, Size: {file_size} bytes")
            
            TMP_DOWNLOAD_FILE.unlink()
            logging.info("Temporary download marker removed successfully")
            
        except PermissionError as e:
            logging.error(f"Permission error removing temporary marker: {e} - File: {TMP_DOWNLOAD_FILE}")
        except FileNotFoundError:
            logging.debug("Temporary marker already removed by another process")
        except Exception as e:
            logging.error(f"Unexpected error removing temporary marker: {e} - File: {TMP_DOWNLOAD_FILE}", exc_info=True)
    else:
        logging.debug("No temporary download marker found to clean up")


def safe_delete_file(file_path: Path) -> bool:
    """
    Safely delete a file with comprehensive logging
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    logging.info(f"Attempting to safely delete file: {file_path}")
    
    if not file_path.exists():
        logging.warning(f"File does not exist, nothing to delete: {file_path}")
        return True
    
    try:
        file_size = file_path.stat().st_size
        logging.debug(f"File info - Size: {file_size} bytes, Path: {file_path}")
        
        file_path.unlink()
        
        # Verify deletion
        if not file_path.exists():
            logging.info(f"File deleted successfully: {file_path}")
            return True
        else:
            logging.error(f"File deletion failed - file still exists: {file_path}")
            return False
            
    except PermissionError as e:
        logging.error(f"Permission error deleting file: {e} - File: {file_path}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error deleting file: {e} - File: {file_path}", exc_info=True)
        return False


def get_file_info(file_path: Path) -> Optional[dict]:
    """
    Get detailed information about a file for debugging
    
    Args:
        file_path: Path to the file
        
    Returns:
        dict: File information or None if file doesn't exist
    """
    logging.debug(f"Getting file info: {file_path}")
    
    if not file_path.exists():
        logging.debug(f"File does not exist: {file_path}")
        return None
    
    try:
        stat = file_path.stat()
        info = {
            'path': str(file_path),
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'extension': file_path.suffix.lower(),
            'exists': True
        }
        logging.debug(f"File info retrieved: {info}")
        return info
    except Exception as e:
        logging.error(f"Error getting file info: {e} - File: {file_path}")
        return None