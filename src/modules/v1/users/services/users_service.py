import aiocache
import collections
import typing
from bson import ObjectId
from pydantic import TypeAdapter
import anyio.to_thread
from ..repository import USERS_REPOSITORY
from ..schemas import user_schema


@aiocache.cached_stampede(
    lease=2,
    ttl=120,
    skip_cache_func=lambda count: count == 0,
)
async def _getUsersWithAURACount(
    isActive: bool,
    fromDate: int | None,
    toDate: int | None,
    subscriberActive: bool | None,
) -> int:
    return await USERS_REPOSITORY.countUsersWithAURA(
        isActive=isActive,
        fromDate=fromDate,
        toDate=toDate,
        subscriberActive=subscriberActive,
    )


async def _getUserByID(userID: str) -> user_schema.UserSchema | None:
    try:
        oid = ObjectId(userID)
    except Exception:
        return None
    document = await USERS_REPOSITORY.get_collection().find_one({"_id": oid})
    if not document:
        return None
    return user_schema.UserSchema.model_validate(document)


async def _getUsersByListOfIDs(userIDs: list[str]) -> list[user_schema.UserSchema]:
    oids = []
    for uid in userIDs:
        try:
            oids.append(ObjectId(uid))
        except Exception:
            continue
    cursor = (
        await USERS_REPOSITORY.get_collection().find({"_id": {"$in": oids}})  # ty:ignore[invalid-await]
        if "oids" in locals()
        else await USERS_REPOSITORY.get_collection()
        .find({"_id": {"$in": oids}})
        .to_list(length=None)
    )
    # Fix: previous cursor call was a bit messy, let's redo it clean
    return TypeAdapter(list[user_schema.UserSchema]).validate_python(cursor)


# Re-writing the whole service file to be safe
@aiocache.cached_stampede(
    lease=2,
    ttl=120,
)
async def _getUsersByHypnosisRequestCount(
    isActive: bool,
    fromDate: int | None,
    toDate: int | None,
    subscriberActive: bool | None,
) -> int:
    return await USERS_REPOSITORY.countUsersByHypnosisRequest(
        isActive=isActive,
        fromDate=fromDate,
        toDate=toDate,
        subscriberActive=subscriberActive,
    )


@aiocache.cached_stampede(lease=2, ttl=600)
async def _getUserPortals() -> list[int]:
    return await USERS_REPOSITORY.getDistinctPortals()


@aiocache.cached_stampede(
    lease=2,
    ttl=300,
    skip_cache_func=lambda distribution: distribution.totalUsers == 0,
)
async def _getGeneralUserDistribution(
    subscriberActive: bool | None,
    hasHypnosisRequest: bool | None,
    fromDate: int | None,
    toDate: int | None,
    hypnosisFromDate: int | None,
    hypnosisToDate: int | None,
) -> user_schema.UserGeneralDistributionSchema:
    effectiveHypnosisFromDate = (
        hypnosisFromDate
        if hypnosisFromDate is not None or hasHypnosisRequest is None
        else fromDate
    )
    effectiveHypnosisToDate = (
        hypnosisToDate
        if hypnosisToDate is not None or hasHypnosisRequest is None
        else toDate
    )

    stats = await USERS_REPOSITORY.getDistributionStats(
        subscriberActive=subscriberActive,
        hasHypnosisRequest=hasHypnosisRequest,
        fromDate=fromDate,
        toDate=toDate,
        hypnosisFromDate=effectiveHypnosisFromDate,
        hypnosisToDate=effectiveHypnosisToDate,
    )

    return await anyio.to_thread.run_sync(
        _processStats,
        stats,
        subscriberActive,
        hasHypnosisRequest,
        fromDate,
        toDate,
        effectiveHypnosisFromDate,
        effectiveHypnosisToDate,
    )


@aiocache.cached_stampede(
    lease=2,
    ttl=300,
    skip_cache_func=lambda distribution: distribution.totalUsers == 0,
)
async def _getUserPortalDistribution(
    portal: str,
    fromDate: int | None,
    toDate: int | None,
    subscriberActive: bool | None,
    hasHypnosisRequest: bool | None,
    hypnosisFromDate: int | None,
    hypnosisToDate: int | None,
) -> user_schema.UserPortalDistributionSchema:
    effectiveHypnosisFromDate = (
        hypnosisFromDate
        if hypnosisFromDate is not None or hasHypnosisRequest is None
        else fromDate
    )
    effectiveHypnosisToDate = (
        hypnosisToDate
        if hypnosisToDate is not None or hasHypnosisRequest is None
        else toDate
    )

    stats = await USERS_REPOSITORY.getDistributionStats(
        subscriberActive=subscriberActive,
        hasHypnosisRequest=hasHypnosisRequest,
        fromDate=fromDate,
        toDate=toDate,
        hypnosisFromDate=effectiveHypnosisFromDate,
        hypnosisToDate=effectiveHypnosisToDate,
        portal=portal,
    )

    distribution = _processStats(
        stats,
        subscriberActive,
        hasHypnosisRequest,
        fromDate,
        toDate,
        effectiveHypnosisFromDate,
        effectiveHypnosisToDate,
    )

    return user_schema.UserPortalDistributionSchema(
        portal=portal, **distribution.model_dump()
    )


