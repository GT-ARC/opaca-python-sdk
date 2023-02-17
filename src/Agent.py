from pydantic import BaseModel


class Agent(BaseModel):

    agent_id: str
    agent_type: str
    actions: list = []

    def __init__(self, agent_id: str, agent_type: str):
        super(Agent, self).__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            actions=[]
        )
