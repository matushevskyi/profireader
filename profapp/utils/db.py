from flask import g


# TODO: YG by OZ: remove this file
def query_filter(*args, **kwargs):
    return g.db.query(*args).filter_by(**kwargs)


def execute_function(sql):
    # print(sql)

    return [r for (r,) in g.db().execute("SELECT %s" % (sql,))]

    # for (r,) in ret:
    #     return r


def execute_function_0(sql):
    # print(sql)

    ret = g.db().execute("SELECT %s" % (sql,))

    for (r,) in ret:
        return r


def create_uuid():
    return execute_function_0('create_uuid(NULL)')


def compile(q):
    print(q.statement.compile(compile_kwargs={"literal_binds": True}))
