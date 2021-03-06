from models.block import *
from models.transactions.poc_receipts_v1 import *
from models.transactions.poc_receipts_v2 import *
from models.transactions.payment_v2 import *
from models.transactions.payment_v1 import *
from client import BlockchainNodeClient
from loaders import process_gateway_inventory
from pyArango.connection import Connection
from pyArango.database import Database
from pyArango.collection import Collection, Edges
from pyArango.document import Document
from settings import Settings
from pyArango.theExceptions import CreationError, DocumentNotFoundError, UpdateError
import time
import hashlib
import json
from typing import Union
from pydantic.error_wrappers import ValidationError


class Follower(object):
    def __init__(self):
        self.settings = Settings()

        self.client = BlockchainNodeClient(self.settings)

        self.connection = Connection(
            self.settings.arango_address,
            self.settings.arango_username,
            self.settings.arango_password
        )
        self.database: Optional[Database] = None
        self.poc_receipts: Optional[Edges] = None
        self.payments: Optional[Edges] = None
        self.hotspots: Optional[Collection] = None
        self.accounts: Optional[Collection] = None
        self.follower_info: Optional[Collection] = None

        self.height = self.client.height
        self.first_block: Optional[int] = None
        self.sync_height: Optional[int] = None
        self.inventory_height: Optional[int] = None

    def run(self):
        self.init_database()
        self.get_first_block()
        self.update_follower_info()

        if self.settings.gateway_inventory_bootstrap:
            self.update_gateway_inventory()
            print("Gateway inventory imported successfully")

        print(f"Blockchain follower starting from block {self.sync_height} / {self.height}")

        while True:
            t = time.time()

            retry = 0
            while retry < 50:
                try:
                    if self.sync_height - self.inventory_height > 500:
                        self.update_gateway_inventory()
                    self.process_block(self.sync_height)
                    # self.delete_old_receipts() # deletions not optimized yet
                    break
                except (ValidationError, AttributeError):
                    print("couldn't find transaction...retrying")
                    time.sleep(10)
                    retry += 1
            self.sync_height += 1

            print(f"Block {self.sync_height - 1} synced in {time.time() - t} seconds...")
            self.update_follower_info()
            if self.sync_height >= self.height:
                time.sleep(10)

    def init_database(self):
        if self.connection.hasDatabase(self.settings.arango_database) is False:
            self.connection.createDatabase(self.settings.arango_database)
        self.database: Database = self.connection.databases[self.settings.arango_database]
        for e in ["poc_receipts", "payments"]:
            try:
                self.database.createCollection(className="Edges", name=e)
            except CreationError:
                pass
        for c in ["hotspots", "accounts", "follower_info"]:
            try:
                self.database.createCollection(className="Collection", name=c)
            except CreationError:
                pass
        self.poc_receipts = self.database["poc_receipts"]
        self.payments = self.database["payments"]
        self.hotspots = self.database["hotspots"]
        self.accounts = self.database["accounts"]
        self.follower_info = self.database["follower_info"]

    def get_first_block(self):
        print("Getting first block...")
        try:
            follower_info = self.follower_info.fetchDocument("follower_info")
            self.first_block = follower_info["first_block"]
            self.sync_height = follower_info["sync_height"]
            print(f"first_block height found from database: {self.first_block}")
        except DocumentNotFoundError:
            h = self.height
            while True:
                if h < (self.height - self.settings.block_inventory_size) or self.client.block_get(h, None) is None:
                    self.first_block = h + 1
                    print(f"first_block height found!: {self.first_block}")
                    break
                else:
                    h -= 1
                    if h % 100 == 0:
                        print(f"...still finding blocks, at {h} / {self.height}")

    def update_follower_info(self):
        if not self.first_block:
            self.get_first_block()
        if not self.sync_height:
            self.sync_height = self.first_block
        follower_info = {
            "_key": "follower_info",
            "height": self.height,
            "first_block": self.first_block,
            "sync_height": self.sync_height,
            "inventory_height": self.inventory_height
        }
        self.follower_info.createDocument(follower_info).save(overwriteMode="replace")

    def update_gateway_inventory(self):
        gateway_inventory, inventory_height = process_gateway_inventory(self.settings)
        self.hotspots.importBulk(gateway_inventory)
        self.inventory_height = inventory_height

    def process_block(self, height: int):
        block = self.client.block_get(height, None)
        payment_documents = []
        receipt_documents = []
        account_documents = []
        # hotspot_documents = []
        _t = time.time()

        for txn in block.transactions:

            if txn.type == "payment_v1":
                transaction: PaymentV1 = self.client.transaction_get(txn.hash, txn.type)
                account_documents.append({"_key": transaction.payer})
                payment_document = {
                    "_from": "accounts/" + transaction.payer,
                    "_to": "accounts/" + transaction.payee,
                    "hash": transaction.hash,
                    "amount": transaction.amount,
                    "block": block.height,
                    "timestamp": block.time
                }
                account_documents.append({"_key": transaction.payee})
                payment_key = get_hash_of_dict(payment_document)
                payment_document["_key"] = payment_key
                payment_documents.append(payment_document)
            elif txn.type == "payment_v2":
                transaction: PaymentV2 = self.client.transaction_get(txn.hash, txn.type)
                account_documents.append({"_key": transaction.payer})
                for payment in transaction.payments:
                    payment_document = {
                        "_from": "accounts/" + transaction.payer,
                        "_to": "accounts/" + payment.payee,
                        "hash": transaction.hash,
                        "amount": payment.amount,
                        "block": block.height,
                        "timestamp": block.time
                    }

                    account_documents.append({"_key": payment.payee})
                    payment_key = get_hash_of_dict(payment_document)
                    payment_document["_key"] = payment_key
                    payment_documents.append(payment_document)
            elif txn.type in ["poc_receipts_v1", "poc_receipts_v2"]:
                transaction: Union[PocReceiptsV1, PocReceiptsV2] = self.client.transaction_get(txn.hash, txn.type)
                # hotspot_documents.append({"_key": transaction.path[0].challengee})
                for witness in transaction.path[0].witnesses:
                    receipt_document = {
                        "_from": "hotspots/" + transaction.path[0].challengee,
                        "_to": "hotspots/" + witness.gateway,
                        # "tx_power": transaction.path[0].receipt.tx_power,
                        "frequency": witness.frequency,
                        "datarate": witness.datarate,
                        "is_valid": witness.is_valid,
                        "signal": witness.signal,
                        "snr": witness.snr,
                        "timestamp": witness.timestamp,
                        "hash": txn.hash,
                        "block": block.height
                    }
                    try:
                        receipt_document["tx_power"] = transaction.path[0].receipt.tx_power
                        receipt_document["processing_time_s"] = (witness.timestamp - transaction.path[0].receipt.timestamp) / 1e9
                    except AttributeError:  # some receipts don't have "receipt" field
                        pass
                    # hotspot_documents.append({"_key": witness.gateway})
                    receipt_key = get_hash_of_dict(receipt_document)
                    receipt_document["_key"] = receipt_key
                    receipt_documents.append(receipt_document)
                    # elif txn.type == "add_gateway_v1":

        self.payments.importBulk(payment_documents, onDuplicate="ignore")
        self.accounts.importBulk(account_documents, onDuplicate="ignore")
        self.poc_receipts.importBulk(receipt_documents, onDuplicate="ignore")
        # self.hotspots.importBulk(hotspot_documents, onDuplicate="ignore")

    def delete_old_receipts(self):
        aql = f"""for receipt in poc_receipts
                    filter receipt.block < {self.sync_height - self.settings.block_inventory_size}
                    remove receipt in poc_receipts"""
        self.database.AQLQuery(aql)

    @staticmethod
    def process_block_parallel(transactions: List[BlockTransaction], block_height: int, block_time: int, settings: Settings, output_dict: dict,
                               i: int):
        payment_documents = []
        receipt_documents = []
        account_documents = []
        hotspot_documents = []
        _t = time.time()

        client = BlockchainNodeClient(settings)
        for txn in transactions:
            if txn.type == "payment_v1":
                transaction: PaymentV1 = client.transaction_get(txn.hash, txn.type)
                account_documents.append({"_key": transaction.payer})
                payment_document = {
                    "_from": "accounts/" + transaction.payer,
                    "_to": "accounts/" + transaction.payee,
                    "hash": transaction.hash,
                    "amount": transaction.amount,
                    "block": block_height,
                    "timestamp": block_time
                }
                account_documents.append({"_key": transaction.payee})
                payment_key = get_hash_of_dict(payment_document)
                payment_document["_key"] = payment_key
                payment_documents.append(payment_document)
            elif txn.type == "payment_v2":
                transaction: PaymentV2 = client.transaction_get(txn.hash, txn.type)
                account_documents.append({"_key": transaction.payer})
                for payment in transaction.payments:
                    payment_document = {
                        "_from": "accounts/" + transaction.payer,
                        "_to": "accounts/" + payment.payee,
                        "hash": transaction.hash,
                        "amount": payment.amount,
                        "block": block_height,
                        "timestamp": block_time
                    }

                    account_documents.append({"_key": payment.payee})
                    payment_key = get_hash_of_dict(payment_document)
                    payment_document["_key"] = payment_key
                    payment_documents.append(payment_document)
            elif txn.type in ["poc_receipts_v1", "poc_receipts_v2"]:
                transaction: Union[PocReceiptsV1, PocReceiptsV2] = client.transaction_get(txn.hash, txn.type)
                hotspot_documents.append({"_key": transaction.path[0].challengee})
                for witness in transaction.path[0].witnesses:
                    receipt_document = {
                        "_from": "hotspots/" + transaction.path[0].challengee,
                        "_to": "hotspots/" + witness.gateway,
                        # "tx_power": transaction.path[0].receipt.tx_power,
                        "frequency": witness.frequency,
                        "datarate": witness.datarate,
                        "is_valid": witness.is_valid,
                        "signal": witness.signal,
                        "snr": witness.snr,
                        "timestamp": witness.timestamp,
                        "hash": txn.hash,
                        "block": block_height
                    }
                    hotspot_documents.append({"_key": witness.gateway})
                    receipt_key = get_hash_of_dict(receipt_document)
                    receipt_document["_key"] = receipt_key
                    receipt_documents.append(receipt_document)

        output = {
            "payment_documents": payment_documents,
            "receipt_documents": receipt_documents,
            "account_documents": account_documents,
            "hotspot_documents": hotspot_documents
        }

        output_dict[i] = output
        return output_dict
        # return payment_documents, receipt_documents, account_documents, hotspot_documents


def get_hash_of_dict(d: dict) -> str:
    return hashlib.md5(json.dumps(d, sort_keys=True).encode('utf-8')).hexdigest()

