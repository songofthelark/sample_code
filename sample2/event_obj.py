from __future__ import annotations
from datetime import datetime
from collections import namedtuple

Observation = namedtuple('Observation', 'value obsdate')


class Event:

    def __init__(self, event_datetime: datetime, attributes: dict = None):
        self._datetime = event_datetime
        self._attributes = {}

        # store observed date along with name and value
        if attributes:
            for name, value in attributes.items():
                self._attributes[name] = Observation(value, event_datetime)

    def set_attributes_from_event(self, event: Event):
        # only add attributes, don't update value for any that are already there
        for attribute, value in event.get_attributes().items():
            if attribute not in self._attributes:
                self._attributes[attribute] = value

    def get_attributes(self):
        return self._attributes

    def get_attribute_observation(self, name: str):
        # returns Observation named tuple
        return self._attributes.get(name, None)

    def get_datetime(self) -> datetime:
        return self._datetime

    def __str__(self):
        return self._datetime.isoformat()
