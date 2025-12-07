from PySide6.QtCore import QObject
from PySide6.QtCore import Signal,qIsNull
from PySide6.QtWidgets import QMessageBox

import json
import logging
from models.config import Config
from utils.path_utils import BASE_DIR
from pprint import pprint
class LanguageController(QObject):
    # emit a signal when language is changed
    language_changed = Signal()

    def __init__(self,config:Config):
        super().__init__()
        self.TRANSLATIONS_FILE = BASE_DIR / "translations" / "languages.json"
        self.DEFAULT_FLIE = BASE_DIR / "translations" / "en.json"
        if not self.TRANSLATIONS_FILE.exists():
            logging.warning("Translations file does not exist at initialization.")
        self.config = config
        self.lang = None
        self.default_lang = self.load_default_language()

    def load_default_language(self):
        """Load the default language (English)"""
        if self.DEFAULT_FLIE.exists():
            with self.DEFAULT_FLIE.open("r", encoding="utf-8") as f:
                try:
                    dlang = json.load(f)
                    logging.info("Default language (EN) loaded successfully.")
                    return dlang.get("en", {})
                except json.JSONDecodeError:
                    logging.error("Failed to load default language: Invalid JSON.")
        else:
            logging.error("Default language file not found.")

    # check for translations file
    def check_translations_file(self) -> bool:
        """Check if translations file exists"""
        return self.TRANSLATIONS_FILE.exists()


    def get_available_languages(self):
        """Retrieve available languages from translations directory"""
        # check if translations file exists
        if self.TRANSLATIONS_FILE.exists():
            with self.TRANSLATIONS_FILE.open("r", encoding="utf-8") as f:
                try:
                    languages = json.load(f)
                    return languages.keys().__iter__()
                except json.JSONDecodeError:
                    return {}
        else:
            logging.warning("Translations file not found.")
            return {"en": "English"}
    
    # get a language by key
    def get_language_by_name(self, lang_code: str):
        """Get the display name of a language given its code"""
        if self.TRANSLATIONS_FILE.exists():
            with self.TRANSLATIONS_FILE.open("r", encoding="utf-8") as f:
                try:
                    languages = json.load(f)
                    return languages.get(lang_code, "en")
                except json.JSONDecodeError:
                    return "Unknown"
        else:
            logging.warning("Translations file not found.")
            return "Unknown"
    
    def enumerate_languages(self,combo_box):
        """Enumerate available languages to the combo box"""
        combo_box.clear()
        available_langs = list(self.get_available_languages())
        available_langs.sort()
        combo_box.addItems(map(str.upper, available_langs))

    def on_language_changed(self, lang_name: str):
        """Handle language change request"""
        logging.info(f"Language change requested: {lang_name}")
        self.lang = self.get_language_by_name(lang_name.lower())
        self.config.set_language(lang_name.lower())        
        self.language_changed.emit()
    
    def get(self,key_path: str, default: str = None, **format_args):
        """
        Safely fetch a translation string from nested dicts.

        Example:
            get_text(lang_data, "en", "dialog.info.reset_success_message")
            get_text(lang_data, "en", "status.genaral.range", range_type="wallpaper")

        Args:
            data: main language JSON/dict
            lang: "en", "pl", etc.
            key_path: dot notation string path
            default: fallback value if missing
            **format_args: optional formatting values

        Returns:
            The translated and formatted string, or default.
        """

        try:
            # Validate language block exists
            node = self.lang
            if not isinstance(node, dict):
                logging.warning(f"{key_path} not found.")
                return default

            # Resolve nested keys
            for key in key_path.split("."):
                node = node[key]   # may throw KeyError/TypeError

            # If formatting required
            if format_args:
                try:
                    node = node.format(**format_args) if "{" in node else node
                except Exception:
                    logging.warning(f"Failed to format key '{key_path}'")
                    pass

            return node

        except Exception as e:
            # Resolve nested keys
            node = self.default_lang
            logging.warning(f"Missing translation: {e}.Using default language.")
            for key in key_path.split("."):
                node = node[key]   # may throw KeyError/TypeError
            return node
            # return self.default_land.get(key_path, default) if self.default_land else default
    
        
    # initial language setup
    def setup_initial_language(self, combo_box):
        """Set up the initial language based on config"""
        lang_code = self.config.get_language()
        logging.info(f"Setting up initial language: {lang_code}")
        index = combo_box.findText(lang_code.upper())
        if index != -1:
            combo_box.setCurrentIndex(index)
            self.lang = self.get_language_by_name(lang_code)
            logging.info(f"Initial language set to: {lang_code}")
            self.language_changed.emit()
        else:
            logging.warning(f"Language code '{lang_code}' not found in combo box.")
            logging.warning("Defaulting to EN language")
            self.lang = self.get_language_by_name("en")
            self.config.set_language("en")
            QMessageBox.warning(
                None,
                "Unsupported langauge",
                f"Language code '{lang_code}' not supported by the app.\n\nDefauting to EN language",
                QMessageBox.StandardButton.Ok
            )
        
    
    def get_current_language(self) -> str:
        return self.config.get_language()

    # get current language code
    def get_current_language_code(self) -> str:
        return self.config.get_language()
    