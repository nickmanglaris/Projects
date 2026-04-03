from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///../data/cards.db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    ANTHROPIC_API_KEY: str = ""

    EBAY_CLIENT_ID: str = "YOUR_CLIENT_ID_HERE"
    EBAY_CLIENT_SECRET: str = "YOUR_CLIENT_SECRET_HERE"
    EBAY_REDIRECT_URI: str = "http://localhost:8000/api/v1/ebay/auth/callback"
    EBAY_SANDBOX: bool = True

    @property
    def ebay_connected(self) -> bool:
        return (
            self.EBAY_CLIENT_ID not in ("YOUR_CLIENT_ID_HERE", "")
            and self.EBAY_CLIENT_SECRET not in ("YOUR_CLIENT_SECRET_HERE", "")
        )


settings = Settings()
