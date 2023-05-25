from pydantic import BaseModel
from typing import Dict, List, Union


class Message(BaseModel):

    payload: Union[Dict, List, str, int, float]
    replyTo: str


class ActionDescription(BaseModel):

    name: str
    parameters: Dict[str, str]
    result: str


class AgentDescription(BaseModel):

    agentId: str
    agentType: str
    actions: List[ActionDescription]


class ImageDescription(BaseModel):

    imageName: str
    requires: List[str] = []
    provides: List[str] = []
    name: str = ''
    description: str = ''
    provider: str = ''
    apiPort: int = 8082
    extraPorts: dict = {}


class ContainerDescription(BaseModel):

    containerId: str
    image: ImageDescription
    agents: List[AgentDescription]
    runningSince: str
    connectivity: None
