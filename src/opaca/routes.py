from typing import List, Dict, Any, Annotated
from fastapi import FastAPI
from fastapi.params import Header
from starlette.responses import StreamingResponse

from .container import Container
from .models import Message, AgentDescription, ContainerDescription, StreamDescription, Login


def create_routes(title: str, container: Container) -> FastAPI:
    """
    Create FastAPI instance providing the different REST routes for the OPACA API and 
    calling the respective methods of the given container instance. The application
    still has to be run with `uvicorn.run(app, ...)`.
    """
    app = FastAPI(debug=True, title=title)

    @app.get('/info', response_model=ContainerDescription)
    async def get_container_info() -> ContainerDescription:
        """
        Get a description of the container.
        """
        return container.get_description()


    @app.get('/agents', response_model=List[AgentDescription])
    async def get_all_agents() -> List[AgentDescription]:
        """
        Get a list of all agents and their corresponding actions.
        """
        return container.get_agent_descriptions()


    @app.get('/agents/{agentId}', response_model=AgentDescription)
    async def get_agent(agentId: str) -> AgentDescription:
        """
        Returns the agent with the passed agentId.
        """
        return container.get_agent(agentId).make_description()


    @app.post('/send/{agentId}')
    async def send_message(agentId: str, message: Message):
        """
        Send a message to the specified agent.
        """
        container.send_message(agentId, message)


    @app.post('/broadcast/{channel}')
    async def broadcast(channel: str, message: Message):
        """
        Broadcast a message to all agents that listen on the channel.
        """
        container.broadcast(channel, message)


    @app.post('/invoke/{action}', response_model=Any)
    async def invoke_action(action: str, parameters: Dict[str, Any], ContainerLoginToken: Annotated[str | None, Header()] = None):
        """
        Invoke the specified action on any agent that knows the action.
        """
        return await container.invoke_action(action, parameters, ContainerLoginToken)


    @app.post('/invoke/{action}/{agentId}', response_model=Any)
    async def invoke_agent_action(action: str, agentId: str, parameters: Dict[str, Any], ContainerLoginToken: Annotated[str | None, Header()] = None):
        """
        Invoke an action on a specific agent.
        """
        return await container.invoke_agent_action(action, agentId, parameters, ContainerLoginToken)


    @app.get('/stream/{stream}', response_class=StreamingResponse)
    async def get_stream(stream: str, ContainerLoginToken: Annotated[str | None, Header()] = None):
        """
        GET a stream from any agent.
        """
        return make_stream_response(stream, StreamDescription.Mode.GET, ContainerLoginToken)


    @app.get('/stream/{stream}/{agentId}', response_class=StreamingResponse)
    async def get_agent_stream(stream: str, agent_id: str, ContainerLoginToken: Annotated[str | None, Header()] = None):
        """
        GET a stream from the specified agent.
        """
        return make_stream_response(stream, StreamDescription.Mode.GET, agent_id, ContainerLoginToken)

    @app.post('/login')
    async def login(login: Login):
        """
        Provide login credentials required for actions requiring authentication.
        """
        return await container.login(login)

    @app.post('/logout')
    async def logout(ContainerLoginToken: Annotated[str | None, Header()] = None):
        """
        Performs a logout operation.
        """
        return await container.logout(ContainerLoginToken)


    def make_stream_response(name: str, mode: StreamDescription.Mode, agent_id: str = None, login_token: str = None) -> StreamingResponse:
        """
        Converts the byte stream from the stream invocation into the correct response format.
        """
        result = container.invoke_stream(name, mode, login_token) if agent_id is None \
            else container.invoke_agent_stream(name, mode, agent_id, login_token)
        return StreamingResponse(result, media_type='application/octet-stream')

    return app
