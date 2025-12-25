import logging

from .path_utils import TMP_DOWNLOAD_FILE




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


