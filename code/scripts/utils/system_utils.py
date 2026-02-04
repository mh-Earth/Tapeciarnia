import sys
import subprocess
import locale
import shutil
import ctypes
import logging
from pathlib import Path
from typing import Optional
import socket
import os
import logging
from PySide6.QtWidgets import QApplication
from utils.path_utils import FAVS_DIR

import os
from urllib.parse import urlparse, unquote

from ctypes import wintypes, windll, byref
import ctypes


MDT_EFFECTIVE_DPI = 0

def isBundle() -> bool:
    """
    Determines the path of the running application/script's directory, 
    handling both source code and bundled executables.
    """
    if getattr(sys, 'frozen', False):
        return True
    else:
        return False

def resource_path(relative_path: str) -> Path:
    """
    Get the absolute path to a resource, compatible with PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(relative_path)


def which(cmd: str) -> Optional[str]:
    """Find executable in system PATH with logging"""
    logging.debug(f"Searching for executable in PATH: {cmd}")
    
    try:
        result = shutil.which(cmd)
        if result:
            logging.debug(f"Executable found: {result}")
        else:
            logging.debug(f"Executable not found in PATH: {cmd}")
        return result
    except Exception as e:
        logging.error(f"Error searching for executable '{cmd}': {e}")
        return None


def current_system_locale() -> str:
    """Get current system locale with logging"""
    logging.debug("Detecting system locale")
    
    try:
        loc = locale.getdefaultlocale()[0]
        logging.debug(f"Raw locale detected: {loc}")
        
        if loc:
            language_code = loc.split("_")[0]
            logging.info(f"System locale determined: {language_code}")
            return language_code
        else:
            logging.warning("No locale detected, defaulting to 'en'")
            return "en"
            
    except Exception as e:
        logging.error(f"Error detecting system locale: {e}", exc_info=True)
        logging.warning("Defaulting to 'en' due to locale detection error")
        return "en"


def get_current_desktop_wallpaper() -> Optional[str]:
    """Get current desktop wallpaper path with comprehensive logging"""
    logging.debug("Retrieving current desktop wallpaper")
    
    if sys.platform.startswith("win"):
        logging.debug("Windows platform detected for wallpaper retrieval")
        try:
            buf = ctypes.create_unicode_buffer(260)
            SPI_GETDESKWALLPAPER = 0x0073
            logging.debug("Calling SystemParametersInfoW for wallpaper")
            
            result = ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 260, buf, 0)
            
            if result and buf.value:
                wallpaper_path = buf.value
                logging.info(f"Current Windows wallpaper: {wallpaper_path}")
                return wallpaper_path
            else:
                logging.warning("SystemParametersInfoW failed or returned empty wallpaper path")
                return None
                
        except Exception as e:
            logging.error(f"Error retrieving Windows wallpaper: {e}", exc_info=True)
            return None
            
    elif sys.platform.startswith("linux"):
        logging.debug("Linux platform detected for wallpaper retrieval")
        try:
            logging.debug("Attempting to get wallpaper via gsettings")
            res = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
                capture_output=True, 
                text=True,
                timeout=10  # Add timeout to prevent hanging
            )
            
            if res.returncode == 0:
                val = res.stdout.strip().strip("'\"")
                logging.debug(f"Raw gsettings output: {val}")
                
                if val.startswith("file://"):
                    wallpaper_path = val[7:]
                    logging.info(f"Current Linux wallpaper: {wallpaper_path}")
                    return wallpaper_path
                elif val:
                    logging.info(f"Current Linux wallpaper (non-file URI): {val}")
                    return val
                else:
                    logging.warning("gsettings returned empty wallpaper URI")
                    return None
            else:
                logging.error(f"gsettings command failed - returncode: {res.returncode}, stderr: {res.stderr.strip()}")
                return None
                
        except subprocess.TimeoutExpired:
            logging.error("gsettings command timed out while retrieving wallpaper")
            return None
        except FileNotFoundError:
            logging.error("gsettings command not found - likely not running on GNOME desktop")
            return None
        except Exception as e:
            logging.error(f"Error retrieving Linux wallpaper: {e}", exc_info=True)
            return None
    else:
        logging.warning(f"Unsupported platform for wallpaper retrieval: {sys.platform}")
        return None
    


def set_static_desktop_wallpaper(path: str) -> bool:
    """
    Set wallpaper on:
    - Windows (multi-monitor, correct positioning, span mode, DPI-safe)
    - Windows 11 per-monitor (optional fallback)
    - Linux GNOME (light + dark)

    Image is resized using CSS-like "cover" behavior per monitor.
    """
    wallpaper_path = Path(path)

    if not wallpaper_path.exists():
        logging.error("Wallpaper file not found: %s", wallpaper_path)
        return False

    try:
        # =========================
        # WINDOWS
        # =========================
        if sys.platform.startswith("win"):
            import ctypes
            from PIL import Image
            from screeninfo import get_monitors
            import winreg

            logging.info("Applying Windows multi-monitor wallpaper")

            # -------------------------
            # Get monitors (with x/y)
            # -------------------------
            monitors = get_monitors()
            if not monitors:
                logging.error("No monitors detected")
                return False

            # -------------------------
            # Virtual desktop bounds
            # -------------------------
            min_x = min(m.x for m in monitors)
            min_y = min(m.y for m in monitors)
            max_x = max(m.x + m.width for m in monitors)
            max_y = max(m.y + m.height for m in monitors)

            virtual_width = max_x - min_x
            virtual_height = max_y - min_y

            stitched = Image.new("RGB", (virtual_width, virtual_height))
            source_img = Image.open(wallpaper_path).convert("RGB")

            # -------------------------
            # Resize helper (cover)
            # -------------------------
            def resize_cover(img, target_w, target_h):
                src_w, src_h = img.size
                scale = max(target_w / src_w, target_h / src_h)
                new_size = (int(src_w * scale), int(src_h * scale))
                resized = img.resize(new_size, Image.LANCZOS)
                x1 = (resized.width - target_w) // 2
                y1 = (resized.height - target_h) // 2
                return resized.crop((x1, y1, x1 + target_w, y1 + target_h))

            # -------------------------
            # Paste using real coords
            # -------------------------
            for m in monitors:
                img_resized = resize_cover(source_img, m.width, m.height)
                paste_x = m.x - min_x
                paste_y = m.y - min_y
                stitched.paste(img_resized, (paste_x, paste_y))

            # -------------------------
            # Save BMP (Windows API)
            # -------------------------
            final_path = wallpaper_path.parent / "wallpaper_stitched.bmp"
            stitched.save(final_path, "BMP")

            # -------------------------
            # Force SPAN mode
            # -------------------------
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Control Panel\Desktop",
                    0,
                    winreg.KEY_SET_VALUE
                ) as key:
                    winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "22")  # Span
                    winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
            except Exception:
                logging.warning("Failed to enforce span mode")

            # -------------------------
            # Apply wallpaper
            # -------------------------
            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATEINIFILE = 1
            SPIF_SENDCHANGE = 2

            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                str(final_path),
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )

            if not result:
                logging.error("SystemParametersInfoW failed")
                return False

            logging.info("Wallpaper successfully applied (Windows)")
            return True

        # =========================
        # LINUX (GNOME)
        # =========================
        elif sys.platform.startswith("linux"):
            logging.info("Applying GNOME wallpaper")

            uri = f"file://{wallpaper_path.resolve()}"

            commands = [
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri],
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri],
                ["gsettings", "set", "org.gnome.desktop.background", "picture-options", "zoom"],
            ]

            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logging.error("gsettings error: %s", result.stderr.strip())
                    return False

            logging.info("Wallpaper successfully applied (Linux GNOME)")
            return True

        else:
            logging.warning("Unsupported OS: %s", sys.platform)
            return False

    except Exception as e:
        logging.exception("Unexpected wallpaper error")
        return False

def conver_bytes_to_tmp_path(img_bytes: bytes, filename: str = "current_wallpaper.jpg",ext:str="jpg") -> str:
    """
    Save image/video bytes to a temporary file and return it's path.
    """

    # Create temporary file
    if ext == ".jpg":
        path = FAVS_DIR / filename
    elif ext == ".mp4":
        path = FAVS_DIR / "current_wallpaper.mp4"
    else:
        path = FAVS_DIR / f"current_wallpaper{ext}"


    # Save image
    with open(path, "wb") as f:
        f.write(img_bytes)


    return str(path)


def get_system_info() -> dict:
    """
    Get comprehensive system information for debugging
    
    Returns:
        dict: System information including platform, desktop environment, etc.
    """
    logging.debug("Collecting system information")
    system_info = {
        'platform': sys.platform,
        'python_version': sys.version,
        'executable': sys.executable,
    }
    
    try:
        # Platform-specific information
        if sys.platform.startswith("win"):
            system_info['windows_version'] = f"{sys.getwindowsversion().major}.{sys.getwindowsversion().minor}"
        elif sys.platform.startswith("linux"):
            # Try to detect desktop environment
            de = os.environ.get('XDG_CURRENT_DESKTOP', 'Unknown')
            system_info['desktop_environment'] = de
            system_info['current_wallpaper'] = get_current_desktop_wallpaper()
            
        logging.debug(f"System information collected: {system_info}")
        
    except Exception as e:
        logging.error(f"Error collecting system information: {e}")
        system_info['error'] = str(e)
    
    return system_info


def verify_wallpaper_access() -> bool:
    """
    Verify that wallpaper operations can be performed on this system
    
    Returns:
        bool: True if wallpaper operations are supported, False otherwise
    """
    logging.debug("Verifying wallpaper access capabilities")
    
    if sys.platform.startswith("win"):
        logging.debug("Windows platform supports wallpaper operations")
        return True
    elif sys.platform.startswith("linux"):
        # Check if gsettings is available
        try:
            result = subprocess.run(["which", "gsettings"], capture_output=True, text=True)
            if result.returncode == 0:
                logging.debug("Linux system supports wallpaper operations via gsettings")
                return True
            else:
                logging.warning("Linux system does not have gsettings - wallpaper operations may not work")
                return False
        except Exception as e:
            logging.error(f"Error verifying Linux wallpaper access: {e}")
            return False
    else:
        logging.warning(f"Wallpaper operations not supported on platform: {sys.platform}")
        return False


# Import os for system_info function
def is_connected_to_internet(host="8.8.8.8", port=53, timeout=3):
    """
    Checks if the machine is connected to the internet by attempting to 
    connect to a known stable host (Google's primary DNS server).

    Args:
        host (str): The host to check connectivity against (default is Google DNS).
        port (int): The port to use for the check (default is DNS port).
        timeout (int): The maximum time in seconds to wait for a connection.

    Returns:
        bool: True if connected, False otherwise.
    """
    try:
        # Create a socket object
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Attempt to connect to the host
        s.connect((host, port))
        
        # Connection successful
        s.close()
        logging.info("Internet connection verified successfully.")
        return True
    
    except socket.error as e:
        # Connection failed, indicating no internet access or a firewall block
        logging.warning(f"Internet connection failed check: {e}")
        return False
    except Exception as e:
        # Catch all other potential errors (e.g., DNS resolution failure if host was a name)
        logging.error(f"Unexpected error during connection check: {e}")
        return False


def get_primary_screen_dimensions() -> tuple[int, int]:
    """
    Retrieves the width and height of the primary screen using PySide6's 
    QApplication and QScreen methods.

    Returns:
        tuple[int, int]: (width, height) of the primary screen in pixels.
                         Returns (1920, 1080) as a safe fallback if QApplication is not running.
    """
    try:
        # Get the running QApplication instance
        app = QApplication.instance()
        if not app:
            logging.warning("QApplication instance not found. Returning fallback dimensions.")
            return 1920, 1080
            
        # Get the primary screen object
        screen = app.primaryScreen()
        if screen:
            size = screen.size()
            width = size.width()
            height = size.height()
            logging.info(f"Primary screen dimensions retrieved: {width}x{height}")
            return width, height
        
        logging.warning("Primary screen object not found. Returning fallback dimensions.")
        return 1920, 1080

    except Exception as e:
        logging.error(f"Failed to get screen dimensions: {e}")
        return 1920, 1080 # Safe fallback






def gen_name_from_url(url:str) -> str:
    return url.split("/")[-1]


def find_key_by_value_nested(d, target_value, path=None):
    if path is None:
        path = []

    for k, v in d.items():
        current_path = path + [k]

        if v == target_value:
            return current_path

        if isinstance(v, dict):
            result = find_key_by_value_nested(v, target_value, current_path)
            if result:
                return result

    return None

def get_file_extension_from_url(url: str) -> str:
    """
    Extracts the file extension from a URL.

    Args:
        url (str): The URL string (e.g., "https://example.com/image.jpg?q=1").

    Returns:
        str: The file extension (e.g., ".jpg" or an empty string if none found).
    """
    try:
        # 1. Parse the URL
        # urlparse separates the URL into components (scheme, netloc, path, params, query, fragment)
        parsed_url = urlparse(url)

        # 2. Get the path component
        # The path is the part of the URL that usually contains the filename.
        path = parsed_url.path

        # 3. Unquote the path
        # Decodes URL-encoded characters (e.g., "%20" becomes " ")
        decoded_path = unquote(path)

        # 4. Get the filename and extension
        # os.path.splitext splits the path into a root and an extension.
        # It correctly handles paths without extensions (returns root, "")
        _, ext = os.path.splitext(decoded_path)

        # Return the extension (it includes the dot, e.g., ".jpg")
        # Ensure it's lowercase for standardization
        return ext.lower()

    except Exception as e:
        # Handle potential parsing or decoding errors gracefully
        logging.error(f"Error processing URL '{url}': {e}")
        return ""



def get_windows_version():
    if sys.platform != "win32":
        return "Not Windows"

    version = sys.getwindowsversion()
    build = version.build

    if build >= 22000:
        return "Windows11"
    elif build >= 10240:
        return "Windows10"
    elif build >= 7600:
        return "Windows 7 / 8 / 8.1"
    else:
        return "Older Windows"


def get_monitor_dpi_from_point(x, y):
    # Per-monitor DPI aware (Windows 10/11)
    ctypes.windll.user32.SetProcessDpiAwarenessContext(
        ctypes.c_void_p(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    )

    MONITOR_DEFAULTTONEAREST = 2

    monitor = windll.user32.MonitorFromPoint(
        wintypes.POINT(x, y),
        MONITOR_DEFAULTTONEAREST
    )

    dpi_x = wintypes.UINT()
    dpi_y = wintypes.UINT()

    windll.shcore.GetDpiForMonitor(
        monitor,
        0,  # MDT_EFFECTIVE_DPI
        byref(dpi_x),
        byref(dpi_y)
    )
    logging.debug(f"Monitor DPI at point ({x}, {y}): {dpi_x.value}x{dpi_y.value}")
    return dpi_x.value, dpi_y.value

def get_monitors_dpi_info():

    monitors_dpi = []
    
    user32 = ctypes.windll.user32
    shcore = ctypes.windll.shcore

    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )

    monitors = []
    
    def _monitor_enum_proc(hMonitor, hdc, lprc, lparam):
        rect = lprc.contents
        monitors.append({
            "handle": hMonitor,
            "x": rect.left,
            "y": rect.top,
            "width": rect.right - rect.left,
            "height": rect.bottom - rect.top,
        })
        return True

    user32.EnumDisplayMonitors(
        0,
        0,
        MONITORENUMPROC(_monitor_enum_proc),
        0
    )

    for i, m in enumerate(monitors):
        
        dpi_x, dpi_y = get_monitor_dpi_from_point(m["x"], m["y"])

        scale = dpi_x / 96.0

        monitors_dpi.append(
            {
                "monitor_index": i,
                "position": (m["x"], m["y"]),
                "size": (m["width"], m["height"]),
                "dpi": (dpi_x, dpi_y),
                "ui_scale": scale
            }
        )
        
    return monitors_dpi

# --- Example Usage ---