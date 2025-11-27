import pydantic
from typing import List, Optional, Dict, Any

class LoggingSchema(pydantic.BaseModel):
    id: Optional[str] = pydantic.Field(None, description="The unique identifier for the logging entry")
    receivedArtifact: str = pydantic.Field(..., description="The artifact that received the logged event")
    timestamp: int = pydantic.Field(..., description="Unix timestamp of the logged event")
    eventType: str = pydantic.Field(..., description="Type of the logged event")
    eventMessage: str = pydantic.Field(..., description="Detailed message about the logged event")
    userEmail: Optional[str] = pydantic.Field(None, description="Email associated with the task/event, when available")
    userLanguage: Optional[str] = pydantic.Field(None, description="Language associated with the task/event, when available")
    userLevel: Optional[int] = pydantic.Field(None, description="User level associated with the task/event, when available", ge=0)
    queueRoutingKey: Optional[str] = pydantic.Field(None, description="The routing key of the queue from which the log was received")
    additionalInfo: Optional[Dict[str, Any]] = pydantic.Field(None, description="Additional information related to the logged event")
    audioRequestID: str = pydantic.Field(..., description="The ID of the audio request associated with the logged event")

class LoggingEventsResponse(pydantic.BaseModel):
    items: List[LoggingSchema] = pydantic.Field(..., description="Collection of logging events matching the provided filters")

class QueueCount(pydantic.BaseModel):
    queueName: str = pydantic.Field(..., description="Queue friendly name used internally.")
    rabbitQueue: str = pydantic.Field(..., description="Exact RabbitMQ queue name.")
    messages: int = pydantic.Field(0, description="Total messages in queue (ready + unacknowledged).", ge=0)
    messagesReady: int = pydantic.Field(0, description="Messages ready to be delivered.", ge=0)
    messagesUnacknowledged: int = pydantic.Field(0, description="Messages delivered but not yet acknowledged.", ge=0)

class RemainingTasksResponse(pydantic.BaseModel):
    artifact: str = pydantic.Field(..., description="Artifact identifier (MAKER, EXPORT, DECORATOR, ...).")
    total: int = pydantic.Field(0, description="Total pending tasks across queues.", ge=0)
    queues: Dict[str, QueueCount] = pydantic.Field(..., description="Breakdown per logical queue key.")
