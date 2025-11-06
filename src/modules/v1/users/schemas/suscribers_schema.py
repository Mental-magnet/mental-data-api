import pydantic
import typing

class SuscribersSchema(pydantic.BaseModel):

    model_config = pydantic.ConfigDict(
        extra="ignore",
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
    )

    count: int = pydantic.Field(
        ...,
        description="Cantidad de suscriptores."
    )

    fromDate: typing.Optional[str] = pydantic.Field(
        default=None,
        description="Fecha desde la cual se contabilizan los suscriptores.",
    )

    toDate: typing.Optional[str] = pydantic.Field(
        default=None,
        description="Fecha hasta la cual se contabilizan los suscriptores.",
    )