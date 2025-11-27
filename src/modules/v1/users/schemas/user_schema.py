import pydantic
import pydantic_mongo
import typing
from .membership_schema import MembershipSchema

class UserSchema(pydantic.BaseModel):

    model_config = pydantic.ConfigDict(
        extra="ignore",
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
    )

    id : typing.Optional[pydantic_mongo.PydanticObjectId] = pydantic.Field(
        default=None,
        alias="_id",
        description="Identificador único del usuario.",
    )

    names: str = pydantic.Field(
        ...,
        description="Nombres del usuario.",
    )

    lastnames: str = pydantic.Field(
        ...,
        description="Apellidos del usuario.",
    )

    wantToBeCalled: str = pydantic.Field(
        ...,
        description="Nombre con el que el usuario prefiere ser llamado.",
    )

    email: str = pydantic.Field(
        ...,
        description="Correo electrónico del usuario.",
    )

    gender: str = pydantic.Field(
        ...,
        description="Género del usuario.",
    )

    birthdate: str = pydantic.Field(
        ...,
        description="Fecha de nacimiento del usuario.",
    )

    lastMembership: MembershipSchema = pydantic.Field(
        ...,
        description="Información de la última membresía del usuario.",
    )

    userLevel: typing.Optional[str] = pydantic.Field(
        default=None,
        description="Nivel del usuario (corresponde al portal).",
    )

    features: typing.Dict[str, typing.Any] = pydantic.Field(
        default_factory=dict,
        description="Funcionalidades disponibles para el usuario.",
    )

    auraEnabled: bool = pydantic.Field(
        default=False,
        description="Indica si el aura del usuario está habilitada.",
    )

    language: str = pydantic.Field(
        default="es",
        description="Idioma preferido del usuario.",
    )

class UserCountSchema(pydantic.BaseModel):

    model_config = pydantic.ConfigDict(
        extra="ignore",
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
    )

    count: int = pydantic.Field(
        ...,
        description="Cantidad total de usuarios.",
    )

    fromDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp inicial (segundos Unix) utilizado en el filtrado.",
    )

    toDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp final (segundos Unix) utilizado en el filtrado.",
    )

class UserPortalDistributionSchema(pydantic.BaseModel):

    model_config = pydantic.ConfigDict(
        extra="ignore",
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
        json_schema_extra={
            "example": {
                "portal": "12",
                "totalUsers": 260,
                "genderTotals": {
                    "Mujer": 150,
                    "Hombre": 100,
                    "S/D": 10,
                },
                "languageDistributions": [
                    {
                        "language": "es",
                        "totalUsers": 230,
                        "ageDistribution": {
                            "S/D": 5,
                            "18-24": 70,
                            "25-34": 110,
                            "35-44": 40,
                            "45-54": 5,
                        },
                        "genderDistribution": {
                            "Mujer": 130,
                            "Hombre": 90,
                            "S/D": 10,
                        },
                        "genderAgeBuckets": {
                            "Mujer": {
                                "18-24": 40,
                                "25-34": 70,
                            },
                            "Hombre": {
                                "18-24": 25,
                                "25-34": 50,
                            },
                        },
                    },
                    {
                        "language": "en",
                        "totalUsers": 30,
                        "ageDistribution": {
                            "25-34": 20,
                            "35-44": 10,
                        },
                        "genderDistribution": {
                            "Mujer": 20,
                            "Hombre": 10,
                        },
                        "genderAgeBuckets": {
                            "Mujer": {"25-34": 15},
                            "Hombre": {"35-44": 10},
                        },
                    },
                ],
                "subscriberActive": True,
                "hasHypnosisRequest": None,
                "fromDate": 1730764800,
                "toDate": 1733360400,
                "hypnosisFromDate": None,
                "hypnosisToDate": None,
            }
        },
    )

    portal: str = pydantic.Field(
        ...,
        description="Portal mediante el cual se registró el usuario (valor de userLevel).",
        examples=["12"],
    )

    totalUsers: int = pydantic.Field(
        ...,
        description="Total de usuarios registrados en este portal.",
        examples=[260],
    )

    genderTotals: dict[str, int] = pydantic.Field(
        default_factory=dict,
        description="Conteo total de usuarios por género en el portal.",
        examples=[{"Mujer": 150, "Hombre": 100, "S/D": 10}],
    )

    languageDistributions: list["UserLanguageDistributionSchema"] = pydantic.Field(
        default_factory=list,
        description="Distribución de usuarios agrupada por idioma dentro del portal.",
        examples=[
            [
                {
                    "language": "es",
                    "totalUsers": 230,
                    "ageDistribution": {"18-24": 70, "25-34": 110},
                    "genderDistribution": {"Mujer": 130, "Hombre": 90},
                    "genderAgeBuckets": {"Mujer": {"18-24": 40}},
                }
            ]
        ],
    )

    subscriberActive: typing.Optional[bool] = pydantic.Field(
        default=None,
        description="Filtro aplicado sobre suscriptores (None incluye todos).",
        examples=[True],
    )

    hasHypnosisRequest: typing.Optional[bool] = pydantic.Field(
        default=None,
        description="Filtro aplicado sobre solicitudes de hipnosis (None incluye todos).",
        examples=[None],
    )

    fromDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp inicial (segundos Unix) utilizado en el filtrado.",
        examples=[1730764800],
    )

    toDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp final (segundos Unix) utilizado en el filtrado.",
        examples=[1733360400],
    )

    hypnosisFromDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp inicial (segundos Unix) utilizado para filtrar solicitudes de hipnosis.",
        examples=[1730764800],
    )

    hypnosisToDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp final (segundos Unix) utilizado para filtrar solicitudes de hipnosis.",
        examples=[1733360400],
    )


