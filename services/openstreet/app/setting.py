from pydantic import BaseSettings

class Settings(BaseSettings):
    OPENSTREET_URL : str = ""
    OPENSTREET_AP_KEY : str = ""

settings = Settings()
