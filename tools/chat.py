import sys
sys.path.append('..')

from profapp import create_app, load_database
import socketio, eventlet
import re
from profapp.models.messenger import Contact, Message, Notification
from flask import g
from profapp.utils import db

connected_sid_user_id = {}
connected_user_id_sids = {}


class controlled_execution:
    def __enter__(self):
        ctx.push()
        return True

    def __exit__(self, type, value, traceback):
        g.db.commit()
        ctx.pop()


app = create_app(apptype='profi', config='config.CommandLineConfig')

ctx = app.app_context()

with controlled_execution():
    print('connecting to database')
    load_database(app.config['SQLALCHEMY_DATABASE_URI'])(echo=True)

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


def get_unread(user_id, chatroom_ids=[]):
    to_send = {
        'messages': int(float(db.execute_function("message_unread_count('%s', NULL)" % (user_id,)))),
        'messages_per_chat_room': {},
        'contacts': int(float(db.execute_function("contact_request_count('%s')" % (user_id,)))),
        'notifications': int(float(db.execute_function("notification_unread_count('%s')" % (user_id,))))

    }

    for chatroom_id in chatroom_ids:
        to_send['messages_per_chat_room'][chatroom_id] = int(float(
            db.execute_function("message_unread_count('%s', '%s')" % (user_id, chatroom_id))))
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
def send_message(sid, event_data):
    with controlled_execution():
        user_id = connected_sid_user_id[sid]
        print('send_message', user_id)
        contact = Contact.get(event_data['chatroom_id'])

        message = Message(contact_id=contact.id, content=event_data['content'], from_user_id=user_id)
        message.save()
        message = Message.get(message.id)
        message_tosend = message.client_message()

        for sid_for_author in connected_user_id_sids[user_id]:
            sio.emit('general_notification', {
                'new_message': message_tosend
            }, sid_for_author)

        another_user_to_notify_unread = contact.user1_id if contact.user2_id == user_id else contact.user2_id
        unread = get_unread(another_user_to_notify_unread, [contact.id])
        for sid_for_receiver in connected_user_id_sids[another_user_to_notify_unread]:
            sio.emit('general_notification', {
                'new_message': message_tosend,
                'unread': unread
            }, sid_for_receiver)

        return {'ok': True, 'message_id': message.id}


@sio.on('request_status_changed')
def send_contact_requested(sid, mes_data):
    with controlled_execution():
        from profapp.models.users import User
        usr = User.get(mes_data['to_user_id'])
        data_to_send = {
            'request_status_changed': mes_data,
            'unread': get_unread(usr.id, [])
        }
        if usr.id in connected_user_id_sids:
            for sid_for_recipient in connected_user_id_sids[usr.id]:
                sio.emit('general_notification', data_to_send, sid_for_recipient)

@sio.on('send_notification')
def send_notification(sid, notification_data):
    with controlled_execution():
        from profapp.models.users import User
        usr = User.get(notification_data['to_user_id'])
        n = Notification(to_user_id=usr.id, notification_type=notification_data['notification_type'],
                         notification_data=notification_data, content=notification_data['content'])

        n.save()
        notification = Notification.get(n.id)
        data_to_send = {
            'new_notification': notification.client_message(),
            'unread': get_unread(usr.id, [])}

        if usr.id in connected_user_id_sids:
            for sid_for_recipient in connected_user_id_sids[usr.id]:
                sio.emit('general_notification', data_to_send, sid_for_recipient)



@sio.on('read_message')
def read_message(sid, message_id):
    with controlled_execution():
        message = Message.get(message_id)
        contact = Contact.get(message.contact_id)
        if message.read_tm is None:
            another_user_to_notify_unread = contact.user1_id if contact.user2_id == message.from_user_id else contact.user2_id
            print("SELECT message_set_read('%s', ARRAY ['%s']);" % (message.contact_id, message.id))
            g.db().execute("SELECT message_set_read('%s', ARRAY ['%s']);" % (message.contact_id, message.id))
            unread = get_unread(another_user_to_notify_unread, [contact.id])
            for sid_for_receiver in connected_user_id_sids[another_user_to_notify_unread]:
                sio.emit('general_notification', {
                    'unread': unread
                }, sid_for_receiver)


@sio.on('read_notification')
def read_notification(sid, notification_id):
    with controlled_execution():
        notification = Notification.get(notification_id)
        if notification.read_tm is None:
            print("SELECT notification_set_read(ARRAY ['%s']);" % (notification.id,))
            g.db().execute("SELECT notification_set_read(ARRAY ['%s']);" % (notification.id,))
            unread = get_unread(notification.to_user_id)
            for sid_for_receiver in connected_user_id_sids[notification.to_user_id]:
                sio.emit('general_notification', {'unread': unread}, sid_for_receiver)


@sio.on('load_messages')
def load_messages(sid, event_data):
    with controlled_execution():
        # time.sleep(2)  # delays for 5 seconds
        print('load_messages', event_data)
        user_id = connected_sid_user_id[sid]
        contact = Contact.get(event_data['chat_room_id'])
        older = event_data.get('older', False)
        ret = contact.get_messages(50, older, event_data.get('first_id' if older else 'last_id', None))

        read_ids = [m.id for m in ret['items'] if m.from_user_id != user_id and not m.read_tm]
        if len(read_ids):
            g.db().execute("SELECT message_set_read('%s', ARRAY ['%s']);" % (contact.id, "', '".join(read_ids)))
            unread = get_unread(user_id, [contact.id])
            for sid_for_receiver in connected_user_id_sids[user_id]:
                sio.emit('general_notification', {
                    'unread': unread
                }, sid_for_receiver)

        ret['items'] = [m.client_message() for m in ret['items']]
        return ret


@sio.on('load_notifications')
def load_notifications(sid, event_data):
    with controlled_execution():
        print('load_notifications', event_data)
        user_id = connected_sid_user_id[sid]

        older = event_data.get('older', False)
        ret = Notification.get_notifications(50, user_id, older, event_data.get('first_id' if older else 'last_id', None))
        print(ret)

        read_ids = [n.id for n in ret['items'] if not n.read_tm]
        if len(read_ids):
            g.db().execute("SELECT notification_set_read(ARRAY ['%s']);" % ("', '".join(read_ids)))
            unread = get_unread(user_id)
            for sid_for_receiver in connected_user_id_sids[user_id]:
                sio.emit('general_notification', {
                    'unread': unread
                }, sid_for_receiver)

        ret['items'] = [n.client_message() for n in ret['items']]
        return ret


app = socketio.Middleware(sio, app)
eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
