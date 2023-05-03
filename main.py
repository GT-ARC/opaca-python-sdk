import os
from fastapi import FastAPI
from typing import List, Dict, Union, Any

from src import Container, SampleAgent
from Models import Message, AgentDescription, ContainerDescription


def get_environment_variable(name: str):
    if name in os.environ:
        return os.environ.get(name)
    return ''


# main fastapi app object
app = FastAPI(debug=True, title='Container Agent')


# main (singular) container instance
image_params = {'imageName': 'sample-container-python'}
container = Container(container_id=get_environment_variable('CONTAINER_ID'),
                      platform_url=get_environment_variable('PLATFORM_URL'))
container.set_image(**image_params)


@app.get('/info', response_model=ContainerDescription)
def get_container_info() -> ContainerDescription:
    """
    Get a description of the container.
    """
    return container.make_description()


@app.get('/agents', response_model=List[AgentDescription])
def get_all_agents() -> List[AgentDescription]:
    """
    Get a list of all agents and their corresponding actions.
    """
    return container.get_agent_descriptions()


@app.get('/agents/{agentId}', response_model=AgentDescription)
def get_agent(agentId: str) -> AgentDescription:
    """
    Returns the agent with the passed agentId.
    """
    return container.get_agent(agentId).make_description()


@app.post('/send/{agentId}')
def send_message(agentId: str, message: Message):
    """
    Send a message to the specified agent.
    """
    container.send_message(agentId, message)


@app.post('/invoke/{action}', response_model=Union[str, int, float, Dict, List])
def invoke_action(action: str, parameters: Dict[str, Any]):
    """
    Invoke the specified action on any agent that knows the action.
    """
    return container.invoke_action(action, parameters)


@app.post('/invoke/{action}/{agentId}', response_model=Union[str, int, float, Dict, List])
def invoke_agent_action(action: str, agentId: str, parameters: Dict[str, str]):
    """
    Invoke an action on a specific agent.
    """
    return container.invoke_agent_action(action, agentId, parameters)

@app.post('/broadcast/{channel}')
def broadcast(channel: str, message: Message):
    """
    Broadcast a message to all agents that listen on the channel.
    """
    container.broadcast(channel, message)


def main():
    agent1 = SampleAgent(agent_id='sampleAgent1', agent_type='type1')
    container.add_agent(agent1)
    agent1.subscribe_channel('test_channel')

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=container.image.apiPort)


main()
