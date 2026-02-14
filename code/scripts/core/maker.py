
from PySide6.QtCore import QThread, Signal
import logging
import subprocess
from pathlib import Path
from utils.path_utils import (
    get_ffmpeg_path,
    get_ffprobe_path
)
CREATE_NO_WINDOW = 0x08000000 
import json


class WallpaperMaker(QThread):
    progress = Signal(str)  #message
    done = Signal(Path) # path to modified file
    error = Signal(str) # message
    success = Signal(Path)
    '''
    For zero loss
    crf = 0
    preset = "slow" | "veryfast"
    '''
    def __init__(self, input_video:str,output_video:str,copies:int,target_height:int,crf:int=0,preset: str = "slow"):
        super().__init__()
        self.input_video: str = input_video
        self.output_video: str = output_video
        self.copies: int = copies
        self.target_height: int = target_height
        self.crf: int = crf
        self.preset: str = preset
        logging.debug(f"Initialting maker instance with input:{input_video} output:{output_video} copies:{copies}",)
        

    # prevent running more then one intance of this class 
    def run(self) -> Path:
        """
        Horizontally stack the same video N times with
        perfect scaling, FPS normalization, and no visible quality loss.
        """
        try:
            # Check how many functions are connected to the signals'
            progress_count = self.receivers("progress(str)")
            done_count = self.receivers("done(Path)")
            success_count = self.receivers("success(Path)")
            error_count = self.receivers("error(str)")

            logging.debug(f"progress: {progress_count} done: {done_count} success: {success_count} error: {error_count}")

            if self.copies < 2:
                raise ValueError("copies must be >= 2")

            input_path = Path(self.input_video).resolve()
            output_path = Path(self.output_video).resolve()

            if not input_path.exists():
                raise FileNotFoundError(input_path)

            self.progress.emit("Analyzing video…")
            logging.debug("Analyzing video...")

            info = self.probe_video(input_path)
            src_fps = self.parse_fps(info["r_frame_rate"])

            target_h = self.target_height
            target_h = target_h - (target_h % 2)  # even height

            # Build filter graph
            split_labels = "".join(f"[v{i}]" for i in range(self.copies))
            scaled_labels = "".join(f"[v{i}s]" for i in range(self.copies))
            hstack_inputs = "".join(f"[v{i}s]" for i in range(self.copies))

            scale_steps = ";".join(
                f"[v{i}]scale=-2:{target_h}:flags=lanczos,setsar=1[v{i}s]"
                for i in range(self.copies)
            )

            filter_complex = (
                f"[0:v]"
                f"fps={src_fps},"
                f"scale=trunc(iw/2)*2:trunc(ih/2)*2,"
                f"split={self.copies}{split_labels};"
                f"{scale_steps};"
                f"{hstack_inputs}"
                f"hstack=inputs={self.copies}[v]"
            )

            cmd = [
                str(get_ffmpeg_path()),
                "-y",
                "-nostats",
                "-progress", "pipe:1",
                "-i", str(input_path),
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-an",
                "-c:v", "libx264",
                "-crf", str(self.crf),
                "-preset", self.preset,
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(output_path),
            ]


            duration = self.get_video_duration(input_path)

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                bufsize=1,
            )

            logging.info(f"Applying wallpapaer...")
            def emit_progress(p):
                self.progress.emit(f"Applying wallpapaer...{p}%")

            self.read_ffmpeg_progress(proc, duration, emit_progress)

            proc.wait()

            logging.debug(f"Proc return code {proc.returncode}")
            if proc.returncode != 0:
                raise RuntimeError("FFmpeg failed")
            


            self.progress.emit("Wallpaper ready")
            logging.debug(f"Panoramic wallpaper ready from {input_path}")
            self.done.emit(output_path)
            self.success.emit(output_path)
            return output_path

        except Exception as e:
            msg = f"Wallpaper modification failed: {e}"
            # logging.debug(f"Failed to create oanoramic wallpaper from {input_path}")
            logging.error(msg, exc_info=True)
            self.error.emit(msg)
            raise



    def parse_fps(self,r_frame_rate: str) -> float:
        num, den = r_frame_rate.split("/")
        return float(num) / float(den)

    def probe_video(self,path: Path) -> dict:
        cmd = [
            str(get_ffprobe_path()),
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-of", "json",
            str(path)
        ]
        out = subprocess.check_output(cmd, creationflags=CREATE_NO_WINDOW)
        return json.loads(out)["streams"][0]

    def get_video_duration(self,path: Path) -> float:
        cmd = [
            str(get_ffprobe_path()),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        out = subprocess.check_output(cmd, creationflags=CREATE_NO_WINDOW)
        return float(out.strip())


    def read_ffmpeg_progress(self, proc, duration, on_progress):
        """
        Reads FFmpeg -progress pipe:1 output and emits % updates.
        Safely handles 'N/A' values.
        """
        last_percent = -1
        logging.debug("ffmpeg progress reading started...")
        while True:
            line = proc.stdout.readline()
            if not line:
                break

            line = line.strip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            if key == "out_time_ms":
                if value == "N/A":
                    continue

                try:
                    seconds = int(value) / 1_000_000
                except ValueError:
                    continue
                percent = round((seconds / duration) * 100, 1)
                percent = max(0, min(100, percent))

                # avoid spamming the same % over and over
                if percent != last_percent:
                    last_percent = percent
                    on_progress(percent)

            elif key == "progress" and value == "end":
                on_progress(100)
                break
