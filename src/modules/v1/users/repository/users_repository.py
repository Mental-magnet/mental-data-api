import pydantic_mongo
import pymongo
from src.config import ENVIRONMENT_CONFIG
from src.modules.v1.shared.utils import dates as dates_utils
from ..schemas import user_schema
import logging
import typing

LOGGER = logging.getLogger("uvicorn").getChild("v1.users.repository.users")


class UsersRepository(
    pydantic_mongo.AbstractRepository[user_schema.UserSchema]
):
    class Meta:
        collection_name = ENVIRONMENT_CONFIG.USERS_CONFIG.USER_COLLECTION_NAME

    async def countSuscribers(
        self,
        isActive: bool,
        fromDate: str | None,
        toDate: str | None,
    ) -> int:
        """
        Todos los usuarios activos son aquellos donde
        last.Membership.membershipDate + 1 month > hoy

        Al no proveer un rango de fechas, se cuentan todos los usuarios activos.
        """

        queryFilters = []

        membershipStatusExpr = {
            "$let": {
                "vars": {
                    "membershipDate": {
                        "$convert": {
                            "input": "$lastMembership.membershipDate",
                            "to": "date",
                            "onError": None,
                            "onNull": None,
                        }
                    },
                    "now": "$$NOW",
                },
                "in": {
                    "$and": [
                        {"$ne": ["$$membershipDate", None]},
                        {
                            "$gt": [
                                {
                                    "$dateAdd": {
                                        "startDate": "$$membershipDate",
                                        "unit": "month",
                                        "amount": 1,
                                    }
                                },
                                "$$now",
                            ]
                        },
                    ]
                },
            }
        }

        if isActive:
            # Suscriptor activo: la membresía extendida un mes sigue vigente.
            queryFilters.append({"$expr": membershipStatusExpr})
        else:
            # Suscriptor inactivo: negamos la condición anterior para capturar al resto.
            queryFilters.append({"$expr": {"$not": membershipStatusExpr}})

        # Si se proveen fromDate y toDate, añadimos el filtro
        # Donde createdAt está entre fromDate y toDate
        if fromDate is not None and toDate is not None:
            fromDateParsed = dates_utils.parseISODatetime(fromDate)
            toDateParsed = dates_utils.parseISODatetime(toDate)

            queryFilters.append(
                {
                    "createdAt": {
                        "$gte": fromDateParsed,
                        "$lte": toDateParsed,
                    }
                }
            )

        if not queryFilters:
            query: dict[str, object] = {}
        elif len(queryFilters) == 1:
            query = queryFilters[0]
        else:
            query = {"$and": queryFilters}

        count : int = await self.get_collection().count_documents(query)
        LOGGER.info(
            f"Se contaron {count} suscriptores con la consulta: {query}"
        )
        return count

    async def countUsersWithoutHypnosisRequest(
        self,
        fromDate: str | None,
        toDate: str | None,
    ) -> int:
        """
        Cuenta los usuarios que no han generado una solicitud de hipnosis.

        Si se proporciona un rango de fechas, se filtra por createdAt dentro del rango.
        """

        pipeline: list[dict[str, typing.Any]] = []

        if fromDate is not None and toDate is not None:
            fromDateParsed = dates_utils.parseISODatetime(fromDate)
            toDateParsed = dates_utils.parseISODatetime(toDate)

            pipeline.append(
                {
                    "$match": {
                        "createdAt": {
                            "$gte": fromDateParsed,
                            "$lte": toDateParsed,
                        }
                    }
                }
            )

        lookupPipeline: list[dict[str, typing.Any]] = [
            {
                "$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$userId", "$$userId"]},
                        ]
                    }
                }
            },
            {"$limit": 1},
        ]

        pipeline.append(
            {
                "$lookup": {
                    "from": ENVIRONMENT_CONFIG.HYPNOSIS_CONFIG.HYPNOSIS_COLLECTION_NAME,
                    "let": {"userId": {"$toString": "$_id"}},
                    "pipeline": lookupPipeline,
                    "as": "audioRequests",
                }
            }
        )

        pipeline.append({"$match": {"audioRequests": {"$eq": []}}})
        pipeline.append({"$count": "count"})

        cursor = await self.get_collection().aggregate(pipeline)
        result = await cursor.to_list(length=1)
        if result:
            return typing.cast(int, result[0]["count"])
        return 0

    async def getUsersByPortal(
        self,
        portal: str,
        fromDate: str | None,
        toDate: str | None,
    ) -> list[user_schema.UserSchema]:
        """
        Obtiene los usuarios pertenecientes a un portal específico.

        Permite filtrar por rango de fechas utilizando createdAt.
        """

        queryFilters: list[dict[str, typing.Any]] = [
            {"userLevel": portal},
        ]

        if fromDate is not None and toDate is not None:
            fromDateParsed = dates_utils.parseISODatetime(fromDate)
            toDateParsed = dates_utils.parseISODatetime(toDate)

            queryFilters.append(
                {
                    "createdAt": {
                        "$gte": fromDateParsed,
                        "$lte": toDateParsed,
                    }
                }
            )

        if len(queryFilters) == 1:
            query: dict[str, typing.Any] = queryFilters[0]
        else:
            query = {"$and": queryFilters}

        cursor = self.get_collection().find(query)
        documents: list[dict[str, typing.Any]] = []
        async for document in cursor:
            documents.append(document)
        return [
            user_schema.UserSchema.model_validate(document)
            for document in documents
        ]

    async def countUsersWithAURA(
        self,
        isActive: bool,
        fromDate: str | None,
        toDate: str | None,
    ) -> int:
        """
        Cuenta los usuarios que tienen AURA habilitado.
        """

        queryFilters = []

        if isActive:
            queryFilters.append({"auraEnabled": True})
        else:
            queryFilters.append({"auraEnabled": False})

        if fromDate is not None and toDate is not None:
            fromDateParsed = dates_utils.parseISODatetime(fromDate)
            toDateParsed = dates_utils.parseISODatetime(toDate)

            queryFilters.append(
                {
                    "createdAt": {
                        "$gte": fromDateParsed,
                        "$lte": toDateParsed,
                    }
                }
            )

        if not queryFilters:
            query: dict[str, object] = {}
        elif len(queryFilters) == 1:
            query = queryFilters[0]
        else:
            query = {"$and": queryFilters}

        count = await self.get_collection().count_documents(query)
        LOGGER.info(
            f"Se contaron {count} usuarios con AURA usando la consulta: {query}"
        )
        return count


USERS_MONGO_CLIENT = pymongo.AsyncMongoClient(
    ENVIRONMENT_CONFIG.CONNECTIONS_CONFIG.MONGO_DATABASE_URL
)

USERS_REPOSITORY = UsersRepository(
    database=USERS_MONGO_CLIENT[
        ENVIRONMENT_CONFIG.USERS_CONFIG.USER_DATABASE_NAME
    ]
)