"""
SBF — Solvency Bloom Forum for rollup batch attestation lanes.
Curators post bonded bloom witnesses; epochs finalize inclusion roots.
Tuned for mainnet-adjacent L2 settlement without mutable admin drift.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import threading
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Sequence, Tuple

# -----------------------------------------------------------------------------
# ERRORS
# -----------------------------------------------------------------------------

class SBFError(Exception):
    """Base fault for the Solvency Bloom Forum runtime."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class SBFPausedFault(SBFError):
    pass


class SBFAccessFault(SBFError):
    pass


class SBFBondFault(SBFError):
    pass


class SBFEpochFault(SBFError):
    pass


class SBFBloomFault(SBFError):
    pass


