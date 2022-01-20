from pydantic import BaseModel
from typing import List


class BlockTransaction(BaseModel):
    hash: str
    type: str


class Block(BaseModel):
    hash: str
    height: int
    prev_hash: str
    time: int
    transactions: List[BlockTransaction]
