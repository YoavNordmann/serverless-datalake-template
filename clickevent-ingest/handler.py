import os
import logging
import asyncio
import json
from nats.aio.client import Client as NatsClient

logging.basicConfig(level=logging.DEBUG)

def handle(event, context):
    logging.debug(f"Received a message: {str(event.body)}")
    NATS_URL = os.getenv('nats_url')

    loop = asyncio.new_event_loop()
    loop.run_until_complete(send_message(NATS_URL, event.body, loop))
    loop.close()

    return {
        "statusCode": 200,
        "body": "Message Handled"
    }

async def send_message(nats_url, message, loop):
   client = NatsClient()
   await client.connect(io_loop=loop,servers=[nats_url])
   await client.publish("clickevent.ingest", message)
   await client.flush()
   logging.debug(f"Sent the message")
   await client.close()    
