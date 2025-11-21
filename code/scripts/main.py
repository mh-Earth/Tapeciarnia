import sys
import os
import logging

from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import Signal, QLockFile, QDir,Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QIcon

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.Floor
)

# ============================================================
#  DYNAMIC IMPORTS (WORKS BOTH INSTALLED + DEV MODE)
# ============================================================

try:
    # Absolute imports (packaged layout)
    from code.scripts.utils.path_utils import get_style_path
    from code.scripts.setLogging import InitLogging
    from code.scripts.utils.pathResolver import *
    from code.scripts.ui.main_window import TapeciarniaApp
    from code.scripts.utils.uri_handler import parse_uri_command
    from code.scripts.ui import icons_resource_rc
    from code.scripts.utils.singletons import SingleApplication,get_config
    logging.debug("Loaded modules using absolute imports (code.*)")

except ImportError:
    # Dev environment imports
    from utils.path_utils import get_style_path
    from setLogging import InitLogging
    from utils.pathResolver import *
    from ui.main_window import TapeciarniaApp
    from utils.uri_handler import parse_uri_command
    from utils.singletons import SingleApplication,get_config
    from ui import icons_resource_rc
    logging.debug("Loaded modules using relative imports")

try:
    from devauth import auth_of_devloper
except Exception as e:
    def auth_of_devloper() -> bool:
        return True



# config = Config()
# token, user_id, logged = config.load_session()

# if logged and token:
#     # try to validate the token
#     if api_validate_token(token):
#         open_main_window()
#     else:
#         config.clear_session()
#         open_login()
# else:
#     open_login()



# ============================================================
#  STYLESHEET
# ============================================================

def load_stylesheet(app, path):
    try:
        with open(path, "r") as f:
            app.setStyleSheet(f.read())
        logging.info("Stylesheet applied.")
    except Exception as e:
        logging.error(f"Stylesheet load failed: {e}")

# ============================================================
#  MAIN APPLICATION ENTRY
# ============================================================

def main():
    # Init logging before anything else
    InitLogging()
    logging.info("Starting Tapeciarnia...")

    try:
        app = SingleApplication(sys.argv)
        app.setWindowIcon(QIcon(':/icons/icons/icon.ico'))

        # if not auth_of_devloper():
        #     raise ZeroDivisionError("The app has faced some critical error. Please contact the developer.")
        # Single instance wrapper

        # If this is a secondary instance → exit now
        if not app.is_primary_instance:
            sys.exit(0)

        # ------- PRIMARY INSTANCE BEGINS --------

        load_stylesheet(app, get_style_path())
        window = TapeciarniaApp()

        # Handle incoming URIs / messages
        def dispatch_message(message):
            uri = next(
                (arg for arg in message.split() if arg.startswith("tapeciarnia:")),
                None
            )

            # Bring window to foreground
            window.showNormal()
            window.raise_()
            window.activateWindow()

            if uri:
                logging.info(f"Handling URI: {uri}")
                action, params = parse_uri_command(uri)
                if action:
                    window.handle_startup_uri(action, params)
                else:
                    logging.warning("Invalid URI received.")
            else:
                logging.info("No URI supplied by secondary instance.")

        app.message_received.connect(dispatch_message)

        # Initial launch with arguments
        if len(sys.argv) > 1:
            dispatch_message(" ".join(sys.argv[1:]))
        else:
            window.showNormal()

        logging.info("Entering Qt event loop...")
        sys.exit(app.exec())

    except Exception as e:
        QMessageBox.critical(
            None,
            "Unexpected Error",
            str(e),
            QMessageBox.StandardButton.Ok
        )

        logging.critical("Fatal startup error", exc_info=True)
        raise

if __name__ == "__main__":
    main()
        

