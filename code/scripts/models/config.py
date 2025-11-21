from PySide6.QtCore import QSettings

from utils.path_utils import CONFIG_PATH
from utils.system_utils import current_system_locale
import logging


class Config:
    def __init__(self):
        logging.debug("Initializing QSettings config backend")

        # Organization + Application name (used as storage path)
        self.settings = QSettings("WallApp", "WallAppDesktop")
        self.ensure_default_domains()
        self.ensure_valid_image_extensions()
        self.ensure_valid_video_extensions()
        logging.info("QSettings backend initialized")

    @staticmethod
    def to_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    # -------- Generic get/set -------- #
    def get(self, key: str, default=None):
        value = self.settings.value(key, default)
        logging.debug(f"Config get → {key} = {value} (default={default})")
        return value

    def set(self, key: str, value):
        self.settings.setValue(key, value)
        logging.debug(f"Config set → {key} = {value}")

    # --------- helpers --------- #
    def get_last_video(self):
        return self.get("last_video")

    def set_last_video(self, path: str):
        self.set("last_video", path)

    def get_scheduler_settings(self):
        enabled:bool = self.get("scheduler_enabled", False)
        source:str = self.get("scheduler_source")
        interval:int = int(self.get("scheduler_interval", 30))
        range_type:str = self.get("scheduler_range_type","all")
        return enabled, source, interval, range_type

    def set_scheduler_settings(self,enabled:bool, source:str, interval:int, range_type:str):
        self.set("scheduler_source", source)
        self.set("scheduler_interval", interval)
        self.set("scheduler_range_type", range_type)
        self.set("scheduler_enabled", enabled)

    def get_scheduler_enabled(self) -> bool:
        # print(self.get("scheduler_enabled_state",False))
        return self.to_bool(self.get("scheduler_enabled_state",False))
        
    def set_scheduler_enabled(self,scheduler_enabled:bool):
        self.set("scheduler_enabled_state",scheduler_enabled)

    def get_language(self):
        lang = self.get("language",current_system_locale())
        return lang

    def set_language(self, lang: str):
        self.set("language", lang)

    def get_range_preference(self):
        return self.get("range_preference", "all")

    def set_range_preference(self, pref: str):
        self.set("range_preference", pref)

    def clear(self):
        logging.warning("Clearing all QSettings entries")
        self.settings.clear()

    def get_interval(self) -> int:
        return self.data.get("interval",30)
    
    def set_interval(self,interval:int) -> None:
        self.set("interval",interval) 

    def set_login(self,login:str):
        self.set("login" ,str(login))
    
    def get_login(self):
        return self.get("login","")
    
    def set_login_key(self,key:str):
        self.set("login_key" ,str(key))
    
    def get_login_key(self) -> str:
        return self.get("login_key","")
    
    def get_login_status(self) -> bool:
        return self.get("isLogin",False)
    
    def set_login_status(self,status:bool) -> None:
        self.set("isLogin",status)
    

    # ---------- Session Management ---------- #

    def save_session(self, token: str, user_id: str):
        self.set("session/token", token)
        self.set("session/user_id", user_id)
        self.set("session/logged_in", True)

    def load_session(self):
        token = self.get("session/token")
        user_id = self.get("session/user_id")
        logged = self.get("session/logged_in", False)
        return token, user_id, logged

    def clear_session(self):
        self.settings.remove("session")


    # -----------------------------
    # Allowed Domains Management
    # -----------------------------

    def get_allowed_domains(self) -> list:
        """Return the list of allowed domains."""
        domains = self.get("allowed_domains", [])
        if not isinstance(domains, list):
            logging.warning("allowed_domains was not a list, resetting")
            domains = []
            self.set("allowed_domains", domains)
        return domains

    def add_allowed_domain(self, domain: str) -> bool:
        """
        Add a domain to allowed_domains list.
        Returns True if added, False if not (already exists or invalid).
        """
        domain = (domain or "").strip().lower()

        if not domain:
            logging.warning("Attempted to add empty domain to allowed_domains")
            return False

        domains = self.get_allowed_domains()

        if domain in domains:
            logging.info(f"Domain already exists in allowed_domains: {domain}")
            return False

        domains.append(domain)
        self.set("allowed_domains", domains)

        logging.info(f"Added domain to allowed_domains: {domain}")
        return True

    def remove_allowed_domain(self, domain: str) -> bool:
        """
        Remove a domain from allowed_domains.
        Returns True if removed, False if not found.
        """
        domain = (domain or "").strip().lower()

        domains = self.get_allowed_domains()

        if domain not in domains:
            logging.info(f"Attempted to remove non-existing domain: {domain}")
            return False

        domains.remove(domain)
        self.set("allowed_domains", domains)

        logging.info(f"Removed domain from allowed_domains: {domain}")
        return True

    def ensure_default_domains(self, defaults: list = None):
        """
        Ensure that allowed_domains contains defaults if empty or missing.
        If allowed_domains already has entries, nothing is changed.
        """
        if defaults is None:
            defaults = [
                "tapeciarnia.pl",
                "www.tapeciarnia.pl",
                "netplus.pl",
                "www.netplus.pl"
            ]


        domains = self.get("allowed_domains")

        # Missing or empty → apply defaults
        if not domains:
            logging.info("allowed_domains missing or empty, applying default domains")
            self.set("allowed_domains", defaults)
            return True

        logging.debug("allowed_domains already set, no default applied")
        return False

    # -----------------------------
    # Allowed EXTANTIONS
    # -----------------------------

    def ensure_valid_image_extensions(self, defaults: list = None):
        """
        Ensure that valid_image_extensions contains default extensions if empty or missing.
        """
        if defaults is None:
            defaults = [".jpg", ".jpeg", ".png", ".webp"]

        exts = self.get("valid_image_extensions")
        if not exts:
            logging.info("valid_image_extensions missing or empty, applying default values")
            self.set("valid_image_extensions", defaults)
            return True

        logging.debug("valid_image_extensions already set, no default applied")
        return False


    def ensure_valid_video_extensions(self, defaults: list = None):
        """
        Ensure that valid_video_extensions contains default extensions if empty or missing.
        """
        if defaults is None:
            defaults = [".mp4", ".mov", ".webm", ".avi", ".mkv"]

        exts = self.get("valid_video_extensions")
        if not exts:
            logging.info("valid_video_extensions missing or empty, applying default values")
            self.set("valid_video_extensions", defaults)
            return True

        logging.debug("valid_video_extensions already set, no default applied")
        return False
    

    def get_valid_image_extensions(self) -> list[str]:
        """
        Returns the list of valid image extensions. Sets default if missing or empty.
        """
        defaults = [".jpg", ".jpeg", ".png", ".webp"]
        exts = self.get("valid_image_extensions")
        if not exts:
            logging.info("valid_image_extensions missing or empty, applying default values")
            self.set("valid_image_extensions", defaults)
            return defaults
        return exts

    def get_valid_video_extensions(self) -> list[str]:
        """
        Returns the list of valid video extensions. Sets default if missing or empty.
        """
        defaults = [".mp4", ".mov", ".webm", ".avi", ".mkv"]
        exts = self.get("valid_video_extensions")
        if not exts:
            logging.info("valid_video_extensions missing or empty, applying default values")
            self.set("valid_video_extensions", defaults)
            return defaults
        return exts
    
    def get_all_valid_extensions(self) -> list[str]:
        """
        Returns a combined list of all valid image and video extensions.
        """
        image_exts = self.get_valid_image_extensions()
        video_exts = self.get_valid_video_extensions()
        all_exts = image_exts + video_exts
        logging.debug(f"Combined valid extensions: {all_exts}")
        return all_exts


    def __str__(self):
        return f"Config({len(self.data)} keys, path={CONFIG_PATH})"
