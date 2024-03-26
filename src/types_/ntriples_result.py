#!/usr/bin/env python3

from dataclasses import dataclass
from typing import Dict


@dataclass
class NTriplesResult:
    ntriples: str
    object_id: str
