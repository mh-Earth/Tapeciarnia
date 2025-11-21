import re
import logging
from pathlib import Path
from typing import Optional
import os
import urllib
import re
from urllib.parse import urlparse, parse_qs
import requests
from utils.singletons import get_config



def is_image_url_or_path(s: str) -> bool:
    """Check if string is an image URL or path - IMPROVED"""
    s = s.lower()
    
    # Check for image file extensions
    image_extensions = ('.jpg', '.jpeg', '.png',  '.gif', '.webp')
    
    # Check local file path
    if any(s.endswith(ext) for ext in image_extensions):
        return True
    
    # Check HTTP URL with image extension
    if s.startswith("http"):
        # More flexible pattern to handle query parameters and URL fragments
        pattern = r"\.(jpe?g|png|gif|webp)(\?.*)?$"
        return bool(re.search(pattern, s))
    
    return False

def is_video_url_or_path(s: str) -> bool:
    """Check if string is a video URL or path - IMPROVED"""
    s = s.lower()
    
    # Check for video file extensions
    video_extensions = ('.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.wmv')
    
    # Check local file path
    if any(s.endswith(ext) for ext in video_extensions):
        return True
    
    # Check HTTP URL with video extension
    if s.startswith("http"):
        # More flexible pattern to handle query parameters and URL fragments
        pattern = r"\.(mp4|mkv|webm|avi|mov|flv|wmv)(\?.*)?$"
        if bool(re.search(pattern, s)):
            return True
        
        # Also check for video hosting platforms
        config = get_config()
        video_hosts = config.get_allowed_domains()

        return any(host in s for host in video_hosts)
    
    return False

def validate_url_or_path(s: str) -> Optional[str]:
    """
    Validate and normalize URL, local file path, or custom scheme (tapeciarnia).
    Returns a cleaned string or None if invalid.
    """
    if not s:
        return None

    s = s.strip().strip('"').strip("'")
    if not s:
        return None

    # --- Local Path Handling ---
    try:
        path = Path(os.path.expandvars(os.path.expanduser(s)))
        if path.exists():
            return str(path.resolve())
    except Exception:
        pass  # Continue to URL validation

    # --- URL Validation ---
    lower = s.lower()

    if lower.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(s)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return s  # Valid URL

    # As uri will not set as url text so we don't need this check
    # # --- Custom Scheme: tapeciarnia: ---
    # if lower.startswith("tapeciarnia:"):
    #     # Extract anything after "tapeciarnia:" including optional brackets
    #     m = re.match(r"tapeciarnia:\[?(.*?)\]?$", s, re.IGNORECASE)
    #     if m:
    #         inner = m.group(1).strip()
    #         return inner if inner else None

    return None


# def validate_tapeciarnia_url(s: str) -> Optional[str]:
#     """
#     Accepts ONLY URLs from tapeciarnia.pl or ANY of its subdomains.
#     Example: cdn.tapeciarnia.pl, img.tapeciarnia.pl, etc.
#     """
#     if not s:
#         return None

#     s = s.strip()
#     parsed = urllib.parse.urlparse(s)

#     if parsed.scheme not in ("http", "https"):
#         return None

#     domain = parsed.netloc.lower()

#     # Allow exactly tapeciarnia.pl OR subdomain.tapeciarnia.pl
#     if domain == "tapeciarnia.pl" or domain.endswith(".tapeciarnia.pl"):
#         return s

#     return None


def validate_tapeciarnia_url(s: str) -> Optional[str]:
    """
    Accepts ONLY URLs from tapeciarnia.pl or www.tapeciarnia.pl.
    Returns normalized URL or None.
    """
    if not s:
        return None

    s = s.strip()

    parsed = urllib.parse.urlparse(s)
    if parsed.scheme not in ("http", "https"):
        return None

    domain = parsed.netloc.lower()
    config = get_config()

    allowed_domains = config.get_allowed_domains()

    if domain in allowed_domains:
        return s

    return None


def validate_cli_arg(arg: str) -> Optional[str]:
    """Validate CLI argument - IMPROVED"""
    parsed = validate_url_or_path(arg)
    if parsed:
        return parsed
    
    if arg.lower().startswith("tapeciarnia:"):
        m = re.match(r"tapeciarnia:\[?(.*)\]?$", arg, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    
    return None



def is_tapeciarnia_redirect_url(url: str):
    """
    Identify if the URL matches:
    https://tapeciarnia.pl/program/pobierz_jpeg_v2.php?id=<ID>
    
    Returns:
        dict { "id": <id_int>, "url": <original_url> }
        or None if not matched.
    """
    try:
        parsed = urlparse(url)
        config = get_config()
        # Must be tapeciarnia.pl
        if parsed.netloc.lower() not in config.get_allowed_domains():
            return None

        # Must match the redirect script
        if not parsed.path.endswith("/program/pobierz_jpeg_v2.php"):
            return None

        # Extract ?id=xxx
        query = parse_qs(parsed.query)
        if "id" not in query:
            return None

        id_value = query["id"][0].strip()

        # Only digits allowed
        if not id_value.isdigit():
            return None

        return {
            "id": int(id_value),
            "url": url
        }

    except Exception:
        return None




def get_media_type(s: str) -> str:
    """Determine media type (image, video, or unknown)"""
    if is_image_url_or_path(s):
        return "image"
    elif is_video_url_or_path(s):
        return "video"

if __name__ == "__main__":

    print(validate_tapeciarnia_url("https://www.youtube.com/watch?v=sr_qh33LsKQ&list=RDsr_qh33LsKQ&start_radio=1"))