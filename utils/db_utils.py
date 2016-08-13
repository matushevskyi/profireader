from flask import g

# TODO: YG by OZ: remove this file
def db(*args, **kwargs):
    return g.db.query(*args).filter_by(**kwargs)
