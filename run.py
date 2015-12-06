# coding: utf-8 

import logging
from yowsup.layers.auth import YowCryptLayer, YowAuthenticationProtocolLayer
from yowsup.layers.coder import YowCoderLayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.protocol_messages import YowMessagesProtocolLayer
from yowsup.layers.stanzaregulator import YowStanzaRegulator
from yowsup.layers.protocol_receipts import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks import YowAckProtocolLayer
from yowsup.stacks import YowStack
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.layers.protocol_iq.protocolentities import *
from yowsup.layers.protocol_iq import YowIqProtocolLayer
from yowsup.layers.axolotl import YowAxolotlLayer
from yowsup import env

from layer import EchoLayer
from process import MessageProcessor

logging.basicConfig(level=logging.DEBUG)
CREDENTIALS = ("5519998267695","93CkLqqLqNzCeECaPXbqWl3mIcY=")

if __name__ == "__main__":
    layers = (
        EchoLayer,
        (YowAuthenticationProtocolLayer,YowMessagesProtocolLayer,YowReceiptProtocolLayer,YowAckProtocolLayer, YowIqProtocolLayer),
        YowAxolotlLayer,
        YowCoderLayer,
        YowCryptLayer,
        YowStanzaRegulator,
        YowNetworkLayer
    )
    
    stack = YowStack(layers)
    stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, CREDENTIALS)
    stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])
    stack.setProp(YowCoderLayer.PROP_DOMAIN,YowConstants.DOMAIN)
    stack.setProp(YowCoderLayer.PROP_RESOURCE,env.CURRENT_ENV.getResource())
    
    processor = MessageProcessor(CREDENTIALS[0], CREDENTIALS[1],
                                 "https://neopay.herokuapp.com")
    stack.setProp(EchoLayer.PROP_PROCESSOR, processor)

    stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))

    try:
        load_counter = 0
        while True:
            stack.loop(timeout=0.5, count=1)

            load_counter += 1
            if load_counter >= 4:
                processor.load_pending_messages()
                load_counter = 0

            msg = processor.take_pending_message()
            if not msg:
                continue

            event = YowLayerEvent(EchoLayer.EVENT_FORWARD_MESSAGE,
                                  from_num=msg['from_num'], to_num=msg['to_num'],
                                  text=msg['text'])
            stack.broadcastEvent(event)
    except KeyboardInterrupt:
        stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))

