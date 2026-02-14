# ===========================================================
#  Wallpaper Controller
# ===========================================================


import sys
import subprocess
import logging
import platform
import os
import re
import time
import json
import tomllib
import win32gui # type: ignore
import subprocess
from pathlib import Path

from screeninfo import get_monitors
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread

from utils.system_utils import (
    get_monitors_info,
    which,
    set_static_desktop_wallpaper,
    get_windows_version,
    get_current_desktop_wallpaper,
)
from utils.path_utils import (
    get_weebp_path,
    get_mpv_path,
)
from utils.command_handler import run_and_forget_silent
from ui.widgets import CustomMessageBox,ButtonCollection
from utils.singletons import get_config,get_language_controller
from utils.path_utils import video_settings_path,playback_setting,SAVES_DIR
from models.constants import PlayBackMode
from core.refresh import attach_window_to_desktop
from core.maker import WallpaperMaker
class WallpaperController(QThread):
    def __init__(self):
        logging.debug("initiating wallpaper controller class")
        self.current_is_video = False

        # IPC pipe names (one per monitor)
        self._mpv_ipc_pipes = []

        # Cached paths
        self.weebp_path = get_weebp_path()
        self.mpv_path = get_mpv_path()
        self.mpv_cwd = self.mpv_path.parents[0]

        # Refresh limits
        self.refresh_limit = 50
        self.refresh_count = 0
        # Translator
        self.language_controller = get_language_controller()
        # custom message box
        self.customMessageBox = CustomMessageBox(ButtonCollection(language_data=self.language_controller.lang))
        self.ids_list: list = []
        # monitor detection
        self.mode = None
        # fallback setting
        self.retry_fallback:bool = None
        self.max_retry_attempts:int = 0
        self.retry_fallback_attempts:int = 0
        self.auto_rerty = False
        # setup fallback
        self.setup_fallback_settings()
        # status update
        self.status_callback = None
        self.video_success_callback = None
        self.btn_update_callback = None
        self.initial_monitor_count = self._detect_monitors()


        if not self._check_weebp_and_mpv():
            self.customMessageBox.critical(
                None,
                # TODO: Add translations later
                "Error", # have to add in translations later
                "Weebp or MPV executable not found. animated wallpaper functionality may be limited.", # have to add in translations later
            )
            sys.exit(1)
        # Initial wallpaper at startup
        self.initial_wallpaper = self._get_initial_wallpaper() 

    # ---------------------------------------------------------
    #  Utility Checks
    # ---------------------------------------------------------
    def _check_weebp_and_mpv(self) -> bool:
        return (
            self.weebp_path is not None
            and self.weebp_path.exists()
            and self.mpv_path is not None
            and self.mpv_path.exists()
        )
    # ---------------------------------------------------------
    #  Initial Wallpaper Handling
    # ---------------------------------------------------------

    def _get_current_wallpaper(self):
        """Get the current system wallpaper path"""
        try:
            wallpaper = get_current_desktop_wallpaper()
            logging.debug(f"Retrieved current wallpaper: {wallpaper}")
            return wallpaper
        except Exception as e:
            logging.error(f"Could not get current wallpaper: {e}", exc_info=True)
        return None

    def _get_initial_wallpaper(self):
        """Get the wallpaper that was set when the controller was initialized"""
        wallpaper = self._get_current_wallpaper()
        logging.debug(f"Initial wallpaper at startup: {wallpaper}")
        return wallpaper
    
    def _restore_initial_wallpaper(self):
        """Restore the wallpaper that was set when the app was initialized"""
        if self.initial_wallpaper:
            logging.info("Restoring initial wallpaper...")
            set_static_desktop_wallpaper(self.initial_wallpaper)
        else:
            logging.warning("No initial  wallpaper found to restore.")

    # ---------------------------------------------------------
    #  Optional Tools
    # ---------------------------------------------------------
    def _run_refresh(self, fallback_func=None,**kwargs) -> bool:
        time.sleep(0.5)  # wait a moment to ensure weebp has registered the mpv wallpaper
        video_path=kwargs.get("video_path")
        original_path=kwargs.get("original_path",video_path)

        view_id = self.get_view_id()
        logging.info(f"View IDs obtained: {view_id}")

        for ids in view_id:
            logging.info(f"Processing View ID: {ids}")
            if ids == "0" : # and ids not in self.ids_list did not get valid view id, try again until limit is reached
                if self.refresh_count < self.refresh_limit:
                    logging.warning("View ID not found, retrying refresh...")
                    self.refresh_count += 1
                    return self._run_refresh(fallback_func=None,**kwargs)
                elif self.refresh_count >= self.refresh_limit:
                    logging.error("Max refresh attempts reached, aborting refresh.")
                    self.customMessageBox.critical(
                        None,
                        # TODO: Add translations later
                        "Attempt Error", # have to add in translations later
                        "Failed to set animated wallpaper. Aborting operation.\nTry later", # have to add in translations later
                    )
                    self.force_stop() # stop all wallpaper processes for windows. This will work for now as we are only using this for windows not mac or linux
                    self.video_success_callback(video_path=original_path,success=False)

            else: # got a valid view id, try to attach to desktop

                hwnd = int(ids, 16)
                logging.warning(f"Running refresh for 0x{ids}")
                success = attach_window_to_desktop(hwnd)

                if success:
                    self.auto_rerty = False
                    self.refresh_count = 0  # reset count on success
                    self.ids_list.append(ids)
                    self.current_is_video = success
                    self.video_success_callback(video_path=original_path,success=success)
                else:
                    if self.retry_fallback:
                        logging.warning(f"Failed to attach View ID {ids} to desktop, asking for retry.")
                        # if self.auto_rerty:

                        reply = self.customMessageBox.question(
                            None,
                            # TODO: Add translations later
                            "Attachment Error", # have to add in translations later
                            "Failed to set animated wallpaper.\nTry again??", # have to add in translations later
                        ) if not self.auto_rerty else QMessageBox.YesRole

                        if reply == QMessageBox.YesRole:
                            self.auto_rerty = True
                            self.force_stop() # stop all wallpaper processes for windows. This will work for now as we are only using this for windows not mac or linux
                            if self.retry_fallback_attempts < self.max_retry_attempts:
                                self.retry_fallback_attempts += 1
                                fallback_func(video_path,**kwargs) if fallback_func else None # try again with fallback if provided
                            else:
                                self.retry_fallback_attempts = 0
                                self.auto_rerty = False
                        else:
                            self.force_stop() # stop all wallpaper processes for windows. This will work for now as we are only using this for windows not mac or linux
                            self.video_success_callback(success=False)


                    else:
                        logging.warning(f"Failed to attach View ID {ids} to desktop, aborting setting wallpaper.")
                        self.customMessageBox.critical(
                            None,
                            # TODO: Add translations later
                            "Attachment Error", # have to add in translations later
                            "Failed to set animated wallpaper. Aborting operation.\nTry again", # have to add in translations later
                        )
                        self.force_stop() # stop all wallpaper processes for windows. This will work for now as we are only using this for windows not mac or linux
                        self.video_success_callback(success=False)
                

    def run_optional_tools(self,fallback_func=None,**kwargs) -> bool:
        if get_windows_version() == "Windows11":
            return self._run_refresh(fallback_func,**kwargs)

    # ---------------------------------------------------------
    #  STOP
    # ---------------------------------------------------------
    def stop(self):
        logging.info("Stopping wallpaper processes...")

        if sys.platform.startswith("linux"):
            subprocess.call(
                "pkill -f mpv",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        elif sys.platform.startswith("win"):
            if self.current_is_video:
                logging.debug("Stopping animated wallpaper processes on Windows")
                self._stop_windows()
            else:
                self._restore_initial_wallpaper()

        self.current_is_video = False
        self._mpv_ipc_pipes.clear()

    def _stop_windows(self):
        kill_list = ["mpv.exe", "wp.exe", "autopause.exe","ffmpeg.exe"]

        for proc in kill_list:
            logging.debug(f"Killing process {proc}")
            subprocess.run(
                ["taskkill", "/F", "/IM", proc, "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000,
            )

    def force_stop(self): # ONLY FOR WINDOWS
        logging.warning("Force stopping all wallpaper processes...")
        self.current_is_video = False
        self._mpv_ipc_pipes.clear()
        self._stop_windows()
    # ---------------------------------------------------------
    #  START VIDEO
    # ---------------------------------------------------------
    def start_video(self, video_path: str):
        if not isinstance(video_path,str):
            raise ValueError(f"video path have to be class str not {type(video_path)}")

        logging.debug("start_video function triggerd...")
        self.setup_wallpaper_mode()
        if platform.system() == "Windows":
            if self.current_is_video:
                logging.info("Replacing current video")
                self._play_next_video(video_path)
                return
            
            self._start_video_windows(video_path)
            return
            

        if sys.platform.startswith("linux"):
            self._start_video_linux(video_path)
            return

        self._start_video_fallback(video_path)

    # ---------------------------------------------------------
    #  MPV IPC (REAL CONTROL)
    # ---------------------------------------------------------
    def _mpv_ipc(self, pipe_name: str, command: list, silent=False):
        payload = json.dumps({"command": command}) + "\n"
        pipe_path = r"\\.\pipe\\" + pipe_name

        try:
            with open(pipe_path, "w", encoding="utf-8") as pipe:
                pipe.write(payload)
                pipe.flush()
            return True

        except FileNotFoundError:
            # IPC pipe not created yet (normal during startup)
            if not silent:
                logging.debug("IPC pipe not ready yet: %s", pipe_name)
            return False

        except Exception as e:
            logging.error("IPC failed (%s): %s", pipe_name, e,exc_info=True)
            return False

    # ---------------------------------------------------------
    #  PLAY NEXT VIDEO (ALL MONITORS)
    # ---------------------------------------------------------
    def _play_next_video(self, video_path: str):
        logging.debug("_play_next_video function triggerd...")
        self.setup_wallpaper_mode()
        if not self._mpv_ipc_pipes:
            logging.error("No active mpv IPC pipes")
            return
        
        if self.mode and self.mode == PlayBackMode.SINGLE:
            # creating panoramic wallpaper from original wallpaper for next wallpaper..
            monitors = len(get_monitors())
            target_height = min(m.height for m in get_monitors())
            logging.info(f"Creating panoramic wallpaper for {monitors} monitor from {video_path}")
            output_path = str(SAVES_DIR / "wallpaper.mp4")
            def update(new_path):
                try:

                    for pipe in self._mpv_ipc_pipes:
                        self._mpv_ipc(pipe, ["loadfile", str(new_path), "replace"])
                    self.video_success_callback(video_path=video_path,success=True)
                except Exception as e:
                    logging.error(e,exc_info=True)
                    self.video_success_callback(success=False)

            self.maker_thread = WallpaperMaker(video_path,output_path,monitors,target_height)
            self.maker_thread.done.connect(lambda new_path: update(new_path) )
            self.maker_thread.error.connect(lambda e: self.status_callback(e))
            self.maker_thread.progress.connect(lambda e: self.status_callback(e))
            self.maker_thread.start()
            return

        for pipe in self._mpv_ipc_pipes:
            self._mpv_ipc(pipe, ["loadfile", video_path, "replace"])


        self.video_success_callback(video_path=video_path,success=True)
        logging.info("Wallpaper video switched on all monitors")
    

    # ---------------------------------------------------------
    #  WINDOWS VIDEO START
    # ---------------------------------------------------------
    def _start_video_windows(self, video_path: str):
        logging.debug("Starting animated wallpaper for windows...")

        try:
            self._mpv_ipc_pipes.clear()

            if self.mode: # there is more then 1 monitor, and mode is set to either "tiled" or "single"
                if self.mode == PlayBackMode.TILED:
                    # check if all monitors are aligned at (0,0) in multi-monitor setup, if not, show warning that animated wallpapers may not work properly
                    if not self.check_monitors_setup():
                        logging.warning("Monitors may not be properly aligned for animated wallpapers. Proceeding anyway.")
                        reply = self.customMessageBox.question(
                            None,
                            title="Monitor Setup Warning",
                            message="Your monitors may not be properly aligned for animated wallpapers. This could lead to visual issues or incorrect display behavior. Continue anyway?",
                        )
                    
                        if reply == QMessageBox.YesRole:
                            logging.info("User chose to proceed with animated wallpaper setup despite monitor alignment issues.")
                            self._start_multi_tiled_video_windows(video_path)
                            
                        else:
                            logging.info("User chose to abort animated wallpaper setup due to monitor alignment issues.")
                            
                    else:
                        logging.info("Monitors properly aligned, proceeding with tiled animated wallpaper setup.")
                        self._start_multi_tiled_video_windows(video_path)
                    

                
                elif self.mode == PlayBackMode.SINGLE:
                    monitors = len(get_monitors())
                    target_height = min(m.height for m in get_monitors())
                    logging.info(f"Creating panoramic wallpaper for {monitors} monitor from {video_path}")
                    output_path = str(SAVES_DIR / "wallpaper.mp4")

                    self.maker_thread = WallpaperMaker(video_path,output_path,monitors,target_height)
                    self.maker_thread.done.connect(lambda new_path: self._start_multi_single_video_windows(new_path,original_path=video_path))
                    self.maker_thread.error.connect(lambda e: self.status_callback(e))
                    self.maker_thread.progress.connect(lambda e: self.status_callback(e))
                    self.maker_thread.start()

                else:
                    logging.warning(f"Unknown wallpaper mode: {self.mode}. Defaulting to 'tiled'.")
                    self._start_multi_single_video_windows(video_path)

            else: # only 1 monitor detected, defaulting to single mode
                # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                self._start_single_monitor_video_window(video_path)

        except Exception as e:
            logging.error("Failed to start animated wallpaper", exc_info=True)
            self.stop()
            self.video_success_callback(success=False)
    
    def _start_single_monitor_video_window(self, video_path: Path) -> bool:

        try:

            logging.warning("Starting animated wallpaper in single monitor mode")

            cmd = self._build_mpv_cmd(video_path, 0)
            run_and_forget_silent(cmd, cwd=self.mpv_cwd)

            self._mpv_ipc_pipes.append(f"mpv_wallpaper_{0}")
            time.sleep(0.5)

            add_cmd = [
                str(self.weebp_path),
                "add",
                "--wait",
                "--fullscreen",
                "--class",
                "mpv",
            ]
            run_and_forget_silent(add_cmd, cwd=self.mpv_cwd)
            time.sleep(0.5)


            # 🔴 WAIT UNTIL IPC EXISTS + PLAYBACK STARTED
            if not self._wait_for_mpv_ready():
                logging.warning("mpv did not become ready in time")
            

            self.run_optional_tools(fallback_func=self._start_single_monitor_video_window, video_path=video_path)
        except Exception as e:
            self.force_stop()
            logging.error(f"Error while Starting animated wallpaper in single monitor mode: {e}",exc_info=True)
            self.video_success_callback(success=False)

    # TODO: Now in development
    def _start_multi_single_video_windows(self, video_path: Path,**kw):
        print(f"vals: {video_path},{kw}")

        try:
            logging.warning("Starting animated wallpaper in multi-monitor single video mode")
            video_path = str(video_path)
            cmd = self._build_mpv_cmd(video_path, 0)
            run_and_forget_silent(cmd, cwd=self.mpv_cwd)

            self._mpv_ipc_pipes.append(f"mpv_wallpaper_{0}")
            time.sleep(0.5)

            add_cmd = [
                str(self.weebp_path),
                "add",
                "--wait",
                "-p",
                "--class",
                "mpv"
            ]
            run_and_forget_silent(add_cmd, cwd=self.mpv_cwd)
            time.sleep(0.3)

            # 🔴 WAIT UNTIL IPC EXISTS + PLAYBACK STARTED
            if not self._wait_for_mpv_ready():
                logging.warning("mpv did not become ready in time")
            
            # ✅ NOW SAFE
            original_path = kw.get("original_path","")
            self.run_optional_tools(fallback_func=self._start_multi_single_video_windows, video_path=video_path,original_path=original_path)

            del self.maker_thread

        except Exception as e:
            self.force_stop()
            logging.error(e,exc_info=True)
            self.video_success_callback(success=False)




    def _start_multi_tiled_video_windows(self, video_path: str):
        # 
        logging.warning("Starting animated wallpaper in multi-monitor tiled mode")

        cmd = self._build_mpv_cmd(video_path, 0)
        run_and_forget_silent(cmd, cwd=self.mpv_cwd)

        self._mpv_ipc_pipes.append(f"mpv_wallpaper_{0}")
        time.sleep(0.5)

        add_cmd = [
            str(self.weebp_path),
            "add",
            "--wait",
            "--panoramic",
            "--class", 
            "mpv"
        ]
        
        run_and_forget_silent(add_cmd, cwd=self.mpv_cwd)
        time.sleep(0.5)


        # 🔴 WAIT UNTIL IPC EXISTS + PLAYBACK STARTED
        if not self._wait_for_mpv_ready():
            logging.warning("mpv did not become ready in time")

        # ✅ NOW SAFE
        self.run_optional_tools(fallback_func=self._start_multi_tiled_video_windows,video_path=video_path)





    # ---------------------------------------------------------
    #  LINUX VIDEO START
    # ---------------------------------------------------------
    def _start_video_linux(self, video_path):
        mpv = which("mpv")
        if not mpv:
            raise RuntimeError("mpv not found")

        subprocess.Popen(
            [
                mpv,
                "--loop",
                "--no-audio",
                "--fullscreen",
                "--no-border",
                video_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # ---------------------------------------------------------
    #  FALLBACK
    # ---------------------------------------------------------
    def _start_video_fallback(self, video_path):
        mpv = which("mpv")
        if not mpv:
            raise RuntimeError(f"Unsupported platform: {sys.platform}")

        subprocess.Popen(
            [
                mpv,
                "--loop",
                "--no-audio",
                "--fullscreen",
                "--no-border",
                video_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # ---------------------------------------------------------
    #  STATIC IMAGE
    # ---------------------------------------------------------
    def start_image(self, image_path):
        set_static_desktop_wallpaper(image_path)

        if self.current_is_video:
            self.stop()

        self.current_is_video = False

    # ---------------------------------------------------------
    #  VIEW ID (Windows 11)
    # ---------------------------------------------------------
    def get_view_id(self) -> list[str]:
        try:
            proc = subprocess.run(
                [str(self.weebp_path), "ls"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=0x08000000,
            )
        except Exception:
            return []

        logging.info("Result of 'weebp ls':\n  %s", proc.stdout.strip())

        # Match lines like: [00A1B2C3] mpv_wallpaper_0
        matches = re.findall(
            r"\[([0-9A-Fa-f]{8})\].*?mpv",
            proc.stdout
        )

        return matches

    # ---------------------------------------------------------
    #  MPV COMMAND BUILDER
    # ---------------------------------------------------------
    def _build_mpv_cmd(self, video_path: str, screen_index: int) -> list:
        return [
            str(self.weebp_path),
            "run",
            "mpv",
            video_path,

            # PER-MONITOR ISOLATION
            f"--screen={screen_index}",
            f"--title=mpv_wallpaper_{screen_index}",


            # WINDOW / WALLPAPER MODE
            "--fullscreen",
            "--no-border",
            "--ontop=no",
            "--keep-open=yes",
            "--loop=inf",

            # VIDEO BEHAVIOR
            "--panscan=0",
            "--geometry=100%x100%",

            # PERFORMANCE
            "--hwdec=auto-safe",
            "--no-audio",
            "--no-osd-bar",
            "--osd-level=0",

            # STABILITY
            "--force-window=yes",

            # ASPECT / SCALING (CRITICAL FOR MULTI-MONITOR)
            "--keepaspect=no",
            # "--video-unscaled=no",

            #"--video-align-x=0.5",
            #"--video-align-y=0.5",
            # ===================================
            # ===================================
            # *self.load_video_flags(),  # load video settings for debugging
            # ===================================


            f"--input-ipc-server=\\\\.\\pipe\\mpv_wallpaper_{screen_index}",
        ]

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def wait_for_hwnd(self, hwnd, timeout=10.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                return True
            time.sleep(0.05)
        return False
    def _mpv_ipc_json(self, pipe_name: str, command: list, silent=False):
        payload = json.dumps({"command": command}) + "\n"
        pipe_path = r"\\.\pipe\\" + pipe_name

        try:
            with open(pipe_path, "r+", encoding="utf-8") as pipe:
                pipe.write(payload)
                pipe.flush()
                return json.loads(pipe.readline())

        except Exception:
            if not silent:
                logging.debug("IPC JSON failed: %s", pipe_name)
            return None


    def _wait_for_mpv_ready(self, timeout=6.0) -> bool:
        start = time.time()

        while time.time() - start < timeout:
            all_ready = True

            for pipe in self._mpv_ipc_pipes:
                response = self._mpv_ipc_json(
                    pipe,
                    ["get_property", "time-pos"],
                    silent=True
                )

                # IPC not ready or playback not started
                if not response or response.get("data") is None:
                    all_ready = False
                    break

            if all_ready:
                logging.info("mpv playback confirmed on all monitors")
                return True

            time.sleep(0.1)

        logging.warning("mpv playback did not become ready in time")
        return False

    def wait_for_playback(self, pipe, timeout=8.0):
        start = time.time()
        while time.time() - start < timeout:
            if self._mpv_ipc_json(pipe, ["get_property", "playback-time"], silent=True):
                return True
            time.sleep(0.1)
        return False


    # ---------------------------------------------------------
    # Monitor setup corss-checking
    # ---------------------------------------------------------
    def check_monitors_setup(self):
        monitors = get_monitors_info()
        logging.debug(f"Monitors detected: {monitors}")
        for m in monitors:
            if m.get("primary") and m.get("position") != (0, 0):
                logging.warning("Primary monitor is not at (0,0) - this may cause issues with animated wallpapers.")
                return False
        return True
    
    def _detect_monitors(self)   -> int:
        return len(get_monitors_info())
    
    def setup_wallpaper_mode(self):

        logging.debug(f"Setting up wallpaper mode")
        monitor_count = self._detect_monitors()
        logging.info(f"{monitor_count} monitor(s) detected")
        if self.initial_monitor_count != monitor_count:
            logging.warning(f"Monitor count change {self.initial_monitor_count} -> {monitor_count}")
            self.initial_monitor_count = monitor_count
            self.stop()

        if monitor_count > 1:
            mode = self.load_video_settings().get("mode", PlayBackMode.TILED)

            if mode == "single":
                self.mode = PlayBackMode.SINGLE
            else:
                self.mode = PlayBackMode.TILED

            logging.info(f"Setting up wallpaper mode: {self.mode}")
        else:
            self.mode = None
    
    def setup_fallback_settings(self):
        self.retry_fallback = self.load_video_settings().get("retry", False)
        self.max_retry_attempts= self.load_video_settings().get("retry_attempts", 10)

    # ============================================================
    # For debugging purposes only
    # ============================================================
    def load_video_flags(self) -> list:
        """Load video settings from toml file."""
        try:
            if not os.path.exists(video_settings_path):
                raise FileNotFoundError(f"Video settings file not found: {video_settings_path}")
            
            with open(video_settings_path, "rb") as f:
                config = tomllib.load(f)
            
            if "flags" not in config:
                raise ValueError("'flags' key not found in video settings")
            
            flags = config["flags"]
            if not isinstance(flags, list):
                raise TypeError(f"'flags' is not a list, got {type(flags)}")
            
            return flags
        
        except (FileNotFoundError, ValueError, TypeError, tomllib.TOMLDecodeError) as e:
            logging.error(f"Error loading video settings: {e}",exc_info=True)
            raise
    
    def load_video_settings(self) -> dict:
        """Load video settings from toml file."""
        try:
            if not os.path.exists(playback_setting):
                return {"mode": "tiles" }
                # raise FileNotFoundError(f"Video mode file not found: {playback_setting}")
            
            with open(playback_setting, "rb") as f:
                config = tomllib.load(f)
            
            if "settings" not in config:
                raise ValueError("'settings' key not found in video settings")
            
            settings = config["settings"]
            if not isinstance(settings, dict):
                raise TypeError(f"'settings' is not a dict, got {type(settings)}")
            
            return settings
        
        except (FileNotFoundError, ValueError, TypeError, tomllib.TOMLDecodeError) as e:
            logging.error(f"Error loading video settings: {e}",exc_info=True)
            raise

