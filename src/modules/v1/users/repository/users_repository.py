import pydantic_mongo
import pymongo
from src.config import ENVIRONMENT_CONFIG
from src.modules.v1.shared.utils import dates as dates_utils
from ..schemas import user_schema
import logging
import typing

LOGGER = logging.getLogger("uvicorn").getChild("v1.users.repository.users")


class UsersRepository(
    pydantic_mongo.AsyncAbstractRepository[user_schema.UserSchema]
):
    class Meta:
        collection_name = ENVIRONMENT_CONFIG.USERS_CONFIG.USER_COLLECTION_NAME

    def _buildSubscribersPipeline(
        self,
        isActive: bool,
        fromDate: int | None,
        toDate: int | None,
    ) -> list[dict[str, typing.Any]]:
        pipeline: list[dict[str, typing.Any]] = [
            {
                "$addFields": {
                    "payDate": {
                        "$convert": {
                            "input": "$lastMembership.membershipPaymentDate",
                            "to": "date",
                            "onError": None,
                            "onNull": None,
                        }
                    },
                    "rawBillingDate": {
                        "$convert": {
                            "input": "$lastMembership.billingDate",
                            "to": "date",
                            "onError": None,
                            "onNull": None,
                        }
                    },
                    "membershipDateConverted": {
                        "$convert": {
                            "input": "$lastMembership.membershipDate",
                            "to": "date",
                            "onError": None,
                            "onNull": None,
                        }
                    },
                }
            },
            {
                "$addFields": {
                    "billDate": {
                        "$cond": {
                            "if": {"$ne": ["$rawBillingDate", None]},
                            "then": "$rawBillingDate",
                            "else": {
                                "$cond": {
                                    "if": {"$ne": ["$membershipDateConverted", None]},
                                    "then": {
                                        "$dateAdd": {
                                            "startDate": "$membershipDateConverted",
                                            "unit": "day",
                                            "amount": 31,
                                        }
                                    },
                                    "else": None,
                                }
                            },
                        }
                    }
                }
            },
        ]

        if fromDate is not None and toDate is not None:
            fromDateParsed = dates_utils.timestampToDatetime(fromDate)
            toDateParsed = dates_utils.timestampToDatetime(toDate)

            pipeline.append(
                {
                    "$match": {
                        "$expr": {
                            "$and": [
                                {"$ne": ["$payDate", None]},
                                {"$gte": ["$payDate", fromDateParsed]},
                                {"$lte": ["$payDate", toDateParsed]},
                            ]
                        }
                    }
                }
            )

        activeConditions: list[dict[str, typing.Any]] = [
            {"$ne": ["$payDate", None]},
            {"$ne": ["$billDate", None]},
            {"$lte": ["$payDate", "$$NOW"]},
            {"$gte": ["$billDate", "$$NOW"]},
        ]

        statusExpr: dict[str, typing.Any]
        if isActive:
            statusExpr = {"$and": activeConditions}
        else:
            statusExpr = {"$not": [{"$and": activeConditions}]}

        pipeline.append(
            {
                "$match": {
                    "lastMembership.type": {"$in": ["monthly", "yearly"]},
                    "$expr": statusExpr,
                }
            }
        )

        return pipeline

    async def countSuscribers(
        self,
        isActive: bool,
        fromDate: int | None,
        toDate: int | None,
    ) -> int:
        """
        Calcula el total de suscriptores activos o inactivos usando una
        agregación que replica la lógica del dashboard.

        El calculo es:
        - Un suscriptor es activo si:
            - lastMembership.membershipPaymentDate existe y es menor o igual a hoy
            - El billingDate (o calculado a partir de membershipDate + 31 días)
              es mayor o igual a hoy
        por lo tal:
        membershipPaymentDate <= hoy <= billingDate
        """
        pipeline = self._buildSubscribersPipeline(
            isActive=isActive,
            fromDate=fromDate,
            toDate=toDate,
        )

        pipeline.append({"$count": "total"})

        cursor = await self.get_collection().aggregate(pipeline)
        result = await cursor.to_list(length=1)
        count = int(result[0]["total"]) if result else 0

        LOGGER.info(
            "Se contaron %s suscriptores usando la agregación: %s",
            count,
            pipeline,
        )

        return count

    async def getSuscribers(
        self,
        isActive: bool,
        fromDate: int | None,
        toDate: int | None,
    ) -> list[user_schema.UserSchema]:
        pipeline = self._buildSubscribersPipeline(
            isActive=isActive,
            fromDate=fromDate,
            toDate=toDate,
        )

        cursor = await self.get_collection().aggregate(pipeline)
        documents = await cursor.to_list(length=None)

        suscribers: list[user_schema.UserSchema] = []
        for document in documents:
            suscribers.append(user_schema.UserSchema.model_validate(document))

        return suscribers

    async def getUsersForGeneralDistribution(
        self,
        subscriberActive: bool | None,
        hasHypnosisRequest: bool | None,
        fromDate: int | None,
        toDate: int | None,
        hypnosisFromDate: int | None,
        hypnosisToDate: int | None,
    ) -> list[user_schema.UserSchema]:
        pipeline: list[dict[str, typing.Any]] = []

        if subscriberActive is not None:
            pipeline.extend(
                self._buildSubscribersPipeline(
                    isActive=subscriberActive,
                    fromDate=fromDate,
                    toDate=toDate,
                )
            )

        if fromDate is not None and toDate is not None:
            fromDateParsed = dates_utils.timestampToDatetime(fromDate)
            toDateParsed = dates_utils.timestampToDatetime(toDate)

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

        useHypnosisFilter = (
            hasHypnosisRequest is not None
            or hypnosisFromDate is not None
            or hypnosisToDate is not None
        )

        if useHypnosisFilter:
            lookupConditions: list[dict[str, typing.Any]] = [
                {"$eq": ["$userId", "$$userId"]},
            ]

            effectiveHypnosisFrom = hypnosisFromDate if hypnosisFromDate is not None else fromDate
            effectiveHypnosisTo = hypnosisToDate if hypnosisToDate is not None else toDate

            if effectiveHypnosisFrom is not None and effectiveHypnosisTo is not None:
                fromDateParsed = dates_utils.timestampToDatetime(effectiveHypnosisFrom)
                toDateParsed = dates_utils.timestampToDatetime(effectiveHypnosisTo)

                createdAtAsDate = {
                    "$convert": {
                        "input": "$createdAt",
                        "to": "date",
                        "onError": None,
                        "onNull": None,
                    }
                }

                lookupConditions.extend(
                    [
                        {"$gte": [createdAtAsDate, fromDateParsed]},
                        {"$lte": [createdAtAsDate, toDateParsed]},
                    ]
                )

            # Si no se determina un rango efectivo se evalúa históricamente.

            lookupPipeline: list[dict[str, typing.Any]] = [
                {
                    "$match": {
                        "$expr": {
                            "$and": lookupConditions,
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

            if hasHypnosisRequest:
                pipeline.append({"$match": {"audioRequests": {"$ne": []}}})
            elif hasHypnosisRequest is False:
                pipeline.append({"$match": {"audioRequests": {"$eq": []}}})

            pipeline.append({"$project": {"audioRequests": 0}})

        if pipeline:
            cursor = await self.get_collection().aggregate(pipeline)
            documents = await cursor.to_list(length=None)
            return [user_schema.UserSchema.model_validate(document) for document in documents]

        cursor = await self.find_by_with_output_type(
            query={},
            output_type=user_schema.UserSchema,
        )

        return list(cursor)

    async def countUsersByHypnosisRequest(
        self,
        isActive: bool,
        fromDate: int | None,
        toDate: int | None,
        subscriberActive: bool | None,
    ) -> int:
        """
        Cuenta usuarios según hayan generado (activos) o no (inactivos) una
        solicitud de hipnosis en el rango proporcionado.

        Sin rango de fechas se evalúa históricamente.
        """

        lookupConditions: list[dict[str, typing.Any]] = [
            {"$eq": ["$userId", "$$userId"]},
        ]

        if fromDate is not None and toDate is not None:
            fromDateParsed = dates_utils.timestampToDatetime(fromDate)
            toDateParsed = dates_utils.timestampToDatetime(toDate)

            createdAtAsDate = {
                "$convert": {
                    "input": "$createdAt",
                    "to": "date",
                    "onError": None,
                    "onNull": None,
                }
            }

            lookupConditions.extend(
                [
                    {"$gte": [createdAtAsDate, fromDateParsed]},
                    {"$lte": [createdAtAsDate, toDateParsed]},
                ]
            )

        lookupPipeline: list[dict[str, typing.Any]] = [
            {
                "$match": {
                    "$expr": {
                        "$and": lookupConditions,
                    }
                }
            },
            {"$limit": 1},
        ]

        pipeline: list[dict[str, typing.Any]] = []

        if subscriberActive is not None:
            pipeline.extend(
                self._buildSubscribersPipeline(
                    isActive=subscriberActive,
                    fromDate=None,
                    toDate=None,
                )
            )

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

        if isActive:
            pipeline.append({"$match": {"audioRequests": {"$ne": []}}})
        else:
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
        fromDate: int | None,
        toDate: int | None,
        subscriberActive: bool | None,
        hasHypnosisRequest: bool | None,
        hypnosisFromDate: int | None,
        hypnosisToDate: int | None,
    ) -> list[user_schema.UserSchema]:
        """
        Obtiene los usuarios pertenecientes a un portal específico.

        Permite filtrar por rango de fechas utilizando createdAt.
        """

        portalStr = str(portal)

        audioPortalLevel: str | None = None
        try:
            portalAsInt = int(portalStr)
        except ValueError:
            audioPortalLevel = None
        else:
            audioPortalLevel = str(max(portalAsInt - 1, 0))

        # Los usuarios se cuentan por el portal actual, pero sus solicitudes pertenecen al nivel previo.

        pipeline: list[dict[str, typing.Any]] = [
            {
                "$match": {
                    "userLevel": portalStr,
                }
            }
        ]

        if subscriberActive is not None:
            pipeline.extend(
                self._buildSubscribersPipeline(
                    isActive=subscriberActive,
                    fromDate=fromDate,
                    toDate=toDate,
                )
            )

        if fromDate is not None and toDate is not None:
            fromDateParsed = dates_utils.timestampToDatetime(fromDate)
            toDateParsed = dates_utils.timestampToDatetime(toDate)

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

        useHypnosisFilter = (
            hasHypnosisRequest is not None
            or hypnosisFromDate is not None
            or hypnosisToDate is not None
        )

        if useHypnosisFilter:
            lookupConditions: list[dict[str, typing.Any]] = [
                {"$eq": ["$userId", "$$userId"]},
            ]

            effectiveHypnosisFrom = hypnosisFromDate if hypnosisFromDate is not None else fromDate
            effectiveHypnosisTo = hypnosisToDate if hypnosisToDate is not None else toDate

            if effectiveHypnosisFrom is not None and effectiveHypnosisTo is not None:
                fromDateParsed = dates_utils.timestampToDatetime(effectiveHypnosisFrom)
                toDateParsed = dates_utils.timestampToDatetime(effectiveHypnosisTo)

                createdAtAsDate = {
                    "$convert": {
                        "input": "$createdAt",
                        "to": "date",
                        "onError": None,
                        "onNull": None,
                    }
                }

                lookupConditions.extend(
                    [
                        {"$gte": [createdAtAsDate, fromDateParsed]},
                        {"$lte": [createdAtAsDate, toDateParsed]},
                    ]
                )

            if audioPortalLevel is not None:
                lookupConditions.append(
                    {
                        "$eq": [
                            {
                                "$convert": {
                                    "input": "$userLevel",
                                    "to": "string",
                                    "onError": None,
                                    "onNull": None,
                                }
                            },
                            "$$audioPortalLevel",
                        ]
                    }
                )

            # Si no se determina un rango efectivo se evalúa históricamente.

            lookupPipeline: list[dict[str, typing.Any]] = [
                {
                    "$match": {
                        "$expr": {
                            "$and": lookupConditions,
                        }
                    }
                },
                {"$limit": 1},
            ]

            pipeline.append(
                {
                    "$lookup": {
                        "from": ENVIRONMENT_CONFIG.HYPNOSIS_CONFIG.HYPNOSIS_COLLECTION_NAME,
                        "let": {
                            "userId": {"$toString": "$_id"},
                            "audioPortalLevel": audioPortalLevel,
                        },
                        "pipeline": lookupPipeline,
                        "as": "audioRequests",
                    }
                }
            )

            if hasHypnosisRequest:
                pipeline.append({"$match": {"audioRequests": {"$ne": []}}})
            elif hasHypnosisRequest is False:
                pipeline.append({"$match": {"audioRequests": {"$eq": []}}})

            pipeline.append({"$project": {"audioRequests": 0}})

        cursor = await self.get_collection().aggregate(pipeline)
        documents = await cursor.to_list(length=None)

        LOGGER.info(
            "Se obtuvieron %s usuarios del portal '%s' con el pipeline: %s",
            len(documents),
            portal,
            pipeline,
        )

        return [user_schema.UserSchema.model_validate(document) for document in documents]

    async def countUsersWithAURA(
        self,
        isActive: bool,
        fromDate: int | None,
        toDate: int | None,
        subscriberActive: bool | None,
    ) -> int:
        """
        Cuenta los usuarios que tienen AURA habilitado.
        """

        matchFilters: list[dict[str, typing.Any]] = [
            {"auraEnabled": isActive},
        ]

        if fromDate is not None and toDate is not None:
            fromDateParsed = dates_utils.timestampToDatetime(fromDate)
            toDateParsed = dates_utils.timestampToDatetime(toDate)

            matchFilters.append(
                {
                    "createdAt": {
                        "$gte": fromDateParsed,
                        "$lte": toDateParsed,
                    }
                }
            )

        if len(matchFilters) == 1:
            baseMatch: dict[str, typing.Any] = matchFilters[0]
        else:
            baseMatch = {"$and": matchFilters}

        if subscriberActive is None:
            count = await self.get_collection().count_documents(baseMatch)
            LOGGER.info(
                "Se contaron %s usuarios con AURA con filtros: %s",
                count,
                baseMatch,
            )
            return count

        pipeline = self._buildSubscribersPipeline(
            isActive=subscriberActive,
            fromDate=None,
            toDate=None,
        )

        pipeline.append({"$match": baseMatch})
        pipeline.append({"$count": "total"})

        cursor = await self.get_collection().aggregate(pipeline)
        result = await cursor.to_list(length=1)
        count = int(result[0]["total"]) if result else 0

        LOGGER.info(
            "Se contaron %s usuarios con AURA filtrando suscriptores (activo=%s) con filtros: %s",
            count,
            subscriberActive,
            baseMatch,
        )

        return count

    async def getDistinctPortals(self) -> list[int]:
        values = await self.get_collection().distinct("userLevel")
        portals: list[int] = []

        for value in values:
            if value is None:
                continue
            try:
                portals.append(int(value))
            except (TypeError, ValueError):
                LOGGER.warning("Valor userLevel no numérico ignorado: %s", value)

        portals.sort()
        LOGGER.info("Se encontraron %s portales distintos: %s", len(portals), portals)
        return portals

USERS_MONGO_CLIENT = pymongo.AsyncMongoClient(
    ENVIRONMENT_CONFIG.CONNECTIONS_CONFIG.MONGO_DATABASE_URL
)

USERS_REPOSITORY = UsersRepository(
    database=USERS_MONGO_CLIENT[
        ENVIRONMENT_CONFIG.USERS_CONFIG.USER_DATABASE_NAME
    ]
)