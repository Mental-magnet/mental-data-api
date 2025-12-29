import pydantic_mongo
import pymongo
from src.config import ENVIRONMENT_CONFIG
from src.modules.v1.shared.utils import dates as dates_utils
from ..schemas import user_schema
import logging
import typing
from pydantic import TypeAdapter

LOGGER = logging.getLogger("uvicorn").getChild("v1.users.repository.users")


class UsersRepository(pydantic_mongo.AsyncAbstractRepository[user_schema.UserSchema]):
    class Meta:
        collection_name = ENVIRONMENT_CONFIG.USERS_CONFIG.USER_COLLECTION_NAME

    def _buildSubscribersPipeline(
        self,
        isActive: bool,
        fromDate: int | None,
        toDate: int | None,
    ) -> list[dict[str, typing.Any]]:
        # Optimización: Filtrar por tipo de membresía al principio para evitar procesar usuarios irrelevantes
        pipeline: list[dict[str, typing.Any]] = [
            {"$match": {"lastMembership.type": {"$in": ["monthly", "yearly"]}}},
        ]

        # Optimization: Pre-filter by string comparison to avoid expensive $convert on all documents
        # We compare lexicographically: "2024-01-01" <= "2024-01-02" works for ISO strings.
        if fromDate is not None:
            fromDateParsed = dates_utils.timestampToDatetime(fromDate)
            # Assuming dates in DB are roughly ISO format at start
            pipeline.append(
                {
                    "$match": {
                        "lastMembership.membershipPaymentDate": {
                            "$gte": fromDateParsed.isoformat()
                        }
                    }
                }
            )

        pipeline.extend(
            [
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
                                        "if": {
                                            "$ne": ["$membershipDateConverted", None]
                                        },
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
        )

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
                    "$expr": statusExpr,
                }
            }
        )

        return pipeline

    async def getDistributionStats(
        self,
        subscriberActive: bool | None,
        hasHypnosisRequest: bool | None,
        fromDate: int | None,
        toDate: int | None,
        hypnosisFromDate: int | None,
        hypnosisToDate: int | None,
        portal: str | None = None,
    ) -> list[dict[str, typing.Any]]:
        """
        Calcula estadísticas de distribución (género, idioma, edad) directamente en MongoDB.
        """
        pipeline: list[dict[str, typing.Any]] = []

        if portal:
            pipeline.append({"$match": {"userLevel": str(portal)}})

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
                        "createdAt": {"$gte": fromDateParsed, "$lte": toDateParsed}
                    }
                }
            )

        useHypnosisFilter = (
            hasHypnosisRequest is not None
            or hypnosisFromDate is not None
            or hypnosisToDate is not None
        )
        if useHypnosisFilter:
            effectiveHypnosisFrom = (
                hypnosisFromDate if hypnosisFromDate is not None else fromDate
            )
            effectiveHypnosisTo = (
                hypnosisToDate if hypnosisToDate is not None else toDate
            )

            lookupConditions = [{"$eq": ["$userId", "$$userId"]}]

            let_vars = {"userId": {"$toString": "$_id"}}
            if portal:
                try:
                    portalAsInt = int(portal)
                    audioPortalLevel = str(max(portalAsInt - 1, 0))
                    let_vars["audioPortalLevel"] = audioPortalLevel
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
                except (ValueError, TypeError):
                    pass

            if effectiveHypnosisFrom is not None and effectiveHypnosisTo is not None:
                fromP = dates_utils.timestampToDatetime(effectiveHypnosisFrom)
                toP = dates_utils.timestampToDatetime(effectiveHypnosisTo)
                lookupConditions.append(
                    {
                        "$gte": [
                            {
                                "$convert": {
                                    "input": "$createdAt",
                                    "to": "date",
                                    "onError": None,
                                    "onNull": None,
                                }
                            },
                            fromP,
                        ]
                    }
                )
                lookupConditions.append(
                    {
                        "$lte": [
                            {
                                "$convert": {
                                    "input": "$createdAt",
                                    "to": "date",
                                    "onError": None,
                                    "onNull": None,
                                }
                            },
                            toP,
                        ]
                    }
                )

            pipeline.append(
                {
                    "$lookup": {
                        "from": ENVIRONMENT_CONFIG.HYPNOSIS_CONFIG.HYPNOSIS_COLLECTION_NAME,
                        "let": let_vars,
                        "pipeline": [
                            {"$match": {"$expr": {"$and": lookupConditions}}},
                            {"$project": {"_id": 1}},
                            {"$limit": 1},
                        ],
                        "as": "audioRequests",
                    }
                }
            )
            if hasHypnosisRequest:
                pipeline.append({"$match": {"audioRequests": {"$ne": []}}})
            elif hasHypnosisRequest is False:
                pipeline.append({"$match": {"audioRequests": {"$eq": []}}})

        # Fase de Agregación de Estadísticas
        pipeline.extend(
            [
                {
                    "$project": {
                        "gender": {"$ifNull": ["$gender", "S/D"]},
                        "language": {"$ifNull": ["$language", "es"]},
                        "birthdate": {"$ifNull": ["$birthdate", ""]},
                    }
                },
                {
                    "$project": {
                        "gender": 1,
                        "language": 1,
                        "year": {
                            "$convert": {
                                "input": {"$substr": ["$birthdate", 0, 4]},
                                "to": "int",
                                "onError": 0,
                                "onNull": 0,
                            }
                        },
                    }
                },
                {
                    "$project": {
                        "gender": 1,
                        "language": 1,
                        "age": {
                            "$cond": [
                                {"$eq": ["$year", 0]},
                                -1,
                                {"$subtract": [{"$year": "$$NOW"}, "$year"]},
                            ]
                        },
                    }
                },
                {
                    "$project": {
                        "gender": 1,
                        "language": 1,
                        "ageBucket": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$lt": ["$age", 0]}, "then": "S/D"},
                                    {"case": {"$lt": ["$age", 18]}, "then": "0-17"},
                                    {"case": {"$lte": ["$age", 24]}, "then": "18-24"},
                                    {"case": {"$lte": ["$age", 34]}, "then": "25-34"},
                                    {"case": {"$lte": ["$age", 44]}, "then": "35-44"},
                                    {"case": {"$lte": ["$age", 54]}, "then": "45-54"},
                                    {"case": {"$lte": ["$age", 64]}, "then": "55-64"},
                                ],
                                "default": "65+",
                            }
                        },
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "language": "$language",
                            "gender": "$gender",
                            "ageBucket": "$ageBucket",
                        },
                        "count": {"$sum": 1},
                    }
                },
            ]
        )

        cursor = await self.get_collection().aggregate(pipeline)
        return await cursor.to_list(length=None)

    async def countSuscribers(
        self, isActive: bool, fromDate: int | None, toDate: int | None
    ) -> int:
        pipeline = self._buildSubscribersPipeline(
            isActive=isActive, fromDate=fromDate, toDate=toDate
        )
        pipeline.append({"$count": "total"})
        cursor = await self.get_collection().aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return int(result[0]["total"]) if result else 0

    async def getSuscribers(
        self, isActive: bool, fromDate: int | None, toDate: int | None
    ) -> list[user_schema.UserSchema]:
        pipeline = self._buildSubscribersPipeline(
            isActive=isActive, fromDate=fromDate, toDate=toDate
        )
        cursor = await self.get_collection().aggregate(pipeline)
        documents = await cursor.to_list(length=None)
        return TypeAdapter(list[user_schema.UserSchema]).validate_python(documents)

    async def countUsersByHypnosisRequest(
        self,
        isActive: bool,
        fromDate: int | None,
        toDate: int | None,
        subscriberActive: bool | None,
    ) -> int:
        lookupConditions = [{"$eq": ["$userId", "$$userId"]}]
        if fromDate is not None and toDate is not None:
            fromDateP = dates_utils.timestampToDatetime(fromDate)
            toDateP = dates_utils.timestampToDatetime(toDate)
            lookupConditions.append(
                {
                    "$gte": [
                        {
                            "$convert": {
                                "input": "$createdAt",
                                "to": "date",
                                "onError": None,
                                "onNull": None,
                            }
                        },
                        fromDateP,
                    ]
                }
            )
            lookupConditions.append(
                {
                    "$lte": [
                        {
                            "$convert": {
                                "input": "$createdAt",
                                "to": "date",
                                "onError": None,
                                "onNull": None,
                            }
                        },
                        toDateP,
                    ]
                }
            )

        pipeline = []
        if subscriberActive is not None:
            pipeline.extend(
                self._buildSubscribersPipeline(
                    isActive=subscriberActive, fromDate=None, toDate=None
                )
            )

        pipeline.append(
            {
                "$lookup": {
                    "from": ENVIRONMENT_CONFIG.HYPNOSIS_CONFIG.HYPNOSIS_COLLECTION_NAME,
                    "let": {"userId": {"$toString": "$_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$and": lookupConditions}}},
                        {"$project": {"_id": 1}},
                        {"$limit": 1},
                    ],
                    "as": "audioRequests",
                }
            }
        )
        pipeline.append(
            {"$match": {"audioRequests": {"$ne": []}}}
            if isActive
            else {"$match": {"audioRequests": {"$eq": []}}}
        )
        pipeline.append({"$count": "count"})

        cursor = await self.get_collection().aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return typing.cast(int, result[0]["count"]) if result else 0

    async def countUsersWithAURA(
        self,
        isActive: bool,
        fromDate: int | None,
        toDate: int | None,
        subscriberActive: bool | None,
    ) -> int:
        matchFilters = [{"auraEnabled": isActive}]
        if fromDate is not None and toDate is not None:
            matchFilters.append(
                {
                    "createdAt": {
                        "$gte": dates_utils.timestampToDatetime(fromDate),
                        "$lte": dates_utils.timestampToDatetime(toDate),
                    }
                }
            )
        baseMatch = (
            matchFilters[0] if len(matchFilters) == 1 else {"$and": matchFilters}
        )

        if subscriberActive is None:
            return await self.get_collection().count_documents(baseMatch)

        pipeline = self._buildSubscribersPipeline(
            isActive=subscriberActive, fromDate=None, toDate=None
        )
        pipeline.append({"$match": baseMatch})
        pipeline.append({"$count": "total"})
        cursor = await self.get_collection().aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return int(result[0]["total"]) if result else 0

    async def getDistinctPortals(self) -> list[int]:
        values = await self.get_collection().distinct("userLevel")
        portals = []
        for v in values:
            if v is not None:
                try:
                    portals.append(int(v))
                except Exception:
                    continue
        portals.sort()
        return portals


USERS_MONGO_CLIENT = pymongo.AsyncMongoClient(
    ENVIRONMENT_CONFIG.CONNECTIONS_CONFIG.MONGO_DATABASE_URL
)
USERS_REPOSITORY = UsersRepository(
    database=USERS_MONGO_CLIENT[ENVIRONMENT_CONFIG.USERS_CONFIG.USER_DATABASE_NAME]
)
