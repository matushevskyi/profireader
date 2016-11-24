from flask import g

# TODO: YG by OZ: remove this file
def db(*args, **kwargs):
    return g.db.query(*args).filter_by(**kwargs)


def execute_function(sql):
    print(sql)
    ret = g.db().execute("SELECT %s" % (sql,))

    for (r,) in ret:
        return r

def compile(q):
    print(q.statement.compile(compile_kwargs={"literal_binds": True}))