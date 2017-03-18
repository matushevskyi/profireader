from profapp import create_app
import argparse

# if __name__ == '__main__':
parser = argparse.ArgumentParser(description='profireader application type')
parser.add_argument("apptype", default='profi')
args = parser.parse_args()
app = create_app(apptype=args.apptype)
# from flask_socketio import SocketIO, send, emit

if __name__ == '__main__':

    if args.apptype == 'file':
        port = 9001
    elif args.apptype == 'socket':
        port = 5000
    elif args.apptype == 'static':
        port = 9000
    if args.apptype == 'front':
        port = 8090
    else:
        port = 8080

    app.run(port=port, host='0.0.0.0', debug=port in [8080, 8090])  # app.run(debug=True)

