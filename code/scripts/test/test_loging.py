import requests
from jsonschema import validate, ValidationError


LOGING_SUCCESSFULL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "is_ok": {"type": "boolean"},
        "login": {"type": "string", "minLength": 1},
        "key": {
            "type": "string",
            # This regex ensures it is exactly 32 hex characters (standard for MD5)
            "pattern": "^[a-f0-9]{32}$" 
        }
    },
    "required": ["is_ok", "login", "key"],
    "additionalProperties": False
}

LOGIN_FALID_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "is_ok": {"type": "boolean"},
        "info": {"type": "string", "minLength": 1}
    },
    "required": ["is_ok", "info"],
    "additionalProperties": False
}


def login(username:str,password:str):
    url = f"https://tapeciarnia.pl/program/login_2025.php?login={username}&haslo={password}&lang=pl"

    response = requests.get(
            url, 
        )
    
    if response.status_code == 200:
        return response.json()

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



def test_loging_success():
    password = "test222"
    username = "gmail"
    data = login(username,password)
    assert validate_response(LOGING_SUCCESSFULL_SCHEMA,data) == True

def test_loging_faild():
    password = "test222xxxx"
    username = "gmail"
    data = login(username,password)
    assert validate_response(LOGIN_FALID_SCHEMA,data) == True
    


