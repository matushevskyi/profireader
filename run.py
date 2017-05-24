from profapp import create_app
import argparse
from profapp.constants.APPLICATION_PORTS import APPLICATION_PORTS

# if __name__ == '__main__':
parser = argparse.ArgumentParser(description='profireader application type')
parser.add_argument("apptype", default='profi')
args = parser.parse_args()
app = create_app(apptype=args.apptype)
# from flask_socketio import SocketIO, send, emit


if __name__ == '__main__':

    port = APPLICATION_PORTS[args.apptype]

    try:
        app.log.info("starting " + args.apptype)
        app.run(port=port, host='0.0.0.0',
                debug=port in [APPLICATION_PORTS['profi'], APPLICATION_PORTS['front']])  # app.run(debug=True)
    except Exception as e:
        app.log.critical(e)
        raise e
