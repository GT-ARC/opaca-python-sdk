from pydantic import BaseModel
from datetime import datetime

from model import AgentDescription, ImageDescription


class ContainerDescription(BaseModel):

    containerId: str
    image: ImageDescription
    agents: list[AgentDescription]
    runningSince: list[int]
