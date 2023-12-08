import os, json
from typing import List, Dict, Any
from fastapi import FastAPI
from starlette.responses import StreamingResponse

from src import Container, SampleAgent
from Models import Message, AgentDescription, ContainerDescription, ImageDescription, StreamDescription
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


@app.get('/stream/{stream}', response_class=StreamingResponse)
async def get_stream(stream: str):
    """
    GET a stream from any agent.
    """
    return make_stream_response(stream, StreamDescription.Mode.GET)


@app.get('/stream/{stream}/{agentId}', response_class=StreamingResponse)
def get_agent_stream(stream: str, agent_id: str):
    """
    GET a stream from the specified agent.
    """
    return make_stream_response(stream, StreamDescription.Mode.GET, agent_id)


def make_stream_response(name: str, mode: StreamDescription.Mode, agent_id: str = None) -> StreamingResponse:
    """
    Converts the byte stream from the stream invocation into the correct response format.
    """
    result = container.invoke_stream(name, mode) if agent_id is None else container.invoke_agent_stream(name, mode, agent_id)
    return StreamingResponse(result, media_type='application/octet-stream')


def main():
    agent1 = SampleAgent(agent_id='sampleAgent1', agent_type='type1')
    container.add_agent(agent1)
    agent1.subscribe_channel('test_channel')

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=container.image.apiPort)


main()
