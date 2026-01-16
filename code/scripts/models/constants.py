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

class URIActions(Enum):
    ID = "id"
    MP4_ID = "mp4_id"


    @classmethod
    def allowed(cls):
        return {cls.ID.value, cls.MP4_ID.value}


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