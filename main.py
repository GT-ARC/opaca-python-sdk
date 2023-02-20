from fastapi import FastAPI

from src import *


# main fastapi app object
app = FastAPI(debug=True, title='Container Agent')


# main (singular) container instance
# image_params = {'image_name': 'abc', 'requires': [], 'provides': []}
container = Container()


@app.get('/agents', response_model=list[Agent])
def get_all_agents() -> list[Agent]:
    """
    Returns a list of all agents and their corresponding actions.
    """
    return container.agents


@app.get('/agents/{agentId}', response_model=Agent)
def get_agent(agentId: str) -> Agent:
    """
    Returns the agent with the passed agentId.
    """
    return container.get_agent(agentId)


@app.post('/send/{agentId}', response_model=str)
def send_message(agentId: str, message: Message) -> str:
    """
    Sends a message to the specified agent.
    """
    return container.send_message(agentId, message)


@app.post('/invoke/{action}', response_model=str)
def invoke_action(action: str, parameters: dict) -> str:
    """
    Invokes the specified action on an agent that knows the action.
    """
    return container.invoke_action(action, parameters)


def main():
    agent1 = Agent(agentId='sampleAgent1', agentType='type1')
    agent1.add_action(Action(name='sampleAction1', parameters={'param1': 'String', 'param2': 'Int'}))
    agent1.add_action(Action(name='sampleAction2', parameters={'param1': 'Map'}))
    agent2 = Agent(agentId='sampleAgent2', agentType='type2')
    agent2.add_action(Action(name='sampleAction2', parameters={'param1': 'Map'}))

    container.add_agent(agent1)
    container.add_agent(agent2)


main()
