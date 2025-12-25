from enum import Enum
from dataclasses import dataclass

class WallpaperType(Enum):
    STATIC = "STATIC"
    ANIMATED = "ANIMATED"

class RangeTypes(Enum):
    ANIMATED = "mp4"
    STATIC = "wallpaper"
    ALL = "all"

class Souces(Enum):
    SUPER = "super"
    FAVOURITE = "favourite"
    COLLECTION = "collection"

@dataclass
class LoginPayload:
    username:str
    password:str
    language:str

    def payload(self):
        return {

                "login": self.username, # aka username
                "haslo": self.password, # aka password
                "lang": self.language
        }