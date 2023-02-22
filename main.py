from fastapi import FastAPI

from model import *
from src import *

import os

# main fastapi app object
app = FastAPI(debug=True, title='Container Agent')


# main (singular) container instance
image_params = {'imageName': 'container-agent-py', 'requires': [], 'provides': []}
container = Container(container_id=os.environ.get("CONTAINER_ID"))
container.set_image(**image_params)


@app.get('/info', response_model=ContainerDescription)
def get_container_info() -> ContainerDescription:
    return container.make_description()


@app.get('/agents', response_model=list[AgentDescription])
def get_all_agents() -> list[AgentDescription]:
    """
    Returns a list of all agents and their corresponding actions.
    """
    return container.get_agent_descriptions()


@app.get('/agents/{agentId}', response_model=AgentDescription)
def get_agent(agentId: str) -> AgentDescription:
    """
    Returns the agent with the passed agentId.
    """
    return container.get_agent(agentId).make_description()


@app.post('/send/{agentId}', response_model=str)
def send_message(agentId: str, message: Message) -> str:
    """
    Sends a message to the specified agent.
    """
    return container.send_message(agentId, message)


@app.post('/invoke/{action}', response_model=str)
def invoke_action(action: str, parameters: dict[str, str]) -> str:
    """
    Invokes the specified action on an agent that knows the action.
    """
    return container.invoke_action(action, parameters)

@app.post('/invoke/{action}/{agentId}', response_model=str)
def invoke_agent_action(action: str, agentId: str, parameters: dict[str, str]) -> str:
    """
    Invokes an action on a specific agent.
    """
    return container.invoke_action(action, parameters, agentId)


def main():
    action1 = Action(name='sampleAction1', parameters={'param1': 'String', 'param2': 'Int'}, result='Int')
    action2 = Action(name='sampleAction2', parameters={'param1': 'Map'}, result='String')
    agent1 = Agent(agent_id='sampleAgent1', agent_type='type1')
    agent1.add_action(action1)
    agent1.add_action(action2)
    agent2 = Agent(agent_id='sampleAgent2', agent_type='type2')
    agent2.add_action(action2)

    container.add_agent(agent1)
    container.add_agent(agent2)


main()
