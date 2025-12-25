import requests
from jsonschema import validate, ValidationError


BASE_URL = "https://tapeciarnia.pl/program/wybierz_tapete_2025.php"
SCHEDULER_DATA_SCHEMA = {
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

FRVT_DATA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "is_ok": {"type": "boolean"},
        "info": {"type": "string"},
        "wall": {
            "type": "object",
            "patternProperties": {
                # Validates any key that consists of one or more digits
                "^[0-9]+$": {
                    "type": "object",
                    "properties": {
                        "l": {"type": "integer"},
                        "url": {"type": "string", "format": "uri"},
                        "www": {"type": "string", "format": "uri"},
                        "type": {"type": "string", "enum": ["img", "mp4"]}
                    },
                    "required": ["l", "url", "www", "type"],
                    "additionalProperties": False
                }
            }
        }
    },
    "required": ["is_ok", "info", "wall"],
    "additionalProperties": False
}


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

def get_all_data():
    pokaz_value = "all"
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

def get_frvt_data():


    url = f"https://www.tapeciarnia.pl/program/wybierz_tapete_2025.php?user=gmail&pokaz=ulubione_tap&x=1080&y=1290&hd=1"
    response = requests.get(
            url, 
            timeout=10 # Set a reasonable timeout
        )
    if response.status_code == 200:
        return response.json()


def validate_response(schema,data):
    try:
        validate(instance=data, schema=schema)
        return True
    except ValidationError as e:
        return False



def test_animated_data():
    data = get_animated_data()
    assert validate_response(SCHEDULER_DATA_SCHEMA,data) == True

def test_static_data():
    data = get_static_data()
    assert validate_response(SCHEDULER_DATA_SCHEMA,data) == True

def test_all_data():
    data = get_all_data()
    assert validate_response(SCHEDULER_DATA_SCHEMA,data) == True

def test_fvrt_data():
    data = get_frvt_data()
    assert validate_response(FRVT_DATA_SCHEMA,data) == True
    


