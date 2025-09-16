from abc import ABC


class ComponentBase(ABC):
    def __init__(self, name):
        self.name = name
