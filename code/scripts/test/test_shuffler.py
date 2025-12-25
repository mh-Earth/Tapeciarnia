import requests
from pprint import pprint
from jsonschema import validate, ValidationError

# test the url for valid data
BASE_URL = "https://tapeciarnia.pl/program/wybierz_tapete_2025.php"
SHUFFLE_DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "is_ok": {"type": "boolean"},
        "wall": {
            "type": "object",
            "patternProperties": {
                # This ensures keys are strings of numbers (e.g., "1", "10")
                "^[0-9]+$": {
                    "type": "object",
                    "properties": {
                        "l": {"type": "integer"},
                        "type": {"type": "string"},
                        "url": {"type": "string", "format": "uri"},
                        "www": {"type": "string", "format": "uri"}
                    },
                    "required": ["l", "type", "url", "www"]
                }
            },
            "additionalProperties": False # No other keys allowed in 'wall'
        }
    },
    "required": ["is_ok", "wall"]
}


def validate_response(schema,data):
    try:
        validate(instance=data, schema=schema)
        print("✅ Data validation successful!")
        return True
    except ValidationError as e:
        print(f"❌ Data validation failed!")
        print(f"Error Path: {' -> '.join(map(str, e.path))}")
        print(f"Message: {e.message}")
        return False


def get_animated_data():
    pokaz_value = "all_mp4"
    url = f"{BASE_URL}?pokaz={pokaz_value}&x=1920&y=1080"
    post_data = {
        'x': 1920,
        'y': 1080,
        'pokaz': pokaz_value,
        'lang': "en"
    }

    response = requests.post(
            url, 
            data=post_data,
            timeout=10 # Set a reasonable timeout
        )
    if response.status_code == 200:
        return response.json()
    else:
        return {}

def get_static_data():
    pokaz_value = "all_img"
    url = f"{BASE_URL}?pokaz={pokaz_value}&x=1920&y=1080"
    post_data = {
        'x': 1920,
        'y': 1080,
        'pokaz': pokaz_value,
        'lang': "en"
    }

    response = requests.post(
            url, 
            data=post_data,
            timeout=10 # Set a reasonable timeout
        )
    if response.status_code == 200:
        return response.json()


def test_animated_data():
    data = get_animated_data()
    assert validate_response(SHUFFLE_DATA_SCHEMA,data) == True

def test_static_data():
    data = get_static_data()
    assert validate_response(SHUFFLE_DATA_SCHEMA,data) == True

# test_animated_data()