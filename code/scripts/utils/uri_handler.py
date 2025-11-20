import urllib.parse
import logging
import re

logger = logging.getLogger(__name__)

ALLOWED_DOMAIN = "tapeciarnia.pl"

def _is_allowed_domain(url: str) -> bool:
    """Return True only if the URL belongs to tapeciarnia.pl domain."""
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower()

        # Accept both:
        #   tapeciarnia.pl
        #   *.tapeciarnia.pl
        return host == ALLOWED_DOMAIN or host.endswith("." + ALLOWED_DOMAIN)
    except:
        return False


def parse_uri_command(uri_string):
    """
    Parses Tapeciarnia custom URI formats.

    Supports:
    - tapeciarnia://action?param=value
    - tapeciarnia:https://image.jpg
    - tapeciarnia:mp4_url:https://video.mp4
    - tapeciarnia:https://tapeciarnia.pl/program/pobierz_jpeg_v2.php?id=123
    - tapeciarnia:<ID>   → allowed always
    """

    try:
        parsed_uri = urllib.parse.urlparse(uri_string)

        if parsed_uri.scheme != "tapeciarnia":
            logger.warning(f"Invalid scheme: {parsed_uri.scheme}")
            return None, None

        action = None
        params = {}

        # --------------------------------------------------------------
        # CUSTOM FORMAT
        # --------------------------------------------------------------
        if not parsed_uri.netloc and not parsed_uri.query and parsed_uri.path:
            payload = parsed_uri.path.strip()

            # 1) Pure numeric ID → always allowed
            if re.fullmatch(r"\d+", payload):
                action = "id"
                params = {"id": payload}
                return action, params

            # 2) Format: tapeciarnia:action:URL
            if ":" in payload and not payload.lower().startswith("http"):
                parts = payload.split(":", 1)
                action = parts[0].strip()
                url = parts[1].strip()

                # Domain restriction
                if not _is_allowed_domain(url):
                    logger.warning("Blocked: URL not from tapeciarnia.pl domain.")
                    return None, None

                params = {"url": url}
                return action, params

            # 3) Direct URL tapeciarnia:https://...
            if payload.lower().startswith("http"):
                if not _is_allowed_domain(payload):
                    logger.warning("Blocked: URL not from tapeciarnia.pl domain.")
                    return None, None

                # Auto-classify mp4
                if payload.lower().endswith((".mp4", ".webm", ".mov")):
                    action = "mp4_url"
                else:
                    action = "set_url_default"

                params = {"url": payload}
                return action, params

        # --------------------------------------------------------------
        # STANDARD tapeciarnia://action?url=...
        # --------------------------------------------------------------
        action = parsed_uri.path.strip("/")
        if not action and parsed_uri.netloc:
            action = parsed_uri.netloc.split("@")[-1].split(":")[0]

        query_params = urllib.parse.parse_qs(parsed_uri.query)
        params = {k: v[0] for k, v in query_params.items()}

        # If URL parameter exists — check domain
        if "url" in params and not _is_allowed_domain(params["url"]):
            logger.warning("Blocked: URL not from tapeciarnia.pl domain.")
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
