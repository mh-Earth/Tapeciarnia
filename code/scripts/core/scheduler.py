import time
import random
import logging
from pathlib import Path
from threading import Thread, Event
from typing import Optional, Callable
from utils.singletons import get_config
from utils.path_utils import COLLECTION_DIR, FAVS_DIR,SAVES_DIR



class WallpaperScheduler:
    def __init__(self):
        logging.debug("Initializing WallpaperScheduler")
        self.interval_minutes = 30
        self.source = str(COLLECTION_DIR)
        self.range_type = "all"
        self.is_running = False
        self.thread = None
        self.stop_event = Event()
        self.change_callback: Optional[Callable] = None
        self.last_wallpaper = None
        self.config = get_config()
        logging.info("WallpaperScheduler initialized successfully")


    def set_change_callback(self, callback: Callable):
        """Set callback for when wallpaper should change"""
        logging.debug(f"Setting change callback: {callback}")
        self.change_callback = callback
        logging.debug("Change callback set successfully")

    def set_range(self, range_type: str):
        """Set range type: all, wallpaper, or mp4"""
        logging.info(f"Setting range type: {range_type}")
        self.range_type = range_type
        logging.debug(f"Range type updated to: {range_type}")

    def start(self, source: str, interval_minutes: int):
        """Start the scheduler"""
        logging.info(f"Starting scheduler - Source: {source}, Interval: {interval_minutes} minutes")
        
        if interval_minutes <= 0:
            logging.warning(f"Invalid interval {interval_minutes}, setting to 1 minute")
            interval_minutes = 1

        if self.is_running:
            logging.warning("Scheduler already running, stopping first")
            self.stop()
        
        self.source = source
        self.interval_minutes = interval_minutes
        self.is_running = True
        self.stop_event.clear()
        
        self.thread = Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        logging.info(f"Scheduler started successfully: source='{source}', interval={interval_minutes}min, range={self.range_type}")

    def stop(self):
        """Stop the scheduler"""
        logging.info("Stopping scheduler")
        self.is_running = False
        self.stop_event.set()
        
        if self.thread and self.thread.is_alive():
            logging.debug("Waiting for scheduler thread to finish")
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                logging.warning("Scheduler thread did not stop gracefully within timeout")
            else:
                logging.debug("Scheduler thread stopped successfully")
        else:
            logging.debug("No active scheduler thread to stop")
            
        logging.info("Scheduler stopped")

    def is_active(self):
        """Check if scheduler is running"""
        is_active = self.is_running
        logging.debug(f"Scheduler active status: {is_active}")
        return is_active

    def _scheduler_loop(self):
        """Main scheduler loop"""
        logging.info("Scheduler loop started")
        loop_count = 0
        
        while self.is_running and not self.stop_event.is_set():
            try:
                loop_count += 1
                logging.debug(f"Scheduler loop iteration {loop_count}, waiting {self.interval_minutes} minutes")
                
                # Wait for the interval
                wait_seconds = self.interval_minutes * 60
                self.stop_event.wait(wait_seconds)
                
                if self.stop_event.is_set():
                    logging.debug("Stop event set, breaking scheduler loop")
                    break
                
                if self.is_running and self.change_callback:
                    logging.debug("Interval elapsed, selecting new wallpaper")
                    
                    # Get a random wallpaper that's different from the current one
                    wallpaper = self._get_random_wallpaper()
                    if wallpaper:
                        if wallpaper != self.last_wallpaper:
                            logging.info(f"Selected new wallpaper: {wallpaper.name}")
                            self.last_wallpaper = wallpaper
                            self.change_callback(wallpaper)
                            self.config.set_last_video(wallpaper)
                            logging.debug("Change callback executed successfully")
                        else:
                            logging.info("Skipping same wallpaper selection, waiting for next interval")
                    else:
                        logging.warning("No wallpaper found for scheduling")
                        
            except Exception as e:
                logging.error(f"Scheduler error in loop iteration {loop_count}: {e}", exc_info=True)
                logging.info("Waiting 60 seconds before retrying after error")
                time.sleep(60)  # Wait a minute before retrying
        
        logging.info("Scheduler loop ended")

    def _get_random_wallpaper(self):
        """Get a random wallpaper file"""
        logging.debug("Getting random wallpaper for scheduler")
        files = self._get_media_files()
        
        if files:
            selected = random.choice(files)
            if  len(files) > 1 and selected == self.last_wallpaper:
                logging.debug("Scheduler: Same wallpaper seleted as before. Trying again!!")
                return self._get_random_wallpaper()

            logging.debug(f"Randomly selected wallpaper: {selected.name} from {len(files)} options")
            return selected
        else:
            logging.warning("No media files found for random selection")
            return None

    def _get_media_files(self):
        """Get media files based on current source and range"""
        logging.debug(f"Getting media files - Source: {self.source}, Range: {self.range_type}")
        files = []
        
        # Define search folders based on source
        if self.source == str(FAVS_DIR):
            # Favorites should ONLY use FAVS_DIR
            search_folders = [FAVS_DIR]
            source_type = "favorites"
        elif self.source == str(SAVES_DIR):
            # My Collection should include ALL folders
            search_folders = [SAVES_DIR]
            source_type = "collection"
        else:
            # Custom source
            search_folders = [Path(self.source)]
            source_type = "custom"
        
        logging.debug(f"Search folders for {source_type}: {[str(f) for f in search_folders]}")
        
        # Define extensions based on range type
        if self.range_type == "mp4":
            extensions = self.config.get_valid_video_extensions()
            range_desc = "videos only"
        elif self.range_type == "wallpaper":
            extensions = self.config.get_valid_image_extensions()
            range_desc = "images only"
        else:  # "all"
            extensions = self.config.get_all_valid_extensions()
            range_desc = "all media types"
        
        logging.debug(f"File extensions for {range_desc}: {extensions}")
        
        total_files_found = 0
        for folder in search_folders:
            if folder.exists():
                logging.debug(f"Searching folder: {folder}")
                try:
                    folder_files = [
                        f for f in folder.iterdir() 
                        if f.is_file() and f.suffix.lower() in extensions
                    ]
                    files.extend(folder_files)
                    total_files_found += len(folder_files)
                    logging.debug(f"Found {len(folder_files)} files in {folder}")
                except Exception as e:
                    logging.error(f"Error accessing folder {folder}: {e}")
            else:
                logging.warning(f"Search folder does not exist: {folder}")
        
        # Log summary
        file_types = {}
        for file in files:
            ext = file.suffix.lower()
            file_types[ext] = file_types.get(ext, 0) + 1
        
        logging.info(f"Media files search completed: {len(files)} total files found from {source_type} with range {self.range_type}")
        if file_types:
            type_summary = ", ".join([f"{count} {ext}" for ext, count in file_types.items()])
            logging.debug(f"File type breakdown: {type_summary}")
        
        return files