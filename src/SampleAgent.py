
from src import AbstractAgent
from Models import Message


class SampleAgent(AbstractAgent):
    """
    Sample Agent class that inherits from AbstractAgent.
    Prints some information when receiving messages or executing actions.
    """

    def __init__(self, **kwargs):
        super(SampleAgent, self).__init__(**kwargs)
        self.add_action(
            name='sampleAction1',
            action=self.sample_action_1,
            parameters={'param1': 'String', 'param2': 'Int'},
            result='String'
        )
        self.add_action(
            name='add',
            action=self.add,
            parameters={'x': 'Int', 'y': 'Int'},
            result='Int'
        )
        self.add_action(
            name='timeConsumingAction',
            action=self.time_consuming_action,
            parameters={'text': 'String', 'time_offset': 'Int'},
            result='String'
        )

    def sample_action_1(self, param1: str, param2: int) -> str:
        return f'{self.agent_id} executed sampleAction1 with params: {param1}, {param2}'

    def add(self, x: int, y: int) -> int:
        print(f'{self.agent_id} executed add with params: {x}, {y}')
        try:
            return int(x) + int(y)
        except ValueError:
            return 0

    def time_consuming_action(self, text: str, time_offset: str = 0) -> str:
        time_offset = int(time_offset)
        print(f'{self.agent_id} executing time_consuming action, taking approx {60 + time_offset} seconds')
        from time import sleep
        sleep(60 + time_offset)
        return f'{text}, {time_offset}'

    def receive_message(self, message: Message):
        super().receive_message(message)
        print(f'{self.agent_id} received message: {message}')

