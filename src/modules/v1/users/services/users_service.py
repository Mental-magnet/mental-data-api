import aiocache
import collections
import datetime
import typing
from src.modules.v1.shared.utils import dates as dates_utils
from ..repository import USERS_REPOSITORY
from ..schemas import user_schema
import anyio.to_thread

@aiocache.cached_stampede(
    lease=2,
    ttl=300,
    skip_cache_func=lambda count: count == 0,
)
async def _getUsersWithAURACount(
    isActive: bool,
    fromDate: int | None,
    toDate: int | None,
    subscriberActive: bool | None,
) -> int:

    count = await USERS_REPOSITORY.countUsersWithAURA(
        isActive=isActive,
        fromDate=fromDate,
        toDate=toDate,
        subscriberActive=subscriberActive,
    )

    return count



@aiocache.cached_stampede(
    lease=2,
    ttl=300,
)
async def _getUserByID(
    userID: str,
) -> user_schema.UserSchema | None:
    """
    Obtiene un usuario por su ID.
    """

    user = await USERS_REPOSITORY.getUserByID(userID=userID)
    return user



@aiocache.cached_stampede(
    lease=2,
    ttl=300,
    skip_cache_func=lambda userIDs: len(userIDs) == 0,
)
async def _getUsersByListOfIDs(
    userIDs: list[str],
) -> list[user_schema.UserSchema]:
    """
    Obtiene una lista de usuarios por sus IDs.
    """

    users = await USERS_REPOSITORY.getUsersByListOfIDs(userIDs=userIDs)

    return users



@aiocache.cached_stampede(
    lease=2,
    ttl=300,
    skip_cache_func=lambda count: count == 0,
)
async def _getUsersByHypnosisRequestCount(
    isActive: bool,
    fromDate: int | None,
    toDate: int | None,
    subscriberActive: bool | None,
) -> int:

    count = await USERS_REPOSITORY.countUsersByHypnosisRequest(
        isActive=isActive,
        fromDate=fromDate,
        toDate=toDate,
        subscriberActive=subscriberActive,
    )

    return count


getUsersByHypnosisRequestCount = typing.cast(
    typing.Callable[
        [bool, int | None, int | None, bool | None], typing.Awaitable[int]
    ],
    _getUsersByHypnosisRequestCount,
)


@aiocache.cached_stampede(
    lease=2,
    ttl=300,
    skip_cache_func=lambda portals: len(portals) == 0,
)
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
    effectiveHypnosisFromDate = hypnosisFromDate
    effectiveHypnosisToDate = hypnosisToDate

    # Cuando no se especifica un rango propio para hipnosis reutilizamos el de creación
    # para mantener compatibilidad con las consultas anteriores.
    if effectiveHypnosisFromDate is None and hasHypnosisRequest is not None:
        effectiveHypnosisFromDate = fromDate

    if effectiveHypnosisToDate is None and hasHypnosisRequest is not None:
        effectiveHypnosisToDate = toDate

    users = await USERS_REPOSITORY.getUsersForGeneralDistribution(
        subscriberActive=subscriberActive,
        hasHypnosisRequest=hasHypnosisRequest,
        fromDate=fromDate,
        toDate=toDate,
        hypnosisFromDate=effectiveHypnosisFromDate,
        hypnosisToDate=effectiveHypnosisToDate,
    )

    return _buildGeneralDistribution(
        users=users,
        subscriberActive=subscriberActive,
        hasHypnosisRequest=hasHypnosisRequest,
        fromDate=fromDate,
        toDate=toDate,
        hypnosisFromDate=effectiveHypnosisFromDate,
        hypnosisToDate=effectiveHypnosisToDate,
    )

# Definimos los rangos de edad para la distribución
AGE_BUCKETS: tuple[tuple[str, int, int | None], ...] = (
    ("18-24", 18, 24),
    ("25-34", 25, 34),
    ("35-44", 35, 44),
    ("45-54", 45, 54),
    ("55-64", 55, 64),
    ("65+", 65, None),
)

# Edad por debajo de la cual se considera "menor de edad"
UNDERAGE_BUCKET = "0-17"

UNKNOWN_LABEL = "S/D"
UNKNOWN_AGE = UNKNOWN_LABEL


def _calculateAge(birthdate: str, reference: datetime.datetime) -> int | None:
    try:
        birthDatetime = dates_utils.parseISODatetime(birthdate)
    except ValueError:
        return None

    if birthDatetime.tzinfo is None:
        birthDatetime = birthDatetime.replace(tzinfo=datetime.timezone.utc)

    referenceUTC = reference.astimezone(datetime.timezone.utc)

    years = referenceUTC.year - birthDatetime.year
    hasHadBirthday = (
        (referenceUTC.month, referenceUTC.day)
        >= (birthDatetime.month, birthDatetime.day)
    )

    return years if hasHadBirthday else years - 1


def _resolveAgeBucket(age: int) -> str:
    if age < AGE_BUCKETS[0][1]:
        return UNDERAGE_BUCKET

    for bucketName, startAge, endAge in AGE_BUCKETS:
        if age < startAge:
            continue
        if endAge is None or age <= endAge:
            return bucketName

    return AGE_BUCKETS[-1][0]


def _buildOrderedAgeDistribution(counter: collections.Counter[str]) -> dict[str, int]:
    ordered: dict[str, int] = {}

    if counter.get(UNKNOWN_AGE):
        ordered[UNKNOWN_AGE] = counter[UNKNOWN_AGE]

    for bucket in [UNDERAGE_BUCKET] + [bucketName for bucketName, _, _ in AGE_BUCKETS]:
        if counter.get(bucket):
            ordered[bucket] = counter[bucket]

    return ordered


