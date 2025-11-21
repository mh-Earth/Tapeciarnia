from PySide6.QtCore import QThread, Signal
import logging,requests,json
from PySide6.QtWidgets import QApplication
from utils.singletons import get_config
import socket

class Shuffler(QThread):

    success = Signal(str)
    failed = Signal(str)

    def __init__(self, animated:bool, parent = None):
        super().__init__(parent)
        self.x , self.y = self.get_primary_screen_dimensions()        
        self.config = get_config()
        self.isAnimated = animated

    def run(self):
        self.fetch_shuffled_wallpaper(self.x,self.y,self.isAnimated,self.config.get_language())

    def is_connected_to_internet(self,host="8.8.8.8", port=53, timeout=3):
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


    def get_primary_screen_dimensions(self) -> tuple[int, int]:
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


    def fetch_shuffled_wallpaper(self,width: int, height: int, is_animated: bool = False,lang:str="pl") -> str | None:
        """
        Fetches a shuffled wallpaper download URL from the server using a POST request.

        Args:
            width (int): Device width in pixels.
            height (int): Device height in pixels.
            is_animated (bool): True for animated wallpapers (all_mp4), False for static (all).

        Returns:
            str | None: The wallpaper download URL if successful, otherwise None.
        """
        if not self.is_connected_to_internet():
            self.failed.emit("Couldn't connecto to internet\nCheck your connection")
            return
        
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
                        self.success.emit(download_url)
                    else:
                        self.fetch_shuffled_wallpaper(width=width,height=height,is_animated=is_animated,lang=lang)

                elif data.get("type") == "mp4":
                    self.success.emit(download_url)
                    logging.info(f"Successfully fetched shuffle URL: {download_url}")
                
                else:
                    self.failed.emit(f"JSON response is missing the 'url' key. Full response: {data}")
                    logging.error(f"JSON response is missing the 'url' key. Full response: {data}")
            else:
                self.failed.emit(f"API response was not JSON. Status: {response.status_code}. Content Type: {response.headers.get('Content-Type')}")
                logging.error(f"API response was not JSON. Status: {response.status_code}. Content Type: {response.headers.get('Content-Type')}")
                return None

        except requests.exceptions.Timeout:
            self.failed.emit("API request timed out (10 seconds).")
            logging.error("API request timed out (10 seconds).")
            return None
        except requests.exceptions.ConnectionError:
            self.failed.emit("API connection error. Check internet connection and firewall.")
            logging.error("API connection error. Check internet connection and firewall.")
            return None
        except requests.exceptions.HTTPError as e:
            self.failed.emit(f"HTTP error occurred: {e}. Status: {response.status_code}")
            logging.error(f"HTTP error occurred: {e}. Status: {response.status_code}")
            return None
        except json.JSONDecodeError:
            self.failed.emit("Failed to decode JSON response from the server.")
            logging.error("Failed to decode JSON response from the server.")
            return None
        except Exception as e:
            self.failed.emit(f"An unexpected error occurred during API call: {e}")
            logging.critical(f"An unexpected error occurred during API call: {e}")
            return None
