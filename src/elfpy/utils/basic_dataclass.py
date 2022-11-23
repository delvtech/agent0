from dataclasses import dataclass
from dataclasses import field

@dataclass
class BasicDataclass:
    """A basic dataclass with a few useful methods"""

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def display(self):
        output_string = ""
        for key, value in vars(self).items():
            if value:
                output_string+=f" {key}: {value}"
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
