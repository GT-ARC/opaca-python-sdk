
from src import AbstractAgent


class SampleAgent(AbstractAgent):

    def __init__(self, **kwargs):
        super(SampleAgent, self).__init__(**kwargs)
        self.add_action(
            name='sampleAction1',
            action=self.sampleAction1,
            parameters={'param1': 'String', 'param2': 'Int'},
            result='String'
        )

    def sampleAction1(self, param1: str, param2: int) -> str:
        return f'executed sampleAction1 with params: {param1}, {param2}'

