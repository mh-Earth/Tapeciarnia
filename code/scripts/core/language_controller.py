from PySide6.QtCore import QObject
from PySide6.QtCore import Signal,qIsNull
from PySide6.QtWidgets import QMessageBox

import json
import logging
from models.config import Config
from utils.path_utils import BASE_DIR
from utils.singletons import get_config

class LanguageController(QObject):
    # emit a signal when language is changed
    language_changed = Signal(dict)

    def __init__(self):
        super().__init__()
        self.TRANSLATIONS_FILE = BASE_DIR / "translations" / "languages.json"
        if not self.TRANSLATIONS_FILE.exists():
            logging.warning("Translations file does not exist at initialization.")
        self.config = get_config()

    # check for translations file
    def check_translations_file(self) -> bool:
        """Check if translations file exists"""
        return self.TRANSLATIONS_FILE.exists()


    def get_available_languages(self):
        """Retrieve available languages from translations directory"""
        translations_file = BASE_DIR / "translations" / "languages.json"
        # check if translations file exists
        if translations_file.exists():
            with translations_file.open("r", encoding="utf-8") as f:
                try:
                    languages = json.load(f)
                    return languages.keys().__iter__()
                except json.JSONDecodeError:
                    return {}
        else:
            print("Translations file not found.")
            return {"en": "English"}
    
    # get a language by key
    def get_language_by_name(self, lang_code: str):
        """Get the display name of a language given its code"""
        translations_file = BASE_DIR / "translations" / "languages.json"
        if translations_file.exists():
            with translations_file.open("r", encoding="utf-8") as f:
                try:
                    languages = json.load(f)
                    return languages.get(lang_code, "en")
                except json.JSONDecodeError:
                    return "Unknown"
        else:
            print("Translations file not found.")
            return "Unknown"
    
    def enumerate_languages(self,combo_box):
        """Enumerate available languages to the combo box"""
        combo_box.clear()
        combo_box.addItems(map(str.upper, list(self.get_available_languages())))

    def on_language_changed(self, lang_name: str):
        """Handle language change request"""
        logging.info(f"Language change requested: {lang_name}")
        lang = self.get_language_by_name(lang_name.lower())
        self.config.set_language(lang_name.lower())        
        self.language_changed.emit(lang)
    
    # initial language setup
    def setup_initial_language(self, combo_box):
        """Set up the initial language based on config"""
        lang_code = self.config.get_language()
        logging.info(f"Setting up initial language: {lang_code}")
        index = combo_box.findText(lang_code.upper())
        if index != -1:
            combo_box.setCurrentIndex(index)
            lang = self.get_language_by_name(lang_code)
            logging.info(f"Initial language set to: {lang_code}")
            self.language_changed.emit(lang)
        else:
            logging.warning(f"Language code '{lang_code}' not found in combo box.")
            logging.warning("Defaulting to EN language")
            lang = self.get_language_by_name("en")
            self.config.set_language("en")
            QMessageBox.warning(
                None,
                "Unsupported langauge",
                f"Language code '{lang_code}' not supported by the app.\n\nDefauting to EN language",
                QMessageBox.StandardButton.Ok
            )
        
        return lang
    
    def get_current_language(self) -> str:
        return self.config.get_language()

    


    # def retranslateUi(self, MainWindow):
    #     self.main_window.statusLabel.setText(QCoreApplication.translate("MainWindow", u"Status: min ,Status: min ,Status: min ,Status: min", None))
    # retranslateUi


if __name__ == "__main__":
    lc = LanguageController()
    langs = lc.get_available_languages()
    for code, name in langs.items():
        print(f"{code}: {name}")