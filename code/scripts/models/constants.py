# DEsCRIPTION: This module defines various constants and enumerations used throughout the Tapeciarnia application, including wallpaper types, range types, sources, playback modes, URI actions, and a dataclass for login payloads. These constants help maintain consistency across the application and provide a clear structure for handling different types of wallpapers, user interactions, and API requests.

from enum import Enum
from dataclasses import dataclass

class WallpaperType(Enum):
    STATIC = "STATIC"
    ANIMATED = "ANIMATED"

class RangeTypes(Enum):
    ANIMATED = "mp4"
    STATIC = "wallpaper"
    ALL = "all"

class Sources(Enum):
    SUPER = "super"
    FAVOURITE = "favourite"
    COLLECTION = "collection"

class PlayBackMode(Enum):
    TILED = "tiled"
    SINGLE = "single"

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