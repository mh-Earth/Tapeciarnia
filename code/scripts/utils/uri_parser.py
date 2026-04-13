# ===============================================================
# Description: This module provides a utility function to parse custom Tapeciarnia URI commands. It supports various URI formats, including those with actions and parameters, direct URLs, and numeric IDs. The parser validates the scheme, extracts the action and parameters, and checks if any URLs belong to allowed domains. The function returns a tuple of the action and a dictionary of parameters, or (None, None) if the URI is invalid or blocked. The module also includes logging for debugging and error tracking purposes.
# ===============================================================

import urllib.parse
import logging
import re
from utils.singletons import get_config
from models.constants import URIActions
logger = logging.getLogger(__name__)



def _is_allowed_domain(url: str) -> bool:
    """Return True only if the URL belongs to any allowed domain or its subdomains."""
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower().strip()

        # If empty host → invalid URL
        if not host:
            return False

        for domain in get_config().get_allowed_domains():
            domain = domain.lower()
            # Exact match
            if host == domain:
                return True
            # Subdomain allowed
            if host.endswith("." + domain):
                return True

        return False

    except Exception:
        return False


def parse_uri_command(uri_string):
    """
    Parses Tapeciarnia custom URI formats.

    Supports:
    - tapeciarnia://action?param=value
    - tapeciarnia:https://image.jpg
    - tapeciarnia:mp4_url:https://video.mp4
    - tapeciarnia:https://tapeciarnia.pl/program/pobierz_jpeg_v2.php?id=123
    - tapeciarnia:<ID>
    - tapeciarnia://<ID>
    - tapeciarnia://id-mp4/<ID>
    """

    try:
        parsed_uri = urllib.parse.urlparse(uri_string)

        if parsed_uri.scheme != "tapeciarnia":
            logger.warning(f"Invalid scheme: {parsed_uri.scheme}")
            return None, None

        action = None
        params = {}

        netloc = parsed_uri.netloc.strip()
        path = parsed_uri.path.strip("/")

        # --------------------------------------------------------------
        # 1) tapeciarnia://<ID>
        # --------------------------------------------------------------
        if netloc.isdigit():
            action = URIActions.ID.value
            params = {"id": netloc}
            return action, params

        # --------------------------------------------------------------
        # 2) tapeciarnia://id-mp4/<ID>
        # --------------------------------------------------------------
        if netloc == "id-mp4" and path.isdigit():
            action = URIActions.MP4_ID.value
            params = {"id": path}
            return action, params

        # --------------------------------------------------------------
        # CUSTOM FORMAT (tapeciarnia:<payload>)
        # --------------------------------------------------------------
        if not netloc and not parsed_uri.query and parsed_uri.path:
            payload = parsed_uri.path.strip()

            # Pure numeric ID
            if payload.isdigit():
                action = URIActions.ID.value
                params = {"id": payload}
                return action, params

            # action:URL
            if ":" in payload and not payload.lower().startswith("http"):
                action, url = payload.split(":", 1)
                action = action.strip()
                url = url.strip()

                if not _is_allowed_domain(url):
                    logger.warning("Blocked: URL not from allowed domain.")
                    return None, None

                params = {"url": url}
                return action, params

            # Direct URL
            if payload.lower().startswith("http"):
                if not _is_allowed_domain(payload):
                    logger.warning("Blocked: URL not from allowed domain.")
                    return None, None

                action = (
                    "mp4_url"
                    if payload.lower().endswith((".mp4", ".webm", ".mov"))
                    else "set_url_default"
                )

                params = {"url": payload}
                return action, params

        # --------------------------------------------------------------
        # STANDARD tapeciarnia://action?params
        # --------------------------------------------------------------
        action = path or netloc

        query_params = urllib.parse.parse_qs(parsed_uri.query)
        params = {k: v[0] for k, v in query_params.items()}

        if "url" in params and not _is_allowed_domain(params["url"]):
            logger.warning("Blocked: URL not from allowed domain.")
            return None, None

        return action, params

    except Exception as e:
        logger.error(f"URI parsing error: {e}")
        return None, None


# Standalone testing
if __name__ == "__main__":
    tests = [
        "tapeciarnia:12345",
        "tapeciarnia:https://tapeciarnia.pl/img.jpg",
        "tapeciarnia:mp4_url:https://tapeciarnia.pl/v.mp4",
        "tapeciarnia://setwallpaper?url=https://www.tapeciarnia.pl/image.jpg",
    ]

    for t in tests:
        print(t, "→", parse_uri_command(t))
