from pydantic import BaseModel


class Message(BaseModel):

    payload: dict
    replyTo: str


class ActionDescription(BaseModel):

    name: str
    parameters: dict[str, str]
    result: str


class AgentDescription(BaseModel):

    agentId: str
    agentType: str
    actions: list[ActionDescription]


class ImageDescription(BaseModel):

    imageName: str
    requires: list[str]
    provides: list[str]
    name: str = ''
    description: str = ''
    provider: str = ''


class ContainerDescription(BaseModel):

    containerId: str
    image: ImageDescription
    agents: list[AgentDescription]
    runningSince: list[int]
