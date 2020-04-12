import os
import logging
import asyncio
import json
from nats.aio.client import Client as NatsClient

logging.basicConfig(level=logging.DEBUG)

def handle(req):
    logging.debug(f"Received a message. Saving Raw data and sending a message to NATS")
    save_to_fs(req)
    NATS_URL = os.getenv('nats_url')

    loop = asyncio.new_event_loop()
    loop.run_until_complete(send_message(NATS_URL, req.encode(), loop))
    loop.close()

    return req

async def send_message(nats_url, message, loop):
   client = NatsClient()
   await client.connect(io_loop=loop,servers=[nats_url])
   await client.publish("clickevent.rawdata", message)
   logging.debug(f"Sent the message")
   await client.close()    

def save_to_fs(message):
    logging.debug(f"The message to save: {message}")


