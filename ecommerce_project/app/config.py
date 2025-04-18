import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Your existing fields
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: str
    mail_server: str
    mail_from_name: str
    mail_starttls: bool
    mail_ssl_tls: bool
    stripe_secret_key: str
    stripe_webhook_secret: str

stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY")

class Config:
        env_file = ".env"
        extra = "allow"  # This allows extra fields like stripe_secret_key and stripe_webhook_secret
class Settings(BaseSettings):
    stripe_secret_key: str
    frontend_url: str
    # other fields

    class Config:
        env_file = ".env"
        extra = "ignore" 

# Instantiate the settings
settings = Settings()


