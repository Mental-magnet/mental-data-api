import fastapi
import fastapi.security
import sentry_sdk

from .config import ENVIRONMENT_CONFIG
from .modules import ALL_MODULE_ROUTERS

sentry_sdk.init(
    dsn=ENVIRONMENT_CONFIG.SENTRY_CONFIG.SENTRY_DSN,
    send_default_pii=True,
    traces_sample_rate=ENVIRONMENT_CONFIG.SENTRY_CONFIG.SENTRY_SAMPLE_RATE,
    environment=ENVIRONMENT_CONFIG.SENTRY_CONFIG.SENTRY_ENVIRONMENT,
    release=ENVIRONMENT_CONFIG.SENTRY_CONFIG.SENTRY_RELEASE,
    enable_logs=ENVIRONMENT_CONFIG.SENTRY_CONFIG.SENTRY_ENABLE_LOGS
)

apiKeySchema = fastapi.security.APIKeyHeader(
    name="x-api-key",
    auto_error=True,
    scheme_name="Encabezado de API Key",
    description="API Key necesaria para acceder a los endpoints"
)

async def verifyApiKey(apiKey: str = fastapi.Depends(apiKeySchema)) -> str:
    if apiKey != ENVIRONMENT_CONFIG.SECURITY_CONFIG.SECURITY_API_KEY:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida"
        )
    
    return apiKey

APP = fastapi.FastAPI(
    title="MENTAL DATA API" + " - " + ENVIRONMENT_CONFIG.SENTRY_CONFIG.SENTRY_ENVIRONMENT,
    version=ENVIRONMENT_CONFIG.SENTRY_CONFIG.SENTRY_RELEASE,
    description="Aplicación FastAPI para el procesamiento de datos de Mental",
    dependencies=[fastapi.Depends(verifyApiKey)],
)

for router in ALL_MODULE_ROUTERS:
    APP.include_router(router)