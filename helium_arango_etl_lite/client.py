import requests
from requests import Response
from settings import Settings
from typing import Optional, Dict, Union
from random import randrange
from models.block import Block
from models.transactions.payment_v1 import PaymentV1
from models.transactions.payment_v2 import PaymentV2
from models.transactions.poc_receipts_v1 import PocReceiptsV1
from models.transactions.poc_receipts_v2 import PocReceiptsV2


class BlockchainNodeClient(object):
    def __init__(self, settings: Settings):
        self._node_address = settings.node_address

    @property
    def node_address(self):
        return self._node_address

    @property
    def height(self):
        return BaseRPCCall(self.node_address, "block_height", None, None).call()

    def block_get(self, height: Optional[int], hash: Optional[str]) -> Optional[Block]:
        if height:
            params = {"height": height}
        elif hash:
            params = {"hash": hash}
        else:
            raise Exception("You must provide either a height (int) or hash (str) argument to block_get method")
        block_raw = BaseRPCCall(self.node_address, "block_get", params, request_id=None).call()
        if not block_raw:
            return None
        else:
            return Block.parse_obj(block_raw)


    def transaction_get(self, hash: str, type: str) -> Union[PaymentV1, PaymentV2, PocReceiptsV1, None]:
        params = {"hash": hash}
        response = BaseRPCCall(self.node_address, "transaction_get", params, request_id=None).call()
        if type == "payment_v1":
            return PaymentV1.parse_obj(response)
        elif type == "payment_v2":
            return PaymentV2.parse_obj(response)
        elif type == "poc_receipts_v1":
            return PocReceiptsV1.parse_obj(response)
        elif type == "poc_receipts_v2":
            return PocReceiptsV2.parse_obj(response)
        else:
            raise Exception(f"Unexpected transaction type: {type}")



class BaseRPCCall(object):
    def __init__(self, node_address: str,
                 method: str, params: Optional[Dict],
                 request_id: Optional[str],
                 jsonrpc: Optional[str] = "2.0"):
        self.node_address = node_address
        self.method = method
        self.params = params
        self.id = request_id if request_id else randrange(0, 99999)
        self.jsonrpc = jsonrpc

    def call(self):
        payload = {
            "method": self.method,
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        if self.params:
            payload["params"] = self.params
        response = requests.post(self.node_address, json=payload).json()
        try:
            return response["result"]
        except KeyError:
            error = response["error"]
            if error["code"] == -100:
                return None
            else:
                raise Exception(f"Request {self.method} with params {self.params} failed with error: {error}")




