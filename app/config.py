"""App configuration from environment."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    RETELL_API_KEY: str = os.getenv("RETELL_API_KEY", "")

    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    IMAP_HOST: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_USER: str = os.getenv("IMAP_USER", "")
    IMAP_PASSWORD: str = os.getenv("IMAP_PASSWORD", "")

    RETELL_AGENT_ID: str = os.getenv("RETELL_AGENT_ID", "agent_a8ede5afc28f6ed16682a94e75")
    RETELL_LLM_ID: str = os.getenv("RETELL_LLM_ID", "llm_ebd65462dc353925430ea29eaa7c")
    RETELL_FROM_NUMBER: str = os.getenv("RETELL_FROM_NUMBER", "+12012318503")

    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
    DB_PATH: str = os.getenv("DB_PATH", "data/mystery.db")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
