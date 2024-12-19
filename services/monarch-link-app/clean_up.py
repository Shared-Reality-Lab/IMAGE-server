#!/usr/bin/env python3
import json
from datetime import datetime
import logging


logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')


def clean_up(data):
    cleaned = {}
    for id in data:
        # last update timestamp is more than 3600 seconds
        # before current timestamp
        if not float(data[id]["timestamp"]) + 3600 < (
                datetime.timestamp(datetime.now())):
            cleaned[id] = data[id]
        else:
            logging.debug('Cleared ID value: '+id)
    return cleaned


try:
    with open('/usr/src/app/data.json', 'r') as openfile:
        # Load the JSON data
        data = json.load(openfile)

    # Process and write cleaned data
    cleaned_data = clean_up(data)
    with open('/usr/src/app/data.json', 'w') as openfile:
        json.dump(cleaned_data, openfile)
except Exception as e:
    logging.debug(e)
