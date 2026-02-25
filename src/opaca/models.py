from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from enum import Enum


class Message(BaseModel):
    payload: Any
    replyTo: str = ''


class Parameter(BaseModel):

    class ArrayItems(BaseModel):
        type: str
        items: Optional['Parameter.ArrayItems'] = None

    @staticmethod
    def list_of(type: str, required: bool = True) -> 'Parameter':
        """
        Utility function for making a shallow array parameter.
        """
        return Parameter(type='array', required=required, items=Parameter.ArrayItems(type=type))

    type: str
    required: bool = True
    items: Optional[ArrayItems] = None


class ActionDescription(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Parameter]
    result: Optional[Parameter] = None
    callback: Optional[Any] = Field(default=None, exclude=True)


class StreamDescription(BaseModel):

    class Mode(Enum):
        GET = 'GET'
        POST = 'POST'

    name: str
    description: Optional[str] = None
    mode: Mode = Mode.GET
    callback: Optional[Any] = Field(default=None, exclude=True)


class ImageParameter(BaseModel):
    name: str
    type: str
    required: bool = False
    confidential: bool = False
    defaultValue: Optional[Any] = None


class AgentDescription(BaseModel):
    agentId: str
    agentType: str
    description: Optional[str] = None
    actions: List[ActionDescription] = []
    streams: List[StreamDescription] = []


class ImageDescription(BaseModel):

    class PortDescription(BaseModel):
        protocol: str
        description: str = ''

    imageName: str
    requires: List[str] = []
    provides: List[str] = []
    url: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    provider: Optional[str] = None
    apiPort: int = 8082
    extraPorts: Dict[int, PortDescription] = {}
    parameters: List[ImageParameter] = []
    definitions: Dict[str, Any] = {}
    definitionsByUrl: Dict[str, str] = {}


class ContainerDescription(BaseModel):
    containerId: str
    image: ImageDescription
    arguments: Dict[str, Any] = {}
    agents: List[AgentDescription] = []
    owner: str = ''
    runningSince: str
    connectivity: Optional[Any] = None


class Login(BaseModel):
    username: str
    password: str


class LoginMsg(BaseModel):
    token: str
    login: Login


class PlatformInfo(BaseModel):
    platformId: str
    baseUrl: str
    containers: List[ContainerDescription] = []
    provides: List[str] = []
    connections: List[str] = []
    runningSince: str


class PostContainer(BaseModel):
    image: ImageDescription
    arguments: Dict[str, Any] = {}
    pull: Optional[bool] = None
    clientConfig: Optional[Dict[str, Any]] = None


class ConnectionRequest(BaseModel):
    url: str
    connectBack: bool = False
    token: str | None = None


class Event(BaseModel):

    class EventType(Enum):
        CALL = "CALL"
        FORWARD = "FORWARD"
        SUCCESS = "SUCCESS"
        ERROR = "ERROR"

    id: str
    timestamp: int
    eventType: EventType
    route: Optional[str] = None
    senderId: Optional[str] = None
    receiver: Optional[str] = None
    statusCode: Optional[int] = None
    relatedId: Optional[str] = None
