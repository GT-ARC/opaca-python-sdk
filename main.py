import os, json
from fastapi import FastAPI
from typing import List, Dict, Union, Any

from starlette.responses import StreamingResponse

from src import Container, SampleAgent
from Models import Message, AgentDescription, ContainerDescription, ImageDescription
from src.Utils import http_error


def get_environment_variable(name: str):
    if name in os.environ:
        return os.environ.get(name)
    return ''


def load_image_params():
    with open('resources/container.json', encoding='utf-8') as f:
        return json.load(f)


def load_image():
    try:
        return ImageDescription(**load_image_params())
    except TypeError:
        return http_error(500, 'Failed to load image description.')


def init_container():
    container_id = get_environment_variable('CONTAINER_ID')
    platform_url = get_environment_variable('PLATFORM_URL')
    ctr = Container(container_id, platform_url, load_image())
    return ctr


# main fastapi app object
app = FastAPI(debug=True, title='Sample Container Python')


# main (singular) container instance
container = init_container()


@app.get('/info', response_model=ContainerDescription)
def get_container_info() -> ContainerDescription:
    """
    Get a description of the container.
    """
    return container.get_description()


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


@app.post('/broadcast/{channel}')
def broadcast(channel: str, message: Message):
    """
    Broadcast a message to all agents that listen on the channel.
    """
    container.broadcast(channel, message)


@app.post('/invoke/{action}', response_model=Any)
def invoke_action(action: str, parameters: Dict[str, Any]):
    """
    Invoke the specified action on any agent that knows the action.
    """
    return container.invoke_action(action, parameters)


@app.post('/invoke/{action}/{agentId}', response_model=Any)
def invoke_agent_action(action: str, agentId: str, parameters: Dict[str, Any]):
    """
    Invoke an action on a specific agent.
    """
    return container.invoke_agent_action(action, agentId, parameters)


@app.get('/stream/{streamId}', response_model=StreamingResponse)
def get_stream(streamId: str):
    """
    TODO: GET a stream from this container.
    """
    return None


@app.post('/stream/{streamId}', response_model=Any)
def post_stream(streamId: str):
    """
    TODO: POST a stream to this container.
        see e.g. https://stackoverflow.com/questions/71867214/how-can-i-post-data-in-real-time-using-fastapi
    """
    return None


def main():
    agent1 = SampleAgent(agent_id='sampleAgent1', agent_type='type1')
    container.add_agent(agent1)
    agent1.subscribe_channel('test_channel')

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=container.image.apiPort)


main()
