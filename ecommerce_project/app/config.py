from pydantic_settings import BaseSettings
from typing import Optional
class Settings(BaseSettings):
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: str
    mail_server: str
    mail_from_name: str
    mail_starttls: bool
    mail_ssl_tls: bool
    stripe_secret_key: str
    paypal_secret_key: Optional[str] = None 
    paypal_client_id: str
    frontend_url: str
    stripe_webhook_secret: str  

class Config:
        env_file = ".env"
        extra = "allow"  # This allows extra fields like stripe_secret_key and stripe_webhook_secret

settings = Settings()


