import requests
import os
import h3
from pathlib import Path
import pandas as pd
import parse
from settings import Settings


def geo_index(h):
    # properly format the geospatial index in geoJSON format from the hex
    try:
        coordinates = h3.h3_to_geo(h)
    except TypeError:
        coordinates = [0, 0]
    return {"type": "Point", "coordinates": [coordinates[1], coordinates[0]]}


def process_gateway_inventory(settings: Settings):
    gz_path = Path("gateway_inventory_latest.csv.gz")
    csv_path = Path("gateway_inventory_latest.csv")

    url = settings.latest_inventories_url
    inventories = requests.get(url).json()

    data = pd.read_csv(inventories["gateway_inventory"])
    id = data.address.map("hotspots/{}".format)
    key = data.address
    location_geo = data.location.map(geo_index)

    data["_id"] = id
    data["_key"] = key
    data["location_geo"] = location_geo

    data = data.dropna()

    records = data.to_dict("records")

    try:
        os.remove(gz_path)
        os.remove(csv_path)
    except FileNotFoundError:
        pass

    inventory_height = int(parse.parse("gateway_inventory_{0}.csv.gz", inventories["gateway_inventory"].split("/")[-1])[0])

    return records, inventory_height
