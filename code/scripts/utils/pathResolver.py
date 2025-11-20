import requests
import logging

def resolve_tapeciarnia_redirect(url: str) -> str | None:
    """
    Follow Tapeciarnia redirect and return the final image URL.
    """
    try:
        logging.warning(f"Following redirected path : {url}")
        response = requests.get(url, allow_redirects=True, timeout=10)

        if response.history:  # redirect happened
            final_url = response.url
            logging.info(f"Redirect resolved: {url} → {final_url}")
            return final_url

        # No redirect, just return original
        logging.warning(f"Final path : {url}")

        return url

    except Exception as e:
        logging.error(f"Failed to resolve redirect for {url} : {e}")
        return None



def fast_resolve_tapeciarnia_redirect(url: str) -> str | None:
    """
    Quickly resolve Tapeciarnia redirect URL using HEAD request.
    Returns final image URL or None.
    """

    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=5
        )

        # The last response URL is the final image location
        final_url = response.url

        # Safety check: ensure the final URL is an image
        if final_url.lower().endswith((".jpg", ".jpeg", ".png", ".webp" ".mp4")):
            return final_url

        return None

    except Exception as e:
        print(f"Redirect resolution failed: {e}")
        return None


if __name__ == "__main__":

    final_image_url = fast_resolve_tapeciarnia_redirect(
        "https://tapeciarnia.pl/program/pobierz_jpeg_v2.php?id=386422"
    )

    print(final_image_url)
