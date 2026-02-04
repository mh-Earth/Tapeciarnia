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

from screeninfo import get_monitors
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread

from utils.system_utils import (
    get_monitor_dpi_from_point,
    get_monitors_dpi_info,
    which,
    set_static_desktop_wallpaper,
    get_windows_version,
    get_current_desktop_wallpaper,
)
from utils.path_utils import (
    get_weebp_path,
    get_mpv_path,
    get_tools_path,
)
from utils.command_handler import run_and_forget_silent
from ui.widgets import CustomMessageBox,ButtonCollection
from utils.singletons import get_config,get_language_controller
from utils.path_utils import video_settings_path

class WallpaperController(QThread):
    def __init__(self):
        self.current_is_video = False

        # IPC pipe names (one per monitor)
        self._mpv_ipc_pipes = []

        # Cached paths
        self.tools_path = get_tools_path()
        self.weebp_path = get_weebp_path()
        self.mpv_path = get_mpv_path()

        # Refresh limits
        self.refresh_limit = 50
        self.refresh_count = 0
        # Translator
        self.language_controller = get_language_controller()
        # custom message box
        self.customMessageBox = CustomMessageBox(ButtonCollection(language_data=self.language_controller.lang))
        self.ids_list: list = []


        if not self._check_weebp_and_mpv():
            self.customMessageBox.critical(
                None,
                # TODO: Add translations later
                "Error", # have to add in translations later
                "Weebp or MPV executable not found. Video wallpaper functionality may be limited.", # have to add in translations later
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
    def _run_refresh(self):
        time.sleep(0.5)  # wait a moment to ensure weebp has registered the mpv wallpaper
        view_id = self.get_view_id()
        logging.info(f"View IDs obtained: {view_id}")
        for ids in view_id:
            logging.info(f"Processing View ID: {ids}")
            if ids == "0": # and ids not in self.ids_list:
                if self.refresh_count < self.refresh_limit:
                    logging.warning("View ID not found, retrying refresh...")
                    self.refresh_count += 1
                    return self._run_refresh()
                elif self.refresh_count >= self.refresh_limit:
                    logging.error("Max refresh attempts reached, aborting refresh.")
                    self.customMessageBox.critical(
                        None,
                        # TODO: Add translations later
                        "Attempt Error", # have to add in translations later
                        "Failed to set animated wallpaper.\nAborting operation.\nTry again", # have to add in translations later
                    )
                    self.stop()
                    return
            else :
                refresh_exe = os.path.join(self.tools_path, "refresh.exe")
                run_and_forget_silent([refresh_exe, f"0x{ids}"])
                self.refresh_count = 0  # reset count on success
                self.ids_list.append(ids)
            

    def run_optional_tools(self):
        if get_windows_version() == "Windows11":
            self._run_refresh()
            pass

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
                logging.debug("Stopping video wallpaper processes on Windows")
                self._stop_windows()
            else:
                self._restore_initial_wallpaper()

        self.current_is_video = False
        self._mpv_ipc_pipes.clear()

    def _stop_windows(self):
        kill_list = ["mpv.exe", "wp.exe", "autopause.exe", "refresh.exe"]

        for proc in kill_list:
            subprocess.run(
                ["taskkill", "/F", "/IM", proc, "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000,
            )

    # ---------------------------------------------------------
    #  START VIDEO
    # ---------------------------------------------------------
    def start_video(self, video_path: str):
        if platform.system() == "Windows":
            if self.current_is_video:
                self._play_next_video(video_path)
                return

            self.current_is_video = True
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
            logging.error("IPC failed (%s): %s", pipe_name, e)
            return False

    # ---------------------------------------------------------
    #  PLAY NEXT VIDEO (ALL MONITORS)
    # ---------------------------------------------------------
    def _play_next_video(self, video_path: str):
        if not self._mpv_ipc_pipes:
            logging.error("No active mpv IPC pipes")
            return

        for pipe in self._mpv_ipc_pipes:
            self._mpv_ipc(pipe, ["loadfile", video_path, "replace"])

        logging.info("Wallpaper video switched on all monitors")

    # ---------------------------------------------------------
    #  WINDOWS VIDEO START
    # ---------------------------------------------------------
    def _start_video_windows(self, video_path: str):
        try:
            monitors = get_monitors()
            mpv_cwd = self.mpv_path.parents[0]
            self._mpv_ipc_pipes.clear()

            for idx, monitor in enumerate(monitors):
                print(f"Starting wallpaper on monitor {idx}: {monitor.x}, {monitor.y} - {monitor.width}x{monitor.height}")
                cmd = self._build_mpv_cmd(video_path, idx, monitor)
                run_and_forget_silent(cmd, cwd=mpv_cwd)

                self._mpv_ipc_pipes.append(f"mpv_wallpaper_{idx}")
                time.sleep(0.5)

                add_cmd = [
                    str(self.weebp_path),
                    "add",
                    "--wait",
                    "--fullscreen",
                    "--name",
                    f"mpv_wallpaper_{idx}",
                ]
                run_and_forget_silent(add_cmd, cwd=mpv_cwd)
                time.sleep(0.3)


            # 🔴 WAIT UNTIL IPC EXISTS + PLAYBACK STARTED
            if not self._wait_for_mpv_ready():
                logging.warning("mpv did not become ready in time")
            
            # ✅ NOW SAFE
            self.run_optional_tools()



            # get mpv window handles (one per monitor)
            view_ids = list(reversed(self.get_view_id()))

            monitor_info = get_monitors_dpi_info()  # contains ui_scale
            assert len(view_ids) >= len(monitors)

            for idx, (monitor, view_id) in enumerate(zip(monitors, view_ids)):
                scale = monitor_info[idx]["ui_scale"]

                # logical → physical
                phys_x = int(monitor.x * scale)
                phys_y = int(monitor.y * scale)
                phys_w = int(monitor.width * scale)
                phys_h = int(monitor.height * scale)

                move_cmd = [
                    str(self.weebp_path),
                    "mv",
                    "-a", f"0x{view_id}",
                    "-x", str(phys_x),
                    "-y", str(phys_y),
                    "--width", str(phys_w),
                    "--height", str(phys_h),
                ]

                run_and_forget_silent(move_cmd)
                time.sleep(0.3)



        except Exception as e:
            logging.error("Failed to start video wallpaper", exc_info=True)

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
    def _build_mpv_cmd(self, video_path: str, screen_index: int,monitor=None) -> list:
        return [
            str(self.weebp_path),
            "run",
            "mpv",
            video_path,

            # PER-MONITOR ISOLATION
            f"--screen={screen_index}",
            f"--title=mpv_wallpaper_{screen_index}",
            *self.load_video_settings(),  # load video settings for debugging


            f"--input-ipc-server=\\\\.\\pipe\\mpv_wallpaper_{screen_index}",



        ]
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

# ============================================================
# For debugging purposes only
# ============================================================
    def load_video_settings(self) -> list:
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
            logging.error(f"Error loading video settings: {e}")
            raise

