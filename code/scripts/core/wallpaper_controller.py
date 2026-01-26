import sys
import subprocess
import logging
import platform
import os
import re
import time
import json

from screeninfo import get_monitors
from PySide6.QtWidgets import QMessageBox
from ui.widgets import CustomMessageBox

from utils.system_utils import (
    which,
    set_static_desktop_wallpaper,
    get_windows_version,
)
from utils.path_utils import (
    get_weebp_path,
    get_mpv_path,
    get_tools_path,
)
from utils.command_handler import run_and_forget_silent


class WallpaperController:
    def __init__(self):
        self.current_is_video = False

        # IPC pipe names (one per monitor)
        self._mpv_ipc_pipes = []

        # Cached paths
        self.tools_path = get_tools_path()
        self.weebp_path = get_weebp_path()
        self.mpv_path = get_mpv_path()

        # Refresh limits
        self.refresh_limit = 100
        self.refresh_count = 0

        if not self._check_weebp_and_mpv():
            QMessageBox.critical(
                None,
                # TODO: Add translations later
                "Error", # have to add in translations later
                "Weebp or MPV executable not found. Video wallpaper functionality may be limited.", # have to add in translations later
            )
            sys.exit(1)

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
    #  Optional Tools
    # ---------------------------------------------------------
    def _run_refresh(self):
        view_id = self.get_view_id()
        logging.info(f"View ID obtained: {view_id}")

        if view_id == "0":
            if self.refresh_count < self.refresh_limit:
                logging.warning("View ID not ready, retrying refresh...")
                self.refresh_count += 1
                time.sleep(.3)
                return self._run_refresh()
            elif self.refresh_count >= self.refresh_limit:
                logging.error("Max refresh attempts reached, aborting refresh.")
                CustomMessageBox.critical(
                    None,
                    # TODO: Add translations later
                    "Attempt Error", # have to add in translations later
                    "Failed to set animated wallpaper. Aborting operation.", # have to add in translations later
                )
                self.stop()
                return
        
        refresh_exe = os.path.join(self.tools_path, "refresh.exe")
        run_and_forget_silent([refresh_exe, f"0x{view_id}"])
        logging.info("Launched refresh.exe")

    def run_optional_tools(self):
        if get_windows_version() == "Windows11":
            self._run_refresh()

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

        elif sys.platform.startswith("win") and self.current_is_video:
            self._stop_windows()

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

            for idx, _ in enumerate(monitors):
                cmd = self._build_mpv_cmd(video_path, idx)
                run_and_forget_silent(cmd, cwd=mpv_cwd)

                self._mpv_ipc_pipes.append(f"mpv_wallpaper_{idx}")
                time.sleep(0.25)

            add_cmd = [
                str(self.weebp_path),
                "add",
                "--wait",
                "--fullscreen",
                "--class",
                "mpv",
            ]
            
            run_and_forget_silent(add_cmd, cwd=mpv_cwd)

            # 🔴 WAIT UNTIL IPC EXISTS + PLAYBACK STARTED
            if not self._wait_for_mpv_ready():
                logging.warning("mpv did not become ready in time")

            # ✅ NOW SAFE
            self.run_optional_tools()



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
    def get_view_id(self) -> str:
        try:
            proc = subprocess.run(
                [str(self.weebp_path), "ls"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=0x08000000,
            )
        except Exception:
            return "0"
        logging.debug("Result of 'weebp ls': %s", proc.stdout.strip())
        match = re.search(r"\[([0-9A-Fa-f]{8})\].*?mpv", proc.stdout)
        return match.group(1) if match else "0"

    # ---------------------------------------------------------
    #  MPV COMMAND BUILDER
    # ---------------------------------------------------------
    def _build_mpv_cmd(self, video_path: str, screen_index: int):
        return [
            str(self.weebp_path),
            "run",
            "mpv",
            video_path,
            f"--screen={screen_index}",
            "--fullscreen",
            "--no-border",
            "--panscan=1.0",
            "--loop=inf",
            "--keep-open=yes",
            "--hwdec=auto-safe",
            "--no-audio",
            "--no-osd-bar",
            "--osd-level=0",
            f"--input-ipc-server=\\\\.\\pipe\\mpv_wallpaper_{screen_index}",
        ]

    def _wait_for_mpv_ready(self, timeout=6.0) -> bool:
        start = time.time()

        while time.time() - start < timeout:
            all_ready = True

            for pipe in self._mpv_ipc_pipes:
                ok = self._mpv_ipc(
                    pipe,
                    ["get_property", "time-pos"],
                    silent=True
                )
                if not ok:
                    all_ready = False
                    break

            if all_ready:
                logging.info("mpv playback confirmed")
                return True

            time.sleep(0.1)

        return False
# ============================================================

