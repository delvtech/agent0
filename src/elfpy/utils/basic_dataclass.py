from dataclasses import dataclass
from elfpy.utils.float_to_string import float_to_string   # float→str formatter, also imports numpy as np

@dataclass
class BasicDataclass():
    """A basic dataclass with a few useful methods"""

    def __getitem__(self, key):
        getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def str(self):
        output_string = ""
        for key, value in vars(self).items():
            if value: #  check if object exists
                if value != 0:
                    output_string+=f" {key}: "
                    if isinstance(value, float):
                        output_string+=f"{float_to_string(value)}"
                    elif isinstance(value, list):
                        output_string+='['+', '.join([float_to_string(x) for x in value])+']'
                    elif isinstance(value, dict):
                        output_string+='{'+', '.join([f"{k}: {float_to_string(v)}" for k,v in value.items()])+'}'
                    else:
                        output_string+=f"{value}"
        return output_string

    def update(self, *args, **kwargs):
        return self.__dict__.update(*args, **kwargs)

    def dict(self):
        return self.__dict__

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()
