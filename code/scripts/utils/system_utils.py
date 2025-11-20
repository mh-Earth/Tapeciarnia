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
import requests
import logging
import json
from PySide6.QtWidgets import QApplication
from PIL import Image

# logging = logging.getlogging()
# logging.setLevel(logging.ERROR)


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
    Set wallpaper on Windows (multi-monitor supported via stitching)
    and on Linux GNOME. The wallpaper is resized to completely fill
    each monitor (no empty space). This function is self-contained.
    """
    wallpaper_path = Path(path)

    # Validate the path
    if not wallpaper_path.exists():
        logging.error("Wallpaper file not found: %s", wallpaper_path)
        return False

    try:
        # === WINDOWS ===
        if sys.platform.startswith("win"):
            try:
                import ctypes
                from PIL import Image
                from screeninfo import get_monitors

                logging.info("Applying Windows multi-monitor wallpaper")

                # Get monitor information
                monitors = get_monitors()
                if not monitors:
                    logging.error("No monitors detected")
                    return False

                # Calculate full stitched wallpaper size
                total_width = sum(m.width for m in monitors)
                max_height = max(m.height for m in monitors)

                stitched_wallpaper = Image.new("RGB", (total_width, max_height))
                source_img = Image.open(wallpaper_path)

                # Helper: Resize image to cover target area like CSS "background-size: cover"
                def resize_cover(img, target_w, target_h):
                    src_w, src_h = img.size
                    scale = max(target_w / src_w, target_h / src_h)
                    new_size = (int(src_w * scale), int(src_h * scale))
                    resized = img.resize(new_size, Image.LANCZOS)
                    # Center crop
                    x1 = (resized.width - target_w) // 2
                    y1 = (resized.height - target_h) // 2
                    return resized.crop((x1, y1, x1 + target_w, y1 + target_h))

                # Build stitched wallpaper
                offset_x = 0
                for m in monitors:
                    img_resized = resize_cover(source_img, m.width, m.height)
                    stitched_wallpaper.paste(img_resized, (offset_x, 0))
                    offset_x += m.width

                # Save stitched wallpaper as BMP (required by Windows API)
                final_path = wallpaper_path.parent / "wallpaper_stitched.bmp"
                stitched_wallpaper.save(final_path, format="BMP")

                SPI_SETDESKWALLPAPER = 20
                result = ctypes.windll.user32.SystemParametersInfoW(
                    SPI_SETDESKWALLPAPER, 0, str(final_path), 3
                )

                if result:
                    logging.info("Wallpaper successfully applied (Windows)")
                    return True
                else:
                    logging.error("SystemParametersInfoW failed")
                    return False

            except Exception as e:
                logging.error("Windows wallpaper error: %s", e, exc_info=True)
                return False

        # === LINUX (GNOME) ===
        elif sys.platform.startswith("linux"):
            import subprocess

            logging.info("Applying Linux GNOME wallpaper")

            uri = f"file://{wallpaper_path.resolve()}"

            try:
                result = subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri],
                    capture_output=True, text=True
                )

                if result.returncode != 0:
                    logging.error("gsettings error: %s", result.stderr.strip())
                    return False

                logging.info("Linux wallpaper applied successfully")
                return True

            except FileNotFoundError:
                logging.error("gsettings not found - unsupported desktop environment")
                return False
            except Exception as e:
                logging.error("Linux wallpaper error: %s", e, exc_info=True)
                return False

        else:
            logging.warning("Unsupported OS for wallpaper: %s", sys.platform)
            return False

    except Exception as e:
        logging.error("Unexpected wallpaper error: %s", e, exc_info=True)
        return False

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



def fetch_shuffled_wallpaper(width: int, height: int, is_animated: bool = False,lang:str="pl") -> str | None:
    """
    Fetches a shuffled wallpaper download URL from the server using a POST request.

    Args:
        width (int): Device width in pixels.
        height (int): Device height in pixels.
        is_animated (bool): True for animated wallpapers (all_mp4), False for static (all).

    Returns:
        str | None: The wallpaper download URL if successful, otherwise None.
    """
    BASE_URL = "https://tapeciarnia.pl/program/wybierz_tapete_2025.php"
    # 1. Determine the 'pokaz' parameter based on the type of wallpaper
    pokaz_value = "all_mp4" if is_animated else "all"
    
    # 2. Construct the full URL with GET parameters (pokaz, x, y)
    # Note: Although the user wants POST for variables, the base structure
    # of the URL provided already includes these as GET parameters. 
    # We will send the data in the POST body for robustness, but structure the URL 
    # as provided by the user's example.
    url = f"{BASE_URL}?pokaz={pokaz_value}&x={width}&y={height}"

    # 3. Define the data to be sent via POST (optional, but good practice)
    # Since the user explicitly mentioned sending variables via POST, we can
    # place the critical data (or redundancy) in the body.
    post_data = {
        'x': width,
        'y': height,
        'pokaz': pokaz_value,
        'lang': lang
    }

    logging.info(f"Requesting shuffle URL. Animated: {is_animated}. Dims: {width}x{height}")
    logging.debug(f"API URL: {url}")
    logging.debug(f"POST Data: {post_data}")

    try:
        # 4. Make the POST request
        response = requests.post(
            url, 
            data=post_data,
            timeout=10 # Set a reasonable timeout
        )
        
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status() 

        # 5. Check the Content Type and attempt JSON parsing
        if 'application/json' in response.headers.get('Content-Type', ''):
            data = response.json()
            
            # Assuming the JSON response structure contains a key like 'url' or 'download_link'
            # Adjust the key 'url' based on the actual response structure from the API
            download_url:str = data.get('url') 
            

            if not is_animated:
                if data.get("type") == "img":
                    return download_url
                else:
                    return fetch_shuffled_wallpaper(width=width,height=height,is_animated=is_animated,lang=lang)

            elif data.get("type") == "mp4":
                logging.info(f"Successfully fetched shuffle URL: {download_url}")
                return download_url
            
            else:
                logging.error(f"JSON response is missing the 'url' key. Full response: {data}")
                return None
        else:
            logging.error(f"API response was not JSON. Status: {response.status_code}. Content Type: {response.headers.get('Content-Type')}")
            return None

    except requests.exceptions.Timeout:
        logging.error("API request timed out (10 seconds).")
        return None
    except requests.exceptions.ConnectionError:
        logging.error("API connection error. Check internet connection and firewall.")
        return None
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error occurred: {e}. Status: {response.status_code}")
        return None
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON response from the server.")
        return None
    except Exception as e:
        logging.critical(f"An unexpected error occurred during API call: {e}")
        return None

def gen_name_from_url(url:str) -> str:
    return url.split("/")[-1]



# --- Example of How to Use ---
if __name__ == '__main__':
    # Static Wallpaper Shuffle
    static_url = gen_name_from_url(fetch_shuffled_wallpaper(1920, 1080, is_animated=False))
    print(f"Static Shuffle URL: {static_url}")

    # Animated Wallpaper Shuffle
    animated_url = fetch_shuffled_wallpaper(1920, 1080, is_animated=True)
    print(f"Animated Shuffle URL: {animated_url}")

# Log module initialization
# logging.debug("System utilities module initialized")
