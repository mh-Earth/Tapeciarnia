import time
import random
import logging
from pathlib import Path
from threading import Thread, Event
from utils.singletons import get_config,get_language_controller
from utils.path_utils import FAVS_DIR,SAVES_DIR,SUPER_WALLPAPER_DIR
import requests
import logging
from PySide6.QtCore import QThread, Signal, Slot
import requests
import time
from collections import deque

from models.constants import RangeTypes

class UnifiedWallpaperScheduler:
    """
    One scheduler to rule both modes.
    
    offline = pick random local file
    online  = use online API + ImagePrefetchThread queue
    """

    def __init__(self):
        logging.debug("Initializing UnifiedWallpaperScheduler")

        # common scheduler state
        self.interval_minutes = 30
        self.source = str(SAVES_DIR)
        self.change_callback = None
        self.status_callback = None

        self.config = get_config()
        self.stop_event = Event()
        self.last_wallpaper = None

        # thread states
        self.scheduler_thread = None
        self.is_running = False
        self.range_type= None

        # online mode worker
        self.online_worker = None
        self.api_url = None

        # helper
        self.first_serverd:bool = False

        logging.info("UnifiedWallpaperScheduler initialized")

    def set_api_url(self, api_url: str):
        """Set API URL for online mode"""
        logging.info(f"Online scheduler api set to {api_url}")
        self.api_url = api_url

    def set_change_callback(self, callback):
        self.change_callback = callback

    def set_range(self, range_type: str):
        logging.info(f"Range change to {self.range_type} -> {range_type}")
        self.range_type = range_type

    def get_range(self) ->str:
        return self.range_type

    def get_queue_upadate(self,queue_lenght:int):
        logging.debug("Queue lenght:" + str(queue_lenght))
        if queue_lenght == 1 and not self.first_serverd:
            logging.debug("First image serverd")
            self.online_worker._serve_requested_image()
            self.first_serverd = True

    def handle_status(self,status:str):
        self.set_status.emit(status)
    # -------------------------------------------------------------------
    # START / STOP
    # -------------------------------------------------------------------
    def start(self, source: str, range_type:str, interval_minutes: int):
        logging.info(f"Starting UnifiedWallpaperScheduler with source={self.source}")
        self.range_type = range_type
        if interval_minutes <= 0:
            interval_minutes = 1

        if self.is_running:
            self.stop()


        self.source = source
        self.interval_minutes = interval_minutes
        self.stop_event.clear()
        self.is_running = True

        if self.source == str(SAVES_DIR):
            pass

        # online mode uses its own worker
        elif self.source == str(FAVS_DIR):
            if not self.api_url:
                raise RuntimeError("API URL must be set before starting online mode")

            # start online worker
            self.online_worker = OnlineWallpaperScheduler(self.api_url)
            self.online_worker.image_ready.connect(self._on_online_image_ready)
            self.online_worker.queue_updated.connect(self.get_queue_upadate)
            self.online_worker.setStatus.connect(lambda e: self.status_callback(e))
            self.online_worker.start()

        elif self.source == str(SUPER_WALLPAPER_DIR):
            if not self.api_url:
                raise RuntimeError("API URL must be set before starting online mode")

            # start online worker
            self.online_worker = OnlineWallpaperScheduler(self.api_url)
            self.online_worker.image_ready.connect(self._on_online_image_ready)
            self.online_worker.queue_updated.connect(self.get_queue_upadate)
            self.online_worker.setStatus.connect(lambda e: self.status_callback(e))
            self.online_worker.start()

        # main loop (handles timing)
        self.scheduler_thread = Thread(target=self._main_loop, daemon=True)
        logging.debug("Starting UnifiedWallpaperScheduler mainloop thread")
        self.scheduler_thread.start()

    def stop(self):
        logging.info("Stopping Scheduler")
        self.is_running = False
        self.first_serverd = False
        self.stop_event.set()

        # stop main scheduler
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        # stop online worker
        if self.online_worker:
            self.online_worker.stop()
            self.online_worker = None

    def is_active(self):
        return self.is_running

    # -------------------------------------------------------------------
    # MAIN LOOP
    # -------------------------------------------------------------------
    def _main_loop(self):
        logging.info("Unified scheduler loop started")

        while self.is_running and not self.stop_event.is_set():
            # wait for interval
            if not self.is_running:
                break

            if self.source == str(SAVES_DIR):
                self._run_offline_cycle()

            elif self.source == str(FAVS_DIR):
                # ask for image
                if self.online_worker:
                    self.online_worker.request_image()
            
            elif self.source == str(SUPER_WALLPAPER_DIR):
                # ask for image
                if self.online_worker:
                    self.online_worker.request_image()
            
            self.stop_event.wait(self.interval_minutes * 60)


        logging.info("Unified scheduler loop ended")

    # -------------------------------------------------------------------
    # OFFLINE WORKFLOW (unchanged from your original)
    # -------------------------------------------------------------------
    def _run_offline_cycle(self):
        logging.debug("Offline scheduler cycle ran")
        wallpaper = self._get_random_wallpaper()
        logging.debug(f"Random wallpaper for scheduler: {wallpaper}")

        if wallpaper and wallpaper != self.last_wallpaper:
            self.last_wallpaper = wallpaper
            if self.change_callback:
                self.change_callback(file_path=wallpaper)

    def _get_random_wallpaper(self):
        files = self._get_media_files()
        if not files:
            return None

        selected = random.choice(files)

        # avoid same wallpaper twice
        if len(files) > 1 and selected == self.last_wallpaper:
            return self._get_random_wallpaper()

        return selected

    def _get_media_files(self):
        source = self.source
        files = []

        if source == str(FAVS_DIR):
            folders = [FAVS_DIR]
        elif source == str(SAVES_DIR):
            folders = [SAVES_DIR]
        else:
            folders = [Path(source)]

        if self.range_type != None:
            if self.range_type == RangeTypes.ANIMATED:
                exts = self.config.get_valid_video_extensions()
            elif self.range_type == RangeTypes.STATIC:
                exts = self.config.get_valid_image_extensions()
            elif self.range_type == RangeTypes.ALL:
                exts = self.config.get_all_valid_extensions()
            else:
                logging.warning(f"Invalid range type found: {self.range_type}. Switching to all range")
                self.set_range(RangeTypes.ALL)
                exts = self.config.get_all_valid_extensions()

            for f in folders:
                if not f.exists():
                    continue
                files += [x for x in f.iterdir() if x.is_file() and x.suffix.lower() in exts]

            return files

    # -------------------------------------------------------------------
    # ONLINE WORKFLOW
    # -------------------------------------------------------------------
    @Slot(bytes)
    def _on_online_image_ready(self, img_data:dict): # {"url": url, "data": img_bytes}
        """Offline callback receives Path, online receives bytes."""
        logging.info("Offline callback receives Path, online receives bytes.")
        if self.change_callback:
            self.change_callback(image_data=img_data)

    def reset(self):
        """Reset scheduler state (last wallpaper, etc.)"""
        logging.info("Resetting scheduler state")
        self.last_wallpaper = None
        self.range_type= None
        self.source = None
        self.config.set_scheduler_settings(False, None, 30, None)
        

class OnlineWallpaperScheduler(QThread):
    image_ready = Signal(dict)          # {"url": url, "data": img_bytes} emits raw image data (for QPixmap.loadFromData)
    queue_updated = Signal(int)          # emits current queue size
    setStatus = Signal(str)
    sendStopSignal = Signal(str)


    def __init__(self, api_url: str, parent=None):
        super().__init__(parent)
        self.api_url = api_url
        self.running = True
        self.url_list = []               # list of pending URLs from JSON
        self.queue = deque(maxlen=20)    # RAM-stored preloaded images
        self.min_queue = 3               # keep at least 3 images ready
        self.session = requests.Session()
        self.wait_interval = 1.0         # seconds between checks
        self.request_flag = False        # main app requests next image
        self.traslator = get_language_controller()
        self.config = get_config()
        logging.debug("Initiating OnlineWallpaperScheduler Thread")

    # ---------------------------------------------------------
    #               HELPER METHODS
    # ---------------------------------------------------------
    def filter_urls_by_range_type(self,range_type:str):
        if range_type == RangeTypes.ANIMATED:
            self.url_list = [url for url in self.url_list if url.lower().endswith(tuple(self.config.get_valid_video_extensions()))]
        elif range_type == RangeTypes.STATIC:
            self.url_list = [url for url in self.url_list if url.lower().endswith(tuple(self.config.get_valid_image_extensions()))]
        elif range_type == RangeTypes.ALL:
            pass
        else:
            logging.warning(f"Invalid range type found: {range_type}. No filtering applied")


    # ---------------------------------------------------------
    #               THREAD MAIN LOOP
    # ---------------------------------------------------------
    def run(self):
        self._fetch_json_urls()  # fetch first-time URL list
        # logging.info(self.url_list)

        while self.running:
            # 1) If user requested an image → serve it immediately
            if self.request_flag:
                self._serve_requested_image()
                self.request_flag = False

            # 2) If queue too small → download more images
            if len(self.queue) < self.min_queue:
                self._download_next_image()

            # 3) If URL list is almost empty → fetch more from API
            if len(self.url_list) < 3:
                self._fetch_json_urls()
                
            time.sleep(self.wait_interval)

    # ---------------------------------------------------------
    #               PUBLIC: user requesting next image
    # ---------------------------------------------------------
    @Slot()
    def request_image(self):
        """Main app calls this to request next ready image."""
        self.request_flag = True

    # ---------------------------------------------------------
    #               PRIVATE WORK METHODS
    # ---------------------------------------------------------
    def _serve_requested_image(self):
        """Send one preloaded image to the UI."""
        if not self.queue:
            return  # No ready images → UI will request again

        logging.info("Serving image from schedueler qeueu")
        image_bytes:dict = self.queue.popleft()
        self.image_ready.emit(image_bytes)
        self.queue_updated.emit(len(self.queue))

    def _download_next_image(self):
        """Download next image from URL list and add to queue."""
        logging.info("Downloading wallpaper to add in schedueler qeueu")
        if not self.url_list:
            return

        url:str = self.url_list.pop(0)

        try:
            r = self.session.get(url, timeout=10, stream=True)
            r.raise_for_status()
            data:bytes = r.content
            self.queue.append({"url": url, "data": data})
            self.queue_updated.emit(len(self.queue))

        except Exception as e:
            # skip failed download → continue
            logging.error(f"[ERROR] Failed to download {url}: {e}")

    def _fetch_json_urls(self):
        """Fetch new JSON and extend url_list."""
        logging.info("Fetching images from api")
        self.setStatus.emit(self.traslator.get("status.genaral.fetching_online_wallpaper"))

        try:
            r = self.session.get(self.api_url, timeout=10)
            r.raise_for_status()
            data = r.json()

            walls = data.get("wall", {})
            for _id, meta in walls.items():
                url = meta.get("url")
                if not url:
                    continue
                self.url_list.append(url)

            self.filter_urls_by_range_type(self.config.get_range_preference() or RangeTypes.ALL)

            if len(self.url_list) <= 0:
                self.sendStopSignal.emit(self.traslator.get("status.genaral.empty_frvt_collection"))

        except Exception as e:
            logging.error(f"[ERROR] Could not fetch JSON: {e}")

    # ---------------------------------------------------------
    #               CLEAN STOP
    # ---------------------------------------------------------
    def stop(self):
        self.running = False
        self.wait_interval = 0
        self.quit()
        self.wait()



