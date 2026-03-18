import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")

    @classmethod
    def validate(cls):
        missing = [name for name in ("EMAIL_USER", "EMAIL_PASS") if not getattr(cls, name)]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
