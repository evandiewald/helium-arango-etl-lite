from dotenv import load_dotenv
import os


class Settings(object):
    def __init__(self):
        load_dotenv()
        self._node_address = os.getenv('NODE_ADDRESS')
        self._arango_address = os.getenv('ARANGO_ADDRESS')
        self._arango_username = os.getenv('ARANGO_USERNAME')
        self._arango_password = '*****'
        self._arango_database = os.getenv('ARANGO_DATABASE')
        self._block_inventory_size = os.getenv('BLOCK_INVENTORY_SIZE')
        self._logs_path = os.getenv('LOGS_PATH')

    @property
    def node_address(self):
        return self._node_address

    @property
    def arango_address(self):
        return self._arango_address

    @property
    def arango_username(self):
        return self._arango_username

    @property
    def arango_password(self):
        return os.getenv('ARANGO_PASSWORD')

    @property
    def arango_database(self):
        return self._arango_database

    @property
    def block_inventory_size(self):
        return int(self._block_inventory_size)

    @property
    def logs_path(self):
        return os.getenv('LOGS_PATH')