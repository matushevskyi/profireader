from profapp import create_app
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="host", default='profi.ntaxa.com')
    parser.add_argument("--port", help="port", default='8080', type=int)
    parser.add_argument("--front", help="frontend", default='n')
    args = parser.parse_args()

    app = create_app(host=args.host, front=args.front)

    #app.run(host='127.40.71.198', port=8080)  #app.run(debug=True)
    app.run(host='0.0.0.0', port=args.port, debug=True)  #app.run(debug=True)
    #app.run()
