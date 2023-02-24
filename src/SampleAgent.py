
from src import AbstractAgent
from Models import Message


class SampleAgent(AbstractAgent):

    def __init__(self, **kwargs):
        super(SampleAgent, self).__init__(**kwargs)
        self.add_action(
            name='sampleAction1',
            action=self.sample_action_1,
            parameters={'param1': 'String', 'param2': 'Int'},
            result='String'
        )

    def sample_action_1(self, param1: str, param2: int) -> str:
        print(f'{self.agent_id} executed sampleAction1 with params: {param1}, {param2}')

    def receive_message(self, message: Message):
        super().receive_message(message)
        print(f'{self.agent_id} received message: {message}')

