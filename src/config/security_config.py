import pydantic_settings
import pydantic

class SecurityConfig(pydantic_settings.BaseSettings):
    
    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True
    )

    SECURITY_API_KEY: str = pydantic.Field(
        ...,
        description="API Key utilizada para proteger los endpoints.",
    )