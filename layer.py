# coding: utf-8 

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity

class EchoLayer(YowInterfaceLayer):
    PROP_PROCESSOR = "neopay.prop.processor"
    EVENT_FORWARD_MESSAGE = "neopay.event.forward" 

    def __init__(self):
        super(EchoLayer, self).__init__()

    @property
    def processor(self):
        return self.getProp(self.PROP_PROCESSOR, None)

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom())
        readReceipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom(),True)

        #send receive message and read receipts
        self.toLower(receipt)
        self.toLower(readReceipt)

        #get and store user number
        userFrom = messageProtocolEntity.getFrom()
        charIndex = userFrom.index('@')
        userPhone = userFrom[:charIndex]

        session = self.processor.get_session(userPhone)
        receivedMessage = messageProtocolEntity.getBody()
        messageBody = session.process_message(receivedMessage)

        outgoingMessageProtocolEntity = TextMessageProtocolEntity(messageBody,
        	to=userFrom)
        self.toLower(outgoingMessageProtocolEntity)

        self.processor.store_session(session)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self,entity):
        self.toLower(entity.ack())

    def normalizeJid(self, number):
        if '@' in number:
            return number
        elif "-" in number:
            return "%s@g.us" % number

        return "%s@s.whatsapp.net" % number

    def onEvent(self, event):
    	if event.getName() == self.EVENT_FORWARD_MESSAGE:
    		to_num = event.getArg('to_num')
    		text = event.getArg('text')

    		msg = TextMessageProtocolEntity(text, to=self.normalizeJid(to_num))
        	self.toLower(msg)
        	return True
