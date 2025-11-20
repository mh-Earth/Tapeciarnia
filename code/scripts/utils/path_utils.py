# utils/path_utils.py
import platform
import subprocess
import json
import sys
import os
import logging
from pathlib import Path


def get_app_root():
    """
    Determines the path of the running application/script's directory, 
    handling both source code and bundled executables.
    """
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).resolve()
    else:
        base_path = Path(sys.argv[0]).resolve()
    return base_path.parent

# Base paths
BASE_DIR = get_app_root()
ROOT_DIR = BASE_DIR.parent.parent
CONFIG_PATH = ROOT_DIR / "config.json"

# Collection structure
def get_collections_folder() -> Path:
    """Return the main collection folder for all wallpapers"""
    home = Path.home()
    collection_dir = home / "Pictures" / "Tapeciarnia"
    collection_dir.mkdir(parents=True, exist_ok=True)
    return collection_dir

COLLECTION_DIR = get_collections_folder()
FAVS_DIR = COLLECTION_DIR / "Favorites"
SAVES_DIR = COLLECTION_DIR / "Saves"

# Ensure folders exist
for d in (COLLECTION_DIR,SAVES_DIR):
    d.mkdir(parents=True, exist_ok=True)

TMP_DOWNLOAD_FILE = COLLECTION_DIR / "download_path.tmp"
TRANSLATIONS_DIR = BASE_DIR / "code" / "scripts" / "translations"

# Config file init
if not CONFIG_PATH.exists():
    CONFIG_PATH.write_text(json.dumps({}), encoding="utf-8")

# Executable paths
def get_mpv_path() -> Path:
    """Get MPV executable path"""
    candidates = [
        BASE_DIR / "bin" / "mpv" / "mpv.exe",
        BASE_DIR / "bin" / "tools" / "mpv.exe",
        BASE_DIR / "bin" / "mpv.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None

def get_weebp_path() -> Path:
    """Get weebp executable path for Windows wallpaper"""
    candidates = [
        BASE_DIR / "bin" / "weebp" / "wp.exe",
        BASE_DIR / "bin" / "tools" / "wp.exe",
        BASE_DIR / "bin" / "wp.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None

def get_style_path() -> Path:
    """Get style file path"""
    return BASE_DIR / "ui" / "style" / "style.qss"

def get_bin_path() -> Path:
    """Get binary folder path"""
    return BASE_DIR / "bin" 

def get_tools_path() -> Path:
    """Get tools folder path"""
    return BASE_DIR / "bin" / "tools"

# Folder opening functionality
def open_folder_in_explorer(folder_path: Path):
    """Open folder in system file explorer"""
    try:
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux and other UNIX-like
            subprocess.run(["xdg-open", folder_path])
        return True
    except Exception as e:
        logging.error(f"Failed to open folder {folder_path}: {e}")
        return False

def get_folder_for_source(source_type: str) -> Path:
    """Get the corresponding folder path for a source type"""
    folder_map = {
        "favorites": FAVS_DIR,
        "added": SAVES_DIR,
        "super": SAVES_DIR,  # Fallback for super wallpaper
        "all": SAVES_DIR,
        "save": SAVES_DIR
    }
    return folder_map.get(source_type, COLLECTION_DIR)

def get_folder_for_range(range_type: str) -> Path:
    """Get the corresponding folder path for a range type"""
    folder_map = {
        "all": SAVES_DIR,
        "wallpaper": SAVES_DIR,
        "mp4": SAVES_DIR
    }
    return folder_map.get(range_type, COLLECTION_DIR)

def get_icon_absolute_path(icon_filename):
    """
    Returns the absolute path to a specific icon file within the bundled assets.
    """
    return os.path.join(BASE_DIR, 'ui', 'icons', icon_filename)

# Backward compatibility
get_app_root = get_app_root
get_weebp_path = get_weebp_path
get_mpv_path = get_mpv_path
get_style_path = get_style_path
