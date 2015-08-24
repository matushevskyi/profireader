from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from config import ProductionDevelopmentConfig
from sqlalchemy import event
from utils.validators import validators

# see this: http://flask.pocoo.org/docs/0.10/patterns/sqlalchemy/
# engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
engine = create_engine(ProductionDevelopmentConfig.SQLALCHEMY_DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()


# this event is called whenever an attribute
# on a class is instrumented
@event.listens_for(Base, 'attribute_instrument')
def configure_listener(class_, key, inst):
    if not hasattr(inst.property, 'columns'):
        return
    # this event is called whenever a "set"
    # occurs on that instrumented attribute

    @event.listens_for(inst, "set", retval=True)
    def set_(instance, value, oldvalue, initiator):
        validator = validators.get(inst.property.columns[0].type.__class__)
        if validator:
            return validator(value)
        else:
            return value

Base.query = db_session.query_property()
