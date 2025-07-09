import opaca
from opaca import Container
from sample import SampleAgent


# assemble Agent Container
container = Container("resources/container.json")
agent1 = SampleAgent(agent_id='sampleAgent1')
container.add_agent(agent1)
agent1.subscribe_channel('test_channel')


if __name__ == "__main__":
    opaca.run('sample-container', container)
