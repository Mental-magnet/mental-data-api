import pydantic_settings
import pydantic

class HypnosisConfig(pydantic_settings.BaseSettings):
    
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


    
    HYPNOSIS_DATABASE_NAME: str = pydantic.Field(
        default="mmg",
        description="Nombre de la base de datos utilizada para hipnosis.",
    )

    HYPNOSIS_COLLECTION_NAME: str = pydantic.Field(
        default="audio-requests",
        description="Nombre de la colección donde se guardan las solicitudes de audio.",
    )