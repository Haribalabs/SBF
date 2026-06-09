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


class SBFReentrancyFault(SBFError):
    pass


# -----------------------------------------------------------------------------
# CONSTANTS (immutable deployment envelope)
# -----------------------------------------------------------------------------

SBF_VERSION = "3.7.2"
SBF_CHAIN_ID = "0xfae00"
SBF_DOMAIN_SALT = bytes.fromhex("7ae394d2b22b3a97f269e7bd527d973ae980a091bd02b23fa58f10ccb9c0b055")
SBF_GOVERNOR = "0x0a79513cec9B5445ccDFcbfC0563e8F9F6b01bFc"
SBF_TREASURY = "0xf84de4884c2307d6dE0DeD6a555eB2324eF53Fea"
SBF_ATTEST_RELAY = "0xdC823243430Ec2fbaa049419f7f17Bee005bdEbF"
SBF_BOND_VAULT = "0x4e2c8F233d7a74Cb0d744939686ff51b7612F81d"
SBF_FINALITY_BEACON = "0x89c909fbf5739c8434E2013e155294a56C7FaA46"
SBF_ROLLUP_ANCHOR = "0x8f3b27b0409d46d94d6486Fee9cb32b15Fc0f6B0"
SBF_SLASH_SINK = "0xaCD2beB4f4e38242C48e5729d131A6d9a1e042f0"
SBF_EMERGENCY_COUNCIL = "0xD991905cF0b4d6a1404788F6636ad88293d8443f"
SBF_ZERO_ADDR = "0x0000000000000000000000000000000000000000"
SBF_BPS_DENOM = 10_000
SBF_MIN_BOND_WEI = 250_000_000_000_000_000
SBF_MAX_BOND_WEI = 9_200_000_000_000_000_000_000
SBF_EPOCH_LENGTH_SEC = 3_600
SBF_FINALITY_LAG_EPOCHS = 2
SBF_MAX_CURATORS = 128
SBF_MAX_WITNESSES_PER_EPOCH = 512
SBF_BLOOM_M_BITS = 2_048
SBF_BLOOM_K_HASHES = 7
SBF_QUORUM_BPS = 6_700
SBF_SLASH_BPS = 1_250
SBF_REWARD_BPS = 340
SBF_VIEW_BATCH = 48
SBF_MAX_BATCH_BYTES = 131_072
SBF_NAMESPACE_TAG = 0x5BF10AD
SBF_GAS_REGISTER_CURATOR = 118_400
SBF_GAS_POST_WITNESS = 92_600
SBF_GAS_VOTE_FINALITY = 74_300
SBF_GAS_CLAIM_REWARD = 61_800
SBF_GAS_SLASH = 88_900
SBF_GAS_PAUSE = 41_200
SBF_GAS_UNPAUSE = 39_700

SBF_ROLE_GOVERNOR = 1 << 0
SBF_ROLE_CURATOR = 1 << 1
SBF_ROLE_ATTESTOR = 1 << 2
SBF_ROLE_FINALIZER = 1 << 3
SBF_ROLE_GUARDIAN = 1 << 4

_EVM_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
_HEX32_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")

