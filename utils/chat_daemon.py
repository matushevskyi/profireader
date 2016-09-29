import sys


sys.path.append('..')
from profapp.models.users import User
from profapp.models.messenger import Contact, Message
from profapp.constants import RECORD_IDS

from flask import Flask, g, request, current_app, session

from profapp import create_app, load_database
from flask_socketio import SocketIO, send, emit
# from flask.ext.login import LoginManager, current_user, AnonymousUserMixin



if __name__ == '__main__':

    app = create_app(apptype='socket')
    with app.app_context():
        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()
        socketio = SocketIO(app)


        @socketio.on('connect')
        def test_connect():
            print('connection')
            # print(current_user)


        @socketio.on('disconnect')
        def test_disconnect():
            print('disconnection')


        # @socketio.on('chat_event')
        # def check_chat_event():
        #     print(socketio.rooms())


        socketio.run(app)

