from profapp import create_app
import argparse
import yappi

# if __name__ == '__main__':
parser = argparse.ArgumentParser(description='profireader application type')
parser.add_argument("apptype", default='profi')
args = parser.parse_args()
app = create_app(apptype=args.apptype)



def app_run():

    if args.apptype == 'front':
        port = 8888
    elif args.apptype == 'file':
        port = 9001
    elif args.apptype == 'static':
        port = 9000
    else:
        port = 8080
    #
    # yappi.start()
    app.run(port=port, host='0.0.0.0', debug=True)  # app.run(debug=True)

    # print(yappi.get_func_stats())
# import profile
# print(profile.run("app_run()"))

if __name__ == '__main__':

    # import cProfile,pstats
    #
    # pr = cProfile.Profile()
    # pr.enable()
    app_run()
    # pr.disable()
    # sortby = 'cumulative'
    # ps = pstats.Stats(pr).sort_stats(sortby)
    # ps.print_callers('/home/steve/PycharmProjects/profireader')







