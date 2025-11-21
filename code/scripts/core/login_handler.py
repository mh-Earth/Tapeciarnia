import json
import requests
from PySide6.QtCore import QThread, Signal
import logging
import urllib.parse


'''
payload = {
"login": "gmail", # aka email
"key": "36c202e3ff667dcdf58b2c9fd07a5c8a", # aka password
"lang": "pl"
}

url = https://tapeciarnia.pl/program/login_2025.php
?login=gmail&key=36c202e3ff667dcdf58b2c9fd07a5c8a&lang=pl

access_token
refresh_token (optional)
user_id
expires_at (optional)

'''

class LoginWorker(QThread):
    """Runs a login API request in a background thread (non-blocking)."""

    success = Signal(dict)      # Emits parsed JSON
    failed = Signal(str)        # Emits error message

    def __init__(self, url: str=None, payload: dict=None,method:str="POST",parent=None):
        super().__init__(parent)
        self.url = url
        self.payload = payload
        self._running = True
        self.method = method
        
    def run(self):
        if not self._running:
            return

        try:

            if self.method.lower() == "post":
                response = requests.post(
                    self.url,
                    json=self.payload,
                    timeout=12
                )

                if response.status_code != 200:
                    self.failed.emit(f"HTTP {response.status_code}")
                    return

                try:
                    data = response.json()
                except json.JSONDecodeError:
                    self.failed.emit("Invalid JSON response")
                    return

                self.success.emit(data)


            elif self.method.lower() == "get":
                query_string = urllib.parse.urlencode(self.payload)
                full_url = f"{self.url}?{query_string}"

                response = requests.get(full_url,timeout=12)


                if response.status_code != 200:
                    self.failed.emit(f"HTTP {response.status_code}")
                    return

                try:
                    data = response.json()
                except json.JSONDecodeError:
                    self.failed.emit("Invalid JSON response")
                    return

                self.success.emit(data)

            else:
                logging.error("Invalid login method")
            

        except requests.Timeout:
            self.failed.emit("Request timed out")
        except requests.ConnectionError:
            self.failed.emit("Network connection error")
        except Exception as e:
            self.failed.emit(str(e))

    def stop(self):
        """Optional: call before start() if you want to cancel."""
        self._running = False
    
    # def logout(self):
    #     Config().clear_session()
    #     self.close()
    #     LoginWindow().show()




class TokenValidateThread(QThread):
    valid = Signal()
    invalid = Signal(str)

    def __init__(self, token: str, parent=None):
        super().__init__(parent)
        self.token = token

    def run(self):
        url = "https://your.api/validate"

        try:
            r = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5
            )

            if r.status_code == 200:
                logging.info("Token validated successfully")
                self.valid.emit()
                return

            msg = f"Token invalid: HTTP {r.status_code}"
            logging.warning(msg)
            self.invalid.emit(msg)

        except Exception as e:
            logging.error(f"Token validation exception: {e}")
            self.invalid.emit(str(e))