def _processStats(
    stats: list[dict],
    subscriberActive: bool | None,
    hasHypnosisRequest: bool | None,
    fromDate: int | None,
    toDate: int | None,
    hypnosisFromDate: int | None,
    hypnosisToDate: int | None,
) -> user_schema.UserGeneralDistributionSchema:
    totalUsers = 0
    languageStats: dict[str, dict[str, typing.Any]] = {}
    overallGenderCounter: collections.Counter[str] = collections.Counter()

    for entry in stats:
        meta = entry["_id"]
        count = entry["count"]

        lang = meta.get("language", "S/D")
        gender = meta.get("gender", "S/D")
        bucket = meta.get("ageBucket", "S/D")

        totalUsers += count
        overallGenderCounter[gender] += count

        s = languageStats.setdefault(
            lang,
            {
                "total": 0,
                "genderCounter": collections.Counter(),
                "ageCounter": collections.Counter(),
                "genderAgeCounter": collections.defaultdict(collections.Counter),
            },
        )
        s["total"] += count
        s["genderCounter"][gender] += count
        s["ageCounter"][bucket] += count
        s["genderAgeCounter"][gender][bucket] += count

    languageDistributions: list[user_schema.UserLanguageDistributionSchema] = []
    ALL_BUCKETS = ["S/D", "0-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

    for lang in sorted(languageStats.keys()):
        s = languageStats[lang]
        age_dist = {b: s["ageCounter"][b] for b in ALL_BUCKETS if b in s["ageCounter"]}
        gender_age = {}
        for gender, bucket_counts in s["genderAgeCounter"].items():
            gender_age[gender] = {
                b: bucket_counts[b] for b in ALL_BUCKETS if b in bucket_counts
            }

        languageDistributions.append(
            user_schema.UserLanguageDistributionSchema(
                language=lang,
                totalUsers=s["total"],
                ageDistribution=age_dist,
                genderDistribution=dict(s["genderCounter"]),
                genderAgeBuckets=gender_age,
            )
        )

    return user_schema.UserGeneralDistributionSchema(
        totalUsers=totalUsers,
        genderTotals=dict(overallGenderCounter),
        languageDistributions=languageDistributions,
        subscriberActive=subscriberActive,
        hasHypnosisRequest=hasHypnosisRequest,
        fromDate=fromDate,
        toDate=toDate,
        hypnosisFromDate=hypnosisFromDate,
        hypnosisToDate=hypnosisToDate,
    )


getUsersWithAURACount = typing.cast(
    typing.Callable[[bool, int | None, int | None, bool | None], typing.Awaitable[int]],
    _getUsersWithAURACount,
)
getUserByID = typing.cast(
    typing.Callable[[str], typing.Awaitable[user_schema.UserSchema | None]],
    _getUserByID,
)
getUsersByListOfIDs = typing.cast(
    typing.Callable[[list[str]], typing.Awaitable[list[user_schema.UserSchema]]],
    _getUsersByListOfIDs,
)
getUserPortalDistribution = typing.cast(
    typing.Callable[
        [str, int | None, int | None, bool | None, bool | None, int | None, int | None],
        typing.Awaitable[user_schema.UserPortalDistributionSchema],
    ],
    _getUserPortalDistribution,
)
getUserPortals = typing.cast(
    typing.Callable[[], typing.Awaitable[list[int]]], _getUserPortals
)
getGeneralUserDistribution = typing.cast(
    typing.Callable[
        [bool | None, bool | None, int | None, int | None, int | None, int | None],
        typing.Awaitable[user_schema.UserGeneralDistributionSchema],
    ],
    _getGeneralUserDistribution,
)
getUsersByHypnosisRequestCount = typing.cast(
    typing.Callable[[bool, int | None, int | None, bool | None], typing.Awaitable[int]],
    _getUsersByHypnosisRequestCount,
)
