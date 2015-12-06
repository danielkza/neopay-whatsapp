from decimal import *
from multiprocessing import Lock
import requests

from session import WhatsappSession

class MessageProcessor(object):
    def __init__(self, username, password, base_url):
        self.base_url = base_url
        self.reqs = requests.Session()
        self.reqs.auth = (username, password)
        self.reqs.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        self._queue_lock = Lock()
        self._message_queue = []

        self.sessions = {}

    def url(self, url, *args, **kwargs):
        return self.base_url + '/' + url.format(*args, **kwargs)

    def load_pending_messages(self, limit=5):
        resp = self.reqs.get(self.url('messages'), params={'limit': limit})
        if resp.status_code == 200:
            with self._queue_lock:
                for message in resp.json():
                    self._message_queue.append(message)
        else:
            resp.raise_for_status()

    def get_user(self, phone):
        resp = self.reqs.get(self.url('users/by-phone/{}', phone))
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return None
        else:
            resp.raise_for_status()

    def _transfer_or_request(self, url_fmt, from_number, to_number, amount,
                             message):
        from_user = self.get_user(from_number)
        if not from_user:
            return False

        url = self.url(url_fmt, from_user['id'], to_number)
        resp = self.reqs.post(url,
            json={'amount': str(amount), 'message': message})
        if resp.status_code == 200:
            return True
        elif resp.status_code in (403, 422, 404):
            return False
        else:
            resp.raise_for_status()

    def request(self, from_number, to_number, amount, message):
        return self._transfer_or_request('users/{}/request/{}', from_number,
                                         to_number, amount, message)

    def transfer(self, from_number, to_number, amount, message):
        return self._transfer_or_request('users/{}/transfer/{}', from_number,
                                         to_number, amount, message)

    def take_pending_message(self):
        with self._queue_lock:
            if self._message_queue:
                return self._message_queue.pop(0)
            else:
                return None

    def create_user(self, phone, name, ssn):
        resp = self.reqs.post(self.url('users'),
            json={'phone': phone, 'name': name, 'ssn': ssn})

        if resp.status_code < 300:
            return resp.json()
        else:
            return None

    def update_user(self, id_, **params):
        resp = self.reqs.patch(self.url('users/{}', id_), json=params)
        if resp.status_code < 300:
            return resp.json()
        elif resp.status_code < 500:
            return None
        else:
            resp.raise_for_status()


    def get_session(self, phone):
        try:
            return self.sessions[phone]
        except KeyError:
            session = WhatsappSession(self, phone)
            
            resp = self.reqs.get(self.url('sessions/{}', phone))
            if resp.status_code == 200:
                d = dict(resp.json())
                d['processor'] = self
                session.__setstate__(d)
                self.sessions[phone] = session
            elif resp.status_code == 404:
                self.sessions[phone] = WhatsappSession(self, phone)
            else:
                resp.raise_for_status()

            return self.sessions[phone]


    def store_session(self, session):
        phone = session.number
        self.sessions[phone] = session
        resp = self.reqs.put(self.url('sessions/{}', phone),
            json=session.__getstate__())
        resp.raise_for_status()