class UserPortalListSchema(pydantic.BaseModel):

    model_config = pydantic.ConfigDict(
        extra="ignore",
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
    )

    portals: list[int] = pydantic.Field(
        default_factory=list,
        description="Listado ordenado de portales (userLevel) disponibles.",
    )


class UserLanguageDistributionSchema(pydantic.BaseModel):

    model_config = pydantic.ConfigDict(
        extra="ignore",
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
        json_schema_extra={
            "example": {
                "language": "es",
                "totalUsers": 420,
                "ageDistribution": {
                    "S/D": 5,
                    "0-17": 12,
                    "18-24": 80,
                    "25-34": 140,
                    "35-44": 110,
                    "45-54": 55,
                    "55-64": 15,
                    "65+": 3,
                },
                "genderDistribution": {
                    "Mujer": 220,
                    "Hombre": 180,
                    "S/D": 20,
                },
                "genderAgeBuckets": {
                    "Mujer": {
                        "18-24": 40,
                        "25-34": 90,
                        "35-44": 60,
                    },
                    "Hombre": {
                        "18-24": 30,
                        "25-34": 40,
                        "35-44": 50,
                    },
                    "S/D": {
                        "S/D": 20,
                    },
                },
            }
        },
    )

    language: str = pydantic.Field(
        ...,
        description="Idioma reportado por los usuarios.",
        examples=["es"],
    )

    totalUsers: int = pydantic.Field(
        ...,
        description="Cantidad total de usuarios para el idioma.",
        examples=[420],
    )

    ageDistribution: dict[str, int] = pydantic.Field(
        default_factory=dict,
        description="Distribución de edades para el idioma.",
        examples=[{"18-24": 80, "25-34": 140}],
    )

    genderDistribution: dict[str, int] = pydantic.Field(
        default_factory=dict,
        description="Distribución de género para el idioma.",
        examples=[{"Mujer": 220, "Hombre": 180}],
    )

    genderAgeBuckets: dict[str, dict[str, int]] = pydantic.Field(
        default_factory=dict,
        description="Usuarios por género segmentados en buckets de edad.",
        examples=[{"Mujer": {"18-24": 40, "25-34": 90}}],
    )


class UserGeneralDistributionSchema(pydantic.BaseModel):

    model_config = pydantic.ConfigDict(
        extra="ignore",
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
        json_schema_extra={
            "example": {
                "totalUsers": 800,
                "genderTotals": {
                    "Mujer": 420,
                    "Hombre": 330,
                    "S/D": 50,
                },
                "languageDistributions": [
                    {
                        "language": "es",
                        "totalUsers": 600,
                        "ageDistribution": {
                            "S/D": 10,
                            "0-17": 20,
                            "18-24": 160,
                            "25-34": 240,
                            "35-44": 120,
                            "45-54": 40,
                            "55-64": 8,
                            "65+": 2,
                        },
                        "genderDistribution": {
                            "Mujer": 320,
                            "Hombre": 250,
                            "S/D": 30,
                        },
                        "genderAgeBuckets": {
                            "Mujer": {
                                "18-24": 90,
                                "25-34": 120,
                            },
                            "Hombre": {
                                "18-24": 60,
                                "25-34": 100,
                            },
                        },
                    }
                ],
                "subscriberActive": True,
                "hasHypnosisRequest": False,
                "fromDate": 1730764800,
                "toDate": 1733360400,
                "hypnosisFromDate": 1730764800,
                "hypnosisToDate": 1733360400,
            }
        },
    )

    totalUsers: int = pydantic.Field(
        ...,
        description="Cantidad total de usuarios incluidos en la distribución.",
        examples=[800],
    )

    genderTotals: dict[str, int] = pydantic.Field(
        default_factory=dict,
        description="Conteo total de usuarios por género.",
        examples=[{"Mujer": 420, "Hombre": 330, "S/D": 50}],
    )

    languageDistributions: list[UserLanguageDistributionSchema] = pydantic.Field(
        default_factory=list,
        description="Distribución de usuarios agrupada por idioma.",
        examples=[
            [
                {
                    "language": "es",
                    "totalUsers": 600,
                    "ageDistribution": {"18-24": 160, "25-34": 240},
                    "genderDistribution": {"Mujer": 320, "Hombre": 250},
                    "genderAgeBuckets": {"Mujer": {"18-24": 90}},
                }
            ]
        ],
    )

    subscriberActive: typing.Optional[bool] = pydantic.Field(
        default=None,
        description="Filtro aplicado sobre suscriptores (None incluye todos).",
        examples=[True],
    )

    hasHypnosisRequest: typing.Optional[bool] = pydantic.Field(
        default=None,
        description="Filtro aplicado sobre solicitudes de hipnosis (None incluye todos).",
        examples=[False],
    )

    fromDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp inicial aplicado al filtro de creación de usuarios.",
        examples=[1730764800],
    )

    toDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp final aplicado al filtro de creación de usuarios.",
        examples=[1733360400],
    )

    hypnosisFromDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp inicial (segundos Unix) aplicado al filtro de solicitudes de hipnosis.",
        examples=[1730764800],
    )

    hypnosisToDate: typing.Optional[int] = pydantic.Field(
        default=None,
        description="Timestamp final (segundos Unix) aplicado al filtro de solicitudes de hipnosis.",
        examples=[1733360400],
    )