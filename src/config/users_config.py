import pydantic_settings
import pydantic

class UsersConfig(pydantic_settings.BaseSettings):
    
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



    USER_DATABASE_NAME: str = pydantic.Field(
        default="mmg",
        description="Nombre de la base de datos donde se almacenan los usuarios.",
    )

    USER_COLLECTION_NAME: str = pydantic.Field(
        default="users",
        description="Nombre de la colección que contiene los documentos de usuarios.",
    )