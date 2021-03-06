from pydantic import BaseModel
from typing import List, Optional


class Witness(BaseModel):
    channel: int
    datarate: str
    frequency: float
    gateway: str
    is_valid: Optional[bool]
    packet_hash: str
    signal: int
    snr: float
    timestamp: int


class Receipt(BaseModel):
    channel: int
    data: str
    datarate: Optional[str]
    frequency: float
    gateway: str
    origin: str
    signal: int
    snr: float
    timestamp: int
    tx_power: int


class PathElement(BaseModel):
    challengee: str
    receipt: Optional[Receipt]
    witnesses: List[Witness]


class PocReceiptsV1(BaseModel):
    hash: str
    challenger: str
    fee: int
    onion_key_hash: str
    path: List[PathElement]
    request_block_hash: str
    secret: str