from pydantic import BaseModel
from datetime import datetime
from uuid import uuid4, UUID

from src import ContainerImage, Agent


class Container(BaseModel):

    container_id: UUID
    image: ContainerImage
    agents: list[Agent]
    running_since: datetime

    def __init__(self, image_params):
        super(Container, self).__init__(
            container_id=uuid4(),
            image=ContainerImage(**image_params),
            agents=[],
            running_since=datetime.now()
        )

    def add_agent(self, agent: Agent):
        self.agents.append(agent)
