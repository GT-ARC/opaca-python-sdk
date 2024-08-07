from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from enum import Enum


class Message(BaseModel):
    payload: Any
    replyTo: str = ''


class Parameter(BaseModel):
    type: str
    required: bool = True


class ActionDescription(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Parameter]
    result: Parameter


class StreamDescription(BaseModel):
    class Mode(Enum):
        GET = 'GET'
        POST = 'POST'
    name: str
    description: str
    mode: Mode


class ImageParameter(BaseModel):
    name: str
    type: str
    required: bool = False
    confidential: bool = False
    defaultValue: Optional[str] = None


class AgentDescription(BaseModel):
    agentId: str
    agentType: str
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
