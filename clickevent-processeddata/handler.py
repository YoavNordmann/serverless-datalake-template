import os
import logging
import json

logging.basicConfig(level=logging.DEBUG)

def handle(req):
    logging.debug(f"Received a message. Saving Processed data")
    save_to_fs(req)
    return req

def save_to_fs(message):
    logging.debug(f"The message to save: {message}")


