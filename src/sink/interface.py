#!/usr/bin/env python3

from abc import abstractmethod, abstractproperty, ABC
from multiprocessing import Queue

from src.types_ import NTriplesResult


class Sink(ABC):
    """Get parsing results from a queue and store them
    accordingly.
    """

    in_queue: "Queue[NTriplesResult]"

    @abstractmethod
    def __init__(self, in_queue: "Queue[NTriplesResult]") -> None: ...

    @abstractmethod
    def run(self) -> None: ...
