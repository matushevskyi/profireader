import psycopg2
import psycopg2.extensions
from profapp import create_app, load_database
import socketio, eventlet
import re, time, datetime
from profapp.models.messenger import Contact, Message
from profapp.controllers.errors import BadDataProvided
from flask import g
from utils import db_utils


connected_sid_user_id = {}
connected_user_id_sids = {}


class controlled_execution:
    def __enter__(self):
        ctx.push()
        return True

    def __exit__(self, type, value, traceback):
        g.db.commit()
        ctx.pop()


app = create_app(apptype='profi')
ctx = app.app_context()

with controlled_execution():
    load_database(app.config['SQLALCHEMY_DATABASE_URI'])(echo = True)

sio = socketio.Server(cookie='prsio')

def append_create(dict, index, value):
    if not index:
        return None

    if index not in dict:
        dict[index] = []

    if value not in dict[index]:
        dict[index].append(value)


def remove_delete(dict, index, value):
    if not index or index not in dict:
        return None

    dict[index].remove(value)
    if len(dict[index]) == 0:
        del dict[index]


def check_user_id(environ):
    session_id = environ.get('HTTP_COOKIE', None)
    if not session_id:
        return False
    session_id = re.sub(r'^(.*;\s*)?beaker\.session\.id=([0-9a-f]*).*$', r'\2', session_id)
    import memcache
    mc = memcache.Client(['memcached.profi:11211'], debug=0)
    session = mc.get(session_id + '_session')
    return session.get('user_id', False) if session else False

def get_unread(user_id, chatroom_ids = []):
    to_send = {'total': int(
        float(db_utils.execute_function("message_unread_count('%s', NULL)" % (user_id,))))}
    for chatroom_id in chatroom_ids:
        to_send[chatroom_id] = int(float(
            db_utils.execute_function("message_unread_count('%s', '%s')" % (user_id, chatroom_id))))
    return to_send


@sio.on('connect')
def connect(sid, environ):
    user_id = check_user_id(environ)
    print('connect', user_id)
    if not user_id:
        return False

    connected_sid_user_id[sid] = user_id
    append_create(connected_user_id_sids, user_id, sid)

@sio.on('disconnect')
def disconnect(sid):
    user_id = connected_sid_user_id[sid]
    print('disconnect', sid)
    remove_delete(connected_user_id_sids, user_id, sid)
    # remove_delete(connected_chatroom_id_sids, chatroom_id, sid)
    del connected_sid_user_id[sid]


@sio.on('send_message')
def send_message(sid, data):
    with controlled_execution():
        user_id = connected_sid_user_id[sid]
        print('send_message', user_id)
        contact = Contact.get(data['chatroom_id'])

        message = Message(contact_id=contact.id, content=data['content'], from_user_id=user_id)
        message.save()
        message = Message.get(message.id)
        message_tosend = message.client_message()

        for sid_for_author in connected_user_id_sids[user_id]:
            sio.emit('message_notification', {
                'new_message':  message_tosend
            }, sid_for_author)

        another_user_to_notify_unread = contact.user1_id if contact.user2_id == user_id else contact.user2_id
        unread = get_unread(another_user_to_notify_unread, [contact.id])
        for sid_for_receiver in connected_user_id_sids[another_user_to_notify_unread]:
            sio.emit('message_notification', {
                'new_message':  message_tosend,
                'unread': unread
            }, sid_for_receiver)

        return {'ok': True, 'message_id': message.id}


@sio.on('read_message')
def read_messages(sid, message_id):
    with controlled_execution():
        message = Message.get(message_id)
        contact = Contact.get(message.contact_id)
        if message.read_tm is None:
            another_user_to_notify_unread = contact.user1_id if contact.user2_id == message.from_user_id else contact.user2_id
            print("SELECT message_set_read('%s', ARRAY ['%s']);" % (message.contact_id, message.id))
            g.db().execute("SELECT message_set_read('%s', ARRAY ['%s']);" % (message.contact_id, message.id))
            unread = get_unread(another_user_to_notify_unread, [contact.id])
            for sid_for_receiver in connected_user_id_sids[another_user_to_notify_unread]:
                sio.emit('message_notification', {
                    'unread': unread
                }, sid_for_receiver)


@sio.on('load_messages')
def load_messages(sid, message):
    with controlled_execution():
        import time
        # time.sleep(2)  # delays for 5 seconds
        print('load_messages', message)
        user_id = connected_sid_user_id[sid]
        contact = Contact.get(message['chat_room_id'])
        older = message.get('older', False)
        ret = contact.get_messages(50, older, message.get('first_message_id' if older else 'last_message_id', None))

        read_ids = [m.id for m in ret['messages'] if m.from_user_id != user_id and not m.read_tm]
        if len(read_ids):
            g.db().execute("SELECT message_set_read('%s', ARRAY ['%s']);" % (contact.id, "', '".join(read_ids)))
            unread = get_unread(user_id, [contact.id])
            for sid_for_receiver in connected_user_id_sids[user_id]:
                sio.emit('message_notification', {
                    'unread': unread
                }, sid_for_receiver)

        ret['messages'] = [m.client_message() for m in ret['messages']]
        return ret

app = socketio.Middleware(sio, app)
eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
