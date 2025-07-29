from typing import List, Dict, Any
from fastapi import FastAPI
from starlette.responses import StreamingResponse

from .container import Container
from .models import Message, AgentDescription, ContainerDescription, StreamDescription


def create_routes(title: str, container: Container) -> FastAPI:
    """
    Create FastAPI instance providing the different REST routes for the OPACA API and 
    calling the respective methods of the given container instance. The application
    still has to be run with `uvicorn.run(app, ...)`.
    """
    app = FastAPI(debug=True, title=title)

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
    async def invoke_action(action: str, parameters: Dict[str, Any]):
        """
        Invoke the specified action on any agent that knows the action.
        """
        return await container.invoke_action(action, parameters)


    @app.post('/invoke/{action}/{agentId}', response_model=Any)
    async def invoke_agent_action(action: str, agentId: str, parameters: Dict[str, Any]):
        """
        Invoke an action on a specific agent.
        """
        return await container.invoke_agent_action(action, agentId, parameters)


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
        result = container.invoke_stream(name, mode) if agent_id is None \
            else container.invoke_agent_stream(name, mode, agent_id)
        return StreamingResponse(result, media_type='application/octet-stream')

    return app
