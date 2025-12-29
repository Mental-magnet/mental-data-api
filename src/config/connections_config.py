import pydantic_settings
import pydantic


class ConnectionsConfig(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
    )

    MONGO_DATABASE_URL: str = pydantic.Field(
        default="mongodb://localhost:27017/mmg",
        description="URL de conexión a la base de datos MongoDB.",
    )

    REDIS_URL: str = pydantic.Field(
        default="redis://localhost:6379",
        description="URL de conexión a Redis.",
    )
