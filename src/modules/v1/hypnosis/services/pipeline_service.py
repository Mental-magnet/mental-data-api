import httpx
from fastapi import HTTPException, status
from src.config.environment import EnvironmentConfig
from src.modules.v1.hypnosis.schemas.pipeline_schema import (
    LoggingEventsResponse,
    RemainingTasksResponse,
)


class PipelineService:
    def __init__(self, settings: EnvironmentConfig):
        self.settings = settings
        self.base_url = self.settings.HYPNOSIS_CONFIG.HYPNOSIS_API_URL
        self.api_key = self.settings.HYPNOSIS_CONFIG.HYPNOSIS_API_KEY
        self.headers = {"x-api-key": self.api_key}

    async def getLoggingEvents(
        self, fromDate: int, toDate: int, eventType: str | None = None
    ) -> LoggingEventsResponse:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/v1/logging/events",
                    params={
                        "fromDate": fromDate,
                        "toDate": toDate,
                        "eventType": eventType,
                    },
                    headers=self.headers,
                )
                response.raise_for_status()
                return LoggingEventsResponse(**response.json())
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error fetching logging events: {e.response.text}",
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal server error: {str(e)}",
                )

    async def getRemainingTasks(self, artifact: str) -> RemainingTasksResponse:
        # Artifact should be one of: maker, export, decorator, caronte, moderator, logging
        valid_artifacts = [
            "maker",
            "export",
            "decorator",
            "caronte",
            "moderator",
            "logging",
        ]
        if artifact.lower() not in valid_artifacts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact. Must be one of: {', '.join(valid_artifacts)}",
            )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/v1/{artifact.lower()}/tasks/count-remaining",
                    headers=self.headers,
                )
                response.raise_for_status()
                return RemainingTasksResponse(**response.json())
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error fetching remaining tasks for {artifact}: {e.response.text}",
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal server error: {str(e)}",
                )
