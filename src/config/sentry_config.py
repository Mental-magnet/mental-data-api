import pydantic_settings
import pydantic

class SentryConfig(pydantic_settings.BaseSettings):
    
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

    SENTRY_DSN: str = pydantic.Field(
        ...,
        description="DSN (Data Source Name) utilizado para el monitoreo de errores en Sentry.",
    )

    SENTRY_ENVIRONMENT: str = pydantic.Field(
        default="staging",
        description="Entorno en el que se ejecuta la aplicación (por ejemplo, development, staging, production).",
    )

    SENTRY_SAMPLE_RATE: float = pydantic.Field(
        default=0.1,
        description="Tasa de muestreo para el seguimiento de errores en Sentry (entre 0.0 y 1.0).",
    )

    SENTRY_RELEASE: str = pydantic.Field(
        default="v1",
        description="Versión de la aplicación utilizada para el seguimiento en Sentry.",
    )

    SENTRY_ENABLE_LOGS: bool = pydantic.Field(
        default=True,
        description="Indica si se habilita el registro de logs para Sentry.",
    )