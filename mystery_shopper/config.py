"""Configuration management."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    IMAP_HOST: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_USER: str = os.getenv("IMAP_USER", "")
    IMAP_PASSWORD: str = os.getenv("IMAP_PASSWORD", "")

    # Voice
    RETELL_API_KEY: str = os.getenv("RETELL_API_KEY", "")

    # Web
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8000"))

    # Data
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))

    def __init__(self):
        self.DATA_DIR.mkdir(exist_ok=True)


config = Config()
