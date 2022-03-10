from pydantic import BaseModel


class AddGatewayV1(BaseModel):
    hash: str
    gateway: str
    owner: str
    payer: str
    staking_fee: int
