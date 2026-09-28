from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agentsure"
    environment: str = "dev"
    database_url: str = "sqlite:///./agentsure.db"
    queue_mode: str = "inline"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "agentsure.evaluations"
    otel_service_name: str = "agentsure-api"
    otel_exporter_otlp_endpoint: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
