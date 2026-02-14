from PySide6.QtCore import QSettings

from utils.system_utils import current_system_locale,get_primary_screen_dimensions
import logging
from models.constants import RangeTypes

class Config:
    def __init__(self):
        logging.debug("Initializing QSettings config backend")

        # Organization + Application name (used as storage path)
        self.settings = QSettings("Tapeciarnia", "TapeciarniaApp")
        self.ensure_default_domains()
        self.ensure_valid_image_extensions()
        self.ensure_valid_video_extensions()
        self.set_default_super_wallpaper_urls()
        self.set_login_url("https://tapeciarnia.pl/program/login_2025.php")
        self.set_uri_urls("https://tapeciarnia.pl/app_uri.php?id={wallpaper_id}&typ=windows","https://tapeciarnia.pl/app_uri.php?id=mp4-{wallpaper_id}&typ=windows")
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
        range_type:str = self.get("scheduler_range_type",RangeTypes.ALL)
        return enabled, source, interval, range_type

    def set_scheduler_settings(self,enabled:bool, source:str, interval:int, range_type:str):
        self.set("scheduler_source", source)
        self.set("scheduler_interval", interval)
        self.set("scheduler_range_type", range_type)
        self.set("scheduler_enabled", enabled)

    def get_scheduler_enabled(self) -> bool:
        return self.to_bool(self.get("scheduler_enabled",False))
        
    def set_scheduler_enabled(self,scheduler_enabled:bool):
        self.set("scheduler_enabled",scheduler_enabled)

    def get_language(self) -> str:
        lang = self.get("language",current_system_locale())
        return lang

    def set_language(self, lang: str):
        self.set("language", lang)

    def get_range_preference(self) -> str:
        return self.get("range_preference", RangeTypes.ALL)

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
    
    def set_login_url(self,url):
        self.set("loging_url",url)
    
    def get_loging_url(self) -> str:
        return self.get("login_url","https://tapeciarnia.pl/program/login_2025.php")
    
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

    # -------------------------------
    #  Installation managment
    # -------------------------------
    def set_is_first_run_after_installation(self,value:bool) -> None:
        self.set("first_run_after_installation",value)

    def get_is_first_run_after_installation(self) -> bool:
        self.set("first_run_after_installation",False)

    def __str__(self):
        return f"Config({len(self.data)} keys)"

    # -------------------------------
    # URl Managment
    # -------------------------------

    def set_super_wallpaper_url(self,url:str,rangeType:RangeTypes) -> None:
        if rangeType == RangeTypes.ALL:
            self.set("super_wallpaper_url_all",url)
        
        elif rangeType == RangeTypes.STATIC:
            self.set("super_wallpaper_url_wallpaper",url)
        
        elif rangeType == RangeTypes.ANIMATED:
            self.set("super_wallpaper_url_mp4",url)

    def get_super_wallpaper_url(self,rangeType:RangeTypes) -> str:
        if rangeType == RangeTypes.ALL:
            return self.get("super_wallpaper_url_all","")
        
        elif rangeType == RangeTypes.STATIC:
            return self.get("super_wallpaper_url_wallpaper","")
        
        elif rangeType == RangeTypes.ANIMATED:
            return self.get("super_wallpaper_url_mp4","")
        
        return ""
    
    def set_default_super_wallpaper_urls(self) -> None:
        urls = {
            RangeTypes.ANIMATED: "https://tapeciarnia.pl/program/wybierz_tapete_2025.php?pokaz=all_mp4&x={x}&y={y}&lang={lang}",
            RangeTypes.STATIC: "https://tapeciarnia.pl/program/wybierz_tapete_2025.php?pokaz=all_img&x={x}&y={y}&lang={lang}",
            RangeTypes.ALL: "https://tapeciarnia.pl/program/wybierz_tapete_2025.php?pokaz=all&x={x}&y={y}&lang={lang}"
        }

        x,y = get_primary_screen_dimensions()
        lang = self.get_language() if self.get_language() else current_system_locale()
        
        logging.debug(f"Setting default super wallpaper URLs with x={x}, y={y}, lang={lang}")

        for _type,url_template in urls.items():
            url = url_template.format(x=x, y=y, lang=lang)
            self.set_super_wallpaper_url(url,_type)
            logging.debug(f"Set default super wallpaper URL for type '{type}': {url}")

        logging.debug("Default super wallpaper URLs set successfully")

    def set_fvrt_wallpaper_url(self,user_name:str) -> None:
        if user_name:
            x,y =get_primary_screen_dimensions()
            url = f"https://www.tapeciarnia.pl/program/wybierz_tapete_2025.php?user={user_name}&pokaz=ulubione_tap&x={x}&y={y}&hd=1"
            self.set("fvrt_wallpaper_url",url)

        else:
            raise ValueError("User name must be provided to set favorite wallpaper URL.")
    
    def get_frvt_wallpaper_url(self) -> str:
        return self.get("fvrt_wallpaper_url","")

    # def set_default_fvrt_wallpaper_url(self) -> None:

    #     url = "https://www.tapeciarnia.pl/program/wybierz_tapete_2025.php?user={user_name}&pokaz=ulubione_tap&x={x}&y={y}&hd=1"

    #     x,y = get_primary_screen_dimensions()

    #     url = url.format(x=x, y=y,user_name=None)

    #     self.set("fvrt_wallpaper_url",url)

    #     logging.debug(f"Set default frvt wallpaper URL: {url}")

    def set_uri_image_url(self,url:str):
        self.set("url_image_url",url)

    def get_uri_image_url(self) -> str:
        return self.get("url_image_url","")

    def set_uri_video_url(self,url:str):
        self.set("url_video_url",url)

    def get_uri_video_url(self) -> str:
        return self.get("url_video_url","")
        
    def set_uri_urls(self,image_url:str,video_url:str):
        self.set_uri_image_url(image_url)
        self.set_uri_video_url(video_url)
