# helium-arango-etl-lite
Lightweight ETL to store adjacency data (e.g. payments, witness receipts) from the Helium blockchain in an ArangoDB database. 

## Quickstart (Ubuntu)
* Follow these instructions to run [`blockchain-node`](https://github.com/helium/blockchain-node).
* Launch ArangoDB via docker

`docker run -d --name arango -p 8529:8529 -h 0.0.0.0 -e ARANGO_ROOT_PASSWORD=password arangodb/arangodb:3.8.2`
* If you open port 8529, you should be able to view the Arango WebUI in your browser at:

http://{HOST_ADDRESS}:8529

* Clone this repository and `cd` into the main directory
* Make a copy of `.env.template`, call it `.env`, and edit the environment variables with your settings. 
* Install dependencies with 

`pip3 install requirements.txt`

* Run the ETL

`cd helium_arango_etl_lite && python3 etl.py`

After backfilling all blocks stored on the node, the service should listen for new blocks and process them as they come in. 