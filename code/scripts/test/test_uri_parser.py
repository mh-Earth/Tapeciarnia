import pytest

from utils.uri_parser import parse_uri_command
from utils.validators import extract_file_id_from_url

# ------------------------------------------------------------
# Mock config for allowed domains
# ------------------------------------------------------------
class MockConfig:
    def get_allowed_domains(self):
        return ["tapeciarnia.pl"]


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    from utils import uri_parser
    monkeypatch.setattr(uri_parser, "get_config", lambda: MockConfig())


# ------------------------------------------------------------
# ID handling
# ------------------------------------------------------------
@pytest.mark.parametrize(
    "uri, expected",
    [
        ("tapeciarnia:12345", ("id", {"id": "12345"})),
        ("tapeciarnia://12345", ("id", {"id": "12345"})),
    ],
)
def test_numeric_id(uri, expected):
    assert parse_uri_command(uri) == expected


def test_mp4_id():
    uri = "tapeciarnia://id-mp4/19367"
    assert parse_uri_command(uri) == ("mp4_id", {"id": "19367"})


# ------------------------------------------------------------
# URL handling (allowed domains)
# ------------------------------------------------------------
@pytest.mark.parametrize(
    "uri, action",
    [
        ("tapeciarnia:https://tapeciarnia.pl/img.jpg", "set_url_default"),
        ("tapeciarnia:https://tapeciarnia.pl/video.mp4", "mp4_url"),
        ("tapeciarnia:mp4_url:https://tapeciarnia.pl/video.mp4", "mp4_url"),
        (
            "tapeciarnia://setwallpaper?url=https://www.tapeciarnia.pl/image.jpg",
            "setwallpaper",
        ),
    ],
)
def test_allowed_urls(uri, action):
    action_out, params = parse_uri_command(uri)
    assert action_out == action
    assert "url" in params


# ------------------------------------------------------------
# Blocked domains
# ------------------------------------------------------------
@pytest.mark.parametrize(
    "uri",
    [
        "tapeciarnia:https://google.com/image.jpg",
        "tapeciarnia:mp4_url:https://evil.com/video.mp4",
        "tapeciarnia://setwallpaper?url=https://facebook.com/x.jpg",
    ],
)
def test_blocked_domains(uri):
    assert parse_uri_command(uri) == (None, None)


# ------------------------------------------------------------
# Invalid schemes
# ------------------------------------------------------------
def test_invalid_scheme():
    assert parse_uri_command("http://tapeciarnia.pl/img.jpg") == (None, None)


# ------------------------------------------------------------
# Query parameters
# ------------------------------------------------------------
def test_query_params():
    uri = "tapeciarnia://setwallpaper?url=https://tapeciarnia.pl/a.jpg&mode=fill"
    action, params = parse_uri_command(uri)

    assert action == "setwallpaper"
    assert params["url"] == "https://tapeciarnia.pl/a.jpg"
    assert params["mode"] == "fill"


# ------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------
@pytest.mark.parametrize(
    "uri",
    [
        "tapeciarnia://",
        "tapeciarnia:",
        "tapeciarnia:///",
        "tapeciarnia:   ",
        "tapeciarnia://id-mp4/",
    ],
)
def test_invalid_inputs(uri):
    assert parse_uri_command(uri) == (None, None)


# extract_file_id_from_url tests
@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "https://tapeciarnia.pl/app_uri.php?id=5600&typ=windows",
            ("id", "5600"),
        ),
        (
            "https://tapeciarnia.pl/app_uri.php?id=mp4-2500&typ=windows",
            ("mp4_id", "2500"),
        ),
        (
            "https://tapeciarnia.pl/app_uri.php?id=invalid123&typ=windows",
            (None, None),
        ),
        (
            "https://otherdomain.com/program/pobierz_jpeg_v2.php?id=5600",
            (None, None),
        ),
        (
            "https://tapeciarnia.pl/otherpath.php?id=5600",
            (None, None),
        ),
    ],
)
def test_extract_file_id_from_url(url, expected):
    assert extract_file_id_from_url(url) == expected
