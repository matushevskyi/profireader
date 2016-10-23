import psycopg2
import psycopg2.extensions
from profapp import create_app, load_database
import socketio, eventlet
import re, time, datetime
from profapp.models.messenger import Contact, Message
from profapp.controllers.errors import BadDataProvided
from flask import g
from utils import db_utils


connected_sid_user_id_chatroom_id = {}
connected_user_id_sids = {}
connected_chatroom_id_sids = {}


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
    load_database(app.config['SQLALCHEMY_DATABASE_URI'])()

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

def notify_unread(user_id, chatroom_ids = []):
    to_send = {'total': int(
        float(db_utils.execute_function("message_unread_count('%s', NULL)" % (user_id,))))}
    for chatroom_id in chatroom_ids:
        to_send[chatroom_id] = int(float(
            db_utils.execute_function("message_unread_count('%s', '%s')" % (user_id, chatroom_id))))
    if user_id in connected_user_id_sids:
        for sid_for_another_user in connected_user_id_sids[user_id]:
            sio.emit('set_unread_message_count', to_send, sid_for_another_user)

@sio.on('connect')
def connect(sid, environ):
    user_id = check_user_id(environ)
    print('connect', user_id)
    if not user_id:
        return False

    connected_sid_user_id_chatroom_id[sid] = [user_id, None]
    append_create(connected_user_id_sids, user_id, sid)


@sio.on('select_chat_room_id')
def select_chat_room(sid, select_chat_room_id):
    with controlled_execution():
        print('chat room selected', select_chat_room_id)
        connected_sid_user_id_chatroom_id[sid][1] = select_chat_room_id
        append_create(connected_chatroom_id_sids, select_chat_room_id, sid)


@sio.on('disconnect')
def disconnect(sid):
    [user_id, chatroom_id] = connected_sid_user_id_chatroom_id[sid]
    print('disconnect', sid, user_id, chatroom_id)
    remove_delete(connected_user_id_sids, user_id, sid)
    remove_delete(connected_chatroom_id_sids, chatroom_id, sid)
    del connected_sid_user_id_chatroom_id[sid]


@sio.on('send_message')
def send_message(sid, message_text):
    with controlled_execution():
        [user_id, chatroom_id] = connected_sid_user_id_chatroom_id[sid]
        print('send_message',user_id, chatroom_id)
        contact = Contact.get(chatroom_id)

        message = Message(contact_id=contact.id, content=message_text, from_user_id=user_id)
        message.save()
        message = Message.get(message.id)

        another_user_to_notify_unread = contact.user1_id if contact.user2_id == user_id else contact.user2_id
        if chatroom_id in connected_chatroom_id_sids:
            for sid_for_this_chat_room in connected_chatroom_id_sids[chatroom_id]:
                if connected_sid_user_id_chatroom_id[sid_for_this_chat_room][0] == another_user_to_notify_unread:
                    another_user_to_notify_unread = None
                    print("SELECT message_set_read('%s', ARRAY ['%s']);" % (contact.id, message.id))
                    g.db().execute("SELECT message_set_read('%s', ARRAY ['%s']);" % (contact.id, message.id))
                    break

        message_tosend = message.client_message()

        for sid_for_this_chat_room in connected_chatroom_id_sids[chatroom_id]:
            sio.emit('new_message', message_tosend, sid_for_this_chat_room)

        if another_user_to_notify_unread:
            notify_unread(another_user_to_notify_unread, [chatroom_id])

        return {'ok': True, 'message_id': message.id}

@sio.on('load_messages')
def load_messages(sid, message):
    with controlled_execution():
        print('load_messages', message)
        [user_id, __chatroom_id] = connected_sid_user_id_chatroom_id[sid]
        contact = Contact.get(message['chat_room_id'])
        older = message.get('older', False)
        ret = contact.get_messages(50, older, message.get('first_message_id' if older else 'last_message_id', None))

        read_ids = [m.id for m in ret['messages'] if m.from_user_id != user_id and not m.read_tm]
        if len(read_ids):
            g.db().execute("SELECT message_set_read('%s', ARRAY ['%s']);" % (contact.id, "', '".join(read_ids)))
            notify_unread(user_id, [message['chat_room_id']])

        ret['messages'] = [m.client_message() for m in ret['messages']]

        return ret


app = socketio.Middleware(sio, app)
eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
