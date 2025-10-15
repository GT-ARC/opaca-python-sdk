from opaca import Container, run
from sample import SampleAgent


# Assemble Agent Container
container = Container('resources/container.json')
agent1 = SampleAgent(container=container, agent_id='sampleAgent1')
agent1.subscribe_channel('test_channel')


if __name__ == '__main__':
    run(container)