def _buildPortalDistribution(
    portal: str,
    users: list[user_schema.UserSchema],
    fromDate: int | None,
    toDate: int | None,
    subscriberActive: bool | None,
    hasHypnosisRequest: bool | None,
    hypnosisFromDate: int | None,
    hypnosisToDate: int | None,
) -> user_schema.UserPortalDistributionSchema:
    baseDistribution = _buildGeneralDistribution(
        users=users,
        subscriberActive=subscriberActive,
        hasHypnosisRequest=hasHypnosisRequest,
        fromDate=fromDate,
        toDate=toDate,
        hypnosisFromDate=hypnosisFromDate,
        hypnosisToDate=hypnosisToDate,
    )

    return user_schema.UserPortalDistributionSchema(
        portal=portal,
        totalUsers=baseDistribution.totalUsers,
        genderTotals=baseDistribution.genderTotals,
        languageDistributions=baseDistribution.languageDistributions,
        subscriberActive=subscriberActive,
        hasHypnosisRequest=hasHypnosisRequest,
        fromDate=fromDate,
        toDate=toDate,
        hypnosisFromDate=hypnosisFromDate,
        hypnosisToDate=hypnosisToDate,
    )


def _buildGeneralDistribution(
    users: list[user_schema.UserSchema],
    subscriberActive: bool | None,
    hasHypnosisRequest: bool | None,
    fromDate: int | None,
    toDate: int | None,
    hypnosisFromDate: int | None,
    hypnosisToDate: int | None,
) -> user_schema.UserGeneralDistributionSchema:
    totalUsers = len(users)

    languageStats: dict[str, dict[str, typing.Any]] = {}
    overallGenderCounter: collections.Counter[str] = collections.Counter()

    referenceDate = datetime.datetime.now(datetime.timezone.utc)

    for user in users:
        languageKey = user.language or UNKNOWN_LABEL
        stats = languageStats.setdefault(
            languageKey,
            {
                "total": 0,
                "genderCounter": collections.Counter(),
                "ageCounter": collections.Counter(),
                "genderAgeCounter": collections.defaultdict(collections.Counter),
            },
        )

        stats["total"] += 1

        genderKey = user.gender or UNKNOWN_LABEL
        stats["genderCounter"][genderKey] += 1
        overallGenderCounter[genderKey] += 1

        age = _calculateAge(user.birthdate, referenceDate)
        if age is None or age < 0:
            ageBucket = UNKNOWN_AGE
        else:
            ageBucket = _resolveAgeBucket(age)

        stats["ageCounter"][ageBucket] += 1
        stats["genderAgeCounter"][genderKey][ageBucket] += 1

    languageDistributions: list[user_schema.UserLanguageDistributionSchema] = []

    for languageKey in sorted(languageStats.keys()):
        stats = languageStats[languageKey]
        genderAgeBuckets: dict[str, dict[str, int]] = {
            gender: _buildOrderedAgeDistribution(counter)
            for gender, counter in stats["genderAgeCounter"].items()
        }

        languageDistributions.append(
            user_schema.UserLanguageDistributionSchema(
                language=languageKey,
                totalUsers=stats["total"],
                ageDistribution=_buildOrderedAgeDistribution(stats["ageCounter"]),
                genderDistribution=dict(stats["genderCounter"]),
                genderAgeBuckets=genderAgeBuckets,
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

    effectiveHypnosisFromDate = hypnosisFromDate
    effectiveHypnosisToDate = hypnosisToDate

    # Mantiene compatibilidad con consultas anteriores reutilizando el rango de creación.
    if effectiveHypnosisFromDate is None and hasHypnosisRequest is not None:
        effectiveHypnosisFromDate = fromDate

    if effectiveHypnosisToDate is None and hasHypnosisRequest is not None:
        effectiveHypnosisToDate = toDate

    users = await USERS_REPOSITORY.getUsersByPortal(
        portal=portal,
        fromDate=fromDate,
        toDate=toDate,
        subscriberActive=subscriberActive,
        hasHypnosisRequest=hasHypnosisRequest,
        hypnosisFromDate=effectiveHypnosisFromDate,
        hypnosisToDate=effectiveHypnosisToDate,
    )

    return await anyio.to_thread.run_sync(
        _buildPortalDistribution,
        portal,
        users,
        fromDate,
        toDate,
        subscriberActive,
        hasHypnosisRequest,
        effectiveHypnosisFromDate,
        effectiveHypnosisToDate,
    )




getUsersWithAURACount = typing.cast(
    typing.Callable[
        [bool, int | None, int | None, bool | None], typing.Awaitable[int]
    ],
    _getUsersWithAURACount,
)


getUserByID = typing.cast(
    typing.Callable[
        [str], typing.Awaitable[user_schema.UserSchema | None]
    ],
    _getUserByID,
)


getUsersByListOfIDs = typing.cast(
    typing.Callable[
        [list[str]], typing.Awaitable[list[user_schema.UserSchema]]
    ],
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
    typing.Callable[[], typing.Awaitable[list[int]]],
    _getUserPortals,
)


getGeneralUserDistribution = typing.cast(
    typing.Callable[
        [bool | None, bool | None, int | None, int | None, int | None, int | None],
        typing.Awaitable[user_schema.UserGeneralDistributionSchema],
    ],
    _getGeneralUserDistribution,
)
