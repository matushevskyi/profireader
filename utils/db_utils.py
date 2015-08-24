from db_init import db_session

def db(*args, **kwargs):
    return db_session.query(args[0]).filter_by(**kwargs)
