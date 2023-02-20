from pydantic import BaseModel

from model import ActionDescription


class AgentDescription(BaseModel):

    agentId: str
    agentType: str
    actions: list[ActionDescription]
