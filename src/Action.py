from pydantic import BaseModel

from src.Utils import http_error


class Action(BaseModel):

    name: str
    parameters: dict[str, str]
    result: str

    def __init__(self, name: str = '', parameters: dict = None, result: str = ''):
        super(Action, self).__init__(
            name = name,
            parameters = parameters or {},
            result = result
        )

    def invoke(self, parameters: dict) -> str:
        """
        placeholder for real action, override in subclasses
        """
        if not self.is_parameters_valid(parameters):
            raise http_error(400, f'Invalid action parameters. Needed: {self.parameters}')
        return f'Action executed successfully. Result: {self.result}'

    def is_parameters_valid(self, parameters: dict) -> bool:
        """
        checks if the passed parameters are valid for this action
        """
        for param, api_type in self.parameters.items():
            if param not in parameters:
                return False
            value = parameters[param]
            if type(value) is not Action.convert_type(api_type):
                return False
        return True

    @staticmethod
    def convert_type(api_type: str):
        """
        converts API type to python type for type checking

        todo: return type?
        """
        types = {
            'String': str,
            'Int': int,
            'Map': dict
        }
        if api_type in types: return types[api_type]
        return type(None)