from pydantic import BaseModel, Field, PrivateAttr, field_validator
from typing import Dict, List, Any, Optional, Callable
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
    description: str
    parameters: Dict[str, Parameter]
    result: Parameter
    callback: Any = Field(exclude=True)


class StreamDescription(BaseModel):

    class Mode(Enum):
        GET = 'GET'
        POST = 'POST'

    name: str
    description: str = ''
    mode: Mode = Mode.GET
    callback: Any = Field(exclude=True)


class ImageParameter(BaseModel):
    name: str
    type: str
    required: bool = False
    confidential: bool = False
    defaultValue: Optional[str] = None


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
    name: str = ''
    description: str = ''
    version: str = ''
    provider: str = ''
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
    connectivity: None = None


class Login(BaseModel):
    username: str
    password: str


class LoginMsg(BaseModel):
    token: str
    login: 'Login'
