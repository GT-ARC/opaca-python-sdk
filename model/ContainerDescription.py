from pydantic import BaseModel
from datetime import datetime

from model import AgentDescription


class ContainerDescription(BaseModel):

    containerId: str
    # image: ImageDescription
    agents: list[AgentDescription]
    runningSince: datetime
