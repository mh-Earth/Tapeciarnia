import sys
import subprocess
import logging
import platform
import os
import re
import time

from PySide6.QtWidgets import QMessageBox

from utils.system_utils import which, set_static_desktop_wallpaper
from utils.path_utils import get_weebp_path, get_mpv_path, get_tools_path
from utils.command_handler import run_and_forget_silent


class WallpaperController:
    def __init__(self):
        self.player_procs = []
        self.current_is_video = False

        # Cached paths
        self.tools_path = get_tools_path()
        self.weebp_path = get_weebp_path()
        self.mpv_path = get_mpv_path()

        # Refresh limits
        self.refresh_limit = 6
        self.refresh_count = 0

        if not self._check_weebp_and_mpv():
            QMessageBox.critical(None, "Error",
                                 "Weebp or MPV executable not found. Video wallpaper functionality may be limited.")
            sys.exit(1)

    # ---------------------------------------------------------
    #  Utility Checks
    # ---------------------------------------------------------
    def _check_weebp_and_mpv(self) -> bool:
        return (
            self.weebp_path is not None and self.weebp_path.exists() and
            self.mpv_path is not None and self.mpv_path.exists()
        )

    # ---------------------------------------------------------
    #  Optional Tools
    # ---------------------------------------------------------
    def _run_auto_pause(self):
        exe_path = os.path.join(self.tools_path, "autoPause.exe")
        run_and_forget_silent([exe_path])
        logging.info("Launched autoPause.exe")

    def _run_refresh(self):
        """Repeatedly checks for a valid view ID before refreshing."""
        view_id = self.get_view_id()

        if view_id == "0" and self.refresh_count < self.refresh_limit:
            self.refresh_count += 1
            time.sleep(1)
            return self._run_refresh()

        refresh_exe = os.path.join(self.tools_path, "refresh.exe")
        run_and_forget_silent([refresh_exe, f"0x{view_id}"])
        logging.info("Launched refresh.exe")

    def run_optional_tools(self):
        # self._run_auto_pause()
        self._run_refresh()

    # ---------------------------------------------------------
    #  STOP
    # ---------------------------------------------------------
    def stop(self):
        logging.info("Stopping wallpaper processes...")

        if sys.platform.startswith("linux"):
            for proc in ("xwinwrap", "mpv"):
                subprocess.call(
                    f"pkill -f {proc}", shell=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

        elif sys.platform.startswith("win") and self.current_is_video:
            self._stop_windows()

        self.current_is_video = False
        logging.info("All wallpaper processes stopped")

    def _stop_windows(self):
        self._clear_playlist()

        kill_list = ["mpv.exe", "wp.exe", "autopause.exe", "refresh.exe"]

        for proc in kill_list:
            try:
                subprocess.run(["taskkill", "/F", "/IM", proc, "/T"],
                               check=False,
                               creationflags=0x08000000,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except Exception:
                pass

    # ---------------------------------------------------------
    #  VIDEO STARTERS
    # ---------------------------------------------------------
    def start_video(self, video_path: str):
        logging.debug(f"Current is video: {self.current_is_video}")

        if platform.system() == "Windows":
            if self.current_is_video:
                return self._play_next_video(video_path)

            self.current_is_video = True
            return self._start_video_windows(video_path)

        if sys.platform.startswith("linux"):
            return self._start_video_linux(video_path)

        return self._start_video_fallback(video_path)

    # ---------------------------------------------------------
    #  Playlist Control (Windows)
    # ---------------------------------------------------------
    def _clear_playlist(self):
        """Clears MPV playlist via weebp."""
        cmd = [str(self.weebp_path), "mpv", "playlist-clear"]
        run_and_forget_silent(cmd, cwd=self.mpv_path.parents[0])
        time.sleep(0.5)

    def _play_next_video(self, video_path):
        """Append & switch to next."""
        base_cmd = str(self.weebp_path)

        run_and_forget_silent(
            [base_cmd, "mpv", "loadfile", video_path, "append"],
            cwd=self.mpv_path.parents[0]
        )
        time.sleep(0.2)

        run_and_forget_silent(
            [base_cmd, "mpv", "playlist-next"],
            cwd=self.mpv_path.parents[0]
        )

    # ---------------------------------------------------------
    #  WINDOWS VIDEO START
    # ---------------------------------------------------------
    def _start_video_windows(self, video_path: str):
        try:
            weebp = str(self.weebp_path)
            mpv_cwd = self.mpv_path.parents[0]

            mpv_cmd = [
                weebp, "run", "mpv", video_path,
                "--input-ipc-server=\\\\.\\pipe\\mpvsocket",
                "--fullscreen",
                "--panscan=1.0",
                "--no-border",
                "--geometry=100%x100%",
                "--autofit=100%x100%",
                "--keep-open=yes",
                "--loop=inf"
            ]

            add_cmd = [
                weebp, "add", "--wait",
                "--fullscreen", "--class", "mpv"
            ]

            run_and_forget_silent(mpv_cmd, cwd=mpv_cwd)
            time.sleep(0.6)

            run_and_forget_silent(add_cmd, cwd=mpv_cwd)
            time.sleep(0.4)

            self.run_optional_tools()
            logging.info("MPV wallpaper successfully attached.")
        except Exception as e:
            logging.error(f"Failed to start wallpaper: {e}")

    # ---------------------------------------------------------
    #  LINUX VIDEO START
    # ---------------------------------------------------------
    def _start_video_linux(self, video_path):
        xwinwrap = which("xwinwrap")
        mpv = which("mpv")

        if xwinwrap and mpv:
            try:
                cmd = (
                    f"{xwinwrap} -ov -fs -- "
                    f"{mpv} --loop --no-audio --no-osd-bar --wid=WID '{video_path}'"
                )
                p = subprocess.Popen(cmd, shell=True, executable="/bin/bash",
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                self.player_procs.append(p)
                return
            except Exception as e:
                logging.error(f"xwinwrap failed: {e}")

        if mpv:
            p = subprocess.Popen(
                [mpv, "--loop", "--no-audio", "--no-osd-bar", "--fullscreen", "--no-border", video_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.player_procs.append(p)
            return

        raise RuntimeError("No suitable video wallpaper backend (xwinwrap/mpv).")

    # ---------------------------------------------------------
    #  FALLBACK VIDEO START
    # ---------------------------------------------------------
    def _start_video_fallback(self, video_path):
        mpv = which("mpv")
        if not mpv:
            raise RuntimeError(f"Unsupported platform: {sys.platform}")

        subprocess.Popen(
            [mpv, "--loop", "--no-audio", "--fullscreen", "--no-border", video_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ---------------------------------------------------------
    #  STATIC IMAGE
    # ---------------------------------------------------------
    def start_image(self, image_path):
        try:
            set_static_desktop_wallpaper(image_path)
        except Exception as e:
            logging.error(f"Failed to set wallpaper: {e}")
            raise

        if self.current_is_video:
            self.stop()

        self.current_is_video = False

    # ---------------------------------------------------------
    #  VIEW ID PARSING (Windows)
    # ---------------------------------------------------------
    def get_view_id(self) -> str:
        try:
            proc = subprocess.run(
                [self.weebp_path, "ls"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except Exception:
            return "0"

        output = proc.stdout
        logging.info(f"wp.exe ls output:\n{output}")

        match = re.search(r'\[([0-9A-Fa-f]{8})\].*?mpv', output)
        return match.group(1) if match else "0"
