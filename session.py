from decimal import Decimal, DecimalException

# def minEditDistance(s1,s2):
#     if len(s1) < len(s2):
#         return minEditDistance(s2,s1)

#     if len(s2) == 0:
#         return len(s1)

#     previous_row = range(len(s2) + 1)
#     for i, c1 in enumerate(s1):
#         current_row = [i + 1]
#         for j, c2 in enumerate(s2):
#             insertions = previous_row(s2)[j + 1] + 1
#             deletions = current_row[j] + 1
#             substitutions = previous_row[j] + (c1 != c2)
#             current_row.append(min(insertions,deletions,substitutions))
#         previous_row = current_row

#     return previous_row[-1]

class WhatsappSession(object):
    WAITING_NAME = 0
    WAITING_SSN = 1
    WAITING_COMMAND = 2
    WAITING_AMOUNT_SEND = 3
    WAITING_AMOUNT_REQ = 4
    WAITING_PHONE_NUM_SEND = 5
    WAITING_PHONE_NUM_REQ = 6   
    WAITING_CONFIRM_SEND = 7
    WAITING_CONFIRM_REQ = 8
    NEW_USER = 9

    def __init__(self, processor, number, initial_state=NEW_USER):
        self.state = initial_state
        self.processor = processor
        self.number = number

        self.name = None
        self.ssn = None
        self.amount = None
        self.to_number = None

    def __getstate__(self):
        d = dict(self.__dict__)
        del d['processor']
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)

    def parse_amount(self, s):
        try:
            d = Decimal(s)
            return str(d)
        except (DecimalException, ValueError):
            return None

    def parse_name(self, s):
        return s

    def parse_command(self, s):
        if ' ' in s:
            return 0
        elif s == "send":
            return 1
        elif s.startswith("req"):
            return 2
        elif s.startswith("bal"):
            return 3
        else:
            return 0

    def parse_ssn(self, s):
        digits = filter(lambda c: c.isdigit, s)
        if len(digits) == 9:
            return digits

        return None

    def parse_phone(self, s):
        if all(c.isdigit() or c == '-' or c == ' ' for c in s):
            digits = filter(lambda c: c.isdigit(), s)
            if len(digits) >= 11:
                return digits

        return None

    def _process_message(self, message):
        if 'cancel' in message:
            self.name = None
            self.ssn = None
            self.to_number = None
            self.amount = None

            if self.processor.get_user(self.number):
                return self.WAITING_COMMAND, "Command canceled, feel free to try again!"
            else:
                return self.NEW_USER, "Registration canceled, send any message to start over"

        if self.state == self.NEW_USER:
            return self.WAITING_NAME, "Welcome to NeoPay! Write out your name to start creating a free account."
        elif self.state == self.WAITING_NAME:
            self.name = self.parse_name(message)
            return self.WAITING_SSN, "Hi " + self.name + ". Please tell me your SSN (Social Security Number):",
        elif self.state == self.WAITING_SSN:
            self.ssn = self.parse_ssn(message) 
            if self.ssn:
                user = self.processor.get_user(self.number)
                if user:
                    user = self.processor.update_user(user['id'], name=self.name, ssn=self.ssn)                
                else:
                    user = self.processor.create_user(self.number, self.name, self.ssn)
                
                if user:
                    self.name = None
                    self.ssn = None
                    return self.WAITING_COMMAND, "Your NeoPay account is ready! You can download the NeoPay app from your app store if you want. You can also write 'Send' to send a payment o 'Request' to request a payment to anyone on your contact list."
                else:
                    return self.WAITING_NAME, "There was an error creating your account, please try again"
            else:
                return self.WAITING_SSN, "Please tell me your 9-digit SSN number:"
        elif self.state == self.WAITING_COMMAND:
            command = self.parse_command(message)
            if command == 0:
                return self.WAITING_COMMAND, "I don't understand. Please type 'Send' or 'Request'"
            #send
            elif command == 1:
                return self.WAITING_PHONE_NUM_SEND, "Type the number you want to send money to:"
            #receive
            elif command == 2:
                return self.WAITING_PHONE_NUM_REQ, "Type the number you want to request money from:"
            #balance
            elif command == 3:
                user = self.processor.get_user(self.number)
                balance = (user and user['balance']) or 0
                return self.WAITING_COMMAND, "Your balance is: ${}".format(balance)
        elif self.state in (self.WAITING_PHONE_NUM_SEND, self.WAITING_PHONE_NUM_REQ):
            self.to_number = self.parse_phone(message)
            
            if self.to_number:
                if self.state == self.WAITING_PHONE_NUM_SEND:
                    user = self.processor.get_user(self.number)
                    balance = user and user['balance']

                    return self.WAITING_AMOUNT_SEND, "How much do you want to send? Your current balance is $" + str(balance)
                else:
                    return self.WAITING_AMOUNT_REQ, "How much do you want to request?"
            else:
                return self.state, "I don't understand this phone number, please try again"
        elif self.state in (self.WAITING_AMOUNT_SEND, self.WAITING_AMOUNT_REQ):
            self.amount = self.parse_amount(message)
            if self.amount:
                if self.state == self.WAITING_AMOUNT_SEND:
                    return self.WAITING_CONFIRM_SEND, "You will send ${} to {}. Confirm?".format(self.amount, self.to_number)
                else:
                    return self.WAITING_CONFIRM_REQ, "You will request ${} to {}. Confirm?".format(self.amount, self.to_number)
            else:
                return self.state, "I don't understand this amount, please try again"
        elif self.state in (self.WAITING_CONFIRM_SEND, self.WAITING_AMOUNT_REQ):
            if message.startswith("y"):
                if self.state == self.WAITING_CONFIRM_SEND:
                    result = self.processor.transfer(self.number, self.to_number, self.amount, "Hello, I want to send you money!")
                else:
                    result = self.processor.request(self.number, self.to_number, self.amount, "Hello, I want to ask you for money!")

                if result:
                    self.to_number = None
                    self.amount = None
                    return self.WAITING_COMMAND, "Transaction processed succesfully!"
                else:
                    return self.WAITING_COMMAND, "There was an error processing your transaction, please try again"
            else:
                return self.WAITING_COMMAND, "Transaction aborted."
        else:
            return self.state, "I don't understand this message. Please try again."

    def process_message(self, message):
        state, reply = self._process_message(message.lower())
        self.state = state
        return reply
