import sys
sys.path.append('..')
from profapp.models.bak_articles import Article, ArticleCompany, ArticleCompanyHistory, \
    ArticlePortalDivision
from profapp.models.company import Company, UserCompany
from profapp.models.files import File
from profapp.models.users import User
from profapp.models.portal import Portal
from profapp.models.pr_base import MLStripper
from sqlalchemy import create_engine, event
from profapp.models.pr_base import Search
from profapp.constants.SEARCH import RELEVANCE
import re
from sqlalchemy.orm import scoped_session, sessionmaker
from config import ProductionDevelopmentConfig
import datetime
classes = [ArticlePortalDivision, Article, ArticleCompany, ArticleCompanyHistory,
           Company, UserCompany, File, User, Portal]
engine = create_engine(ProductionDevelopmentConfig.SQLALCHEMY_DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))


def add_to_search(target=None):

    if hasattr(target, 'search_fields'):
        target_fields = ','.join(target.search_fields.keys())
        target_dict = target.get_client_side_dict(fields=target_fields + ',id')
        options = {'relevance': lambda field_name: getattr(RELEVANCE, field_name),
                   'processing': lambda text: MLStripper().strip_tags(text),
                   'index': lambda target_id: target_id}
        md_time = datetime.datetime.now()
        default_time = datetime.datetime.now()
        if hasattr(target, 'publishing_tm'):
            md_time = getattr(target, 'publishing_tm', default_time)
        elif hasattr(target, 'md_tm'):
            md_time = getattr(target, 'md_tm', default_time)
        elif hasattr(target, 'cr_tm'):
            md_time = getattr(target, 'cr_tm', default_time)
        elif hasattr(target, 'registered_tm'):
            md_time = getattr(target, 'registered_tm', default_time)
        for field in target_fields.split(','):
            field_options = target.search_fields[field]
            field_options.update({key: options[key] for key in options
                                 if key not in field_options.keys()})
            pos = getattr(target, 'position', 0)
            position = pos if pos else 0
            db_session.add(Search(index=field_options['index'](target_dict['id']),
                                  table_name=target.__tablename__,
                                  relevance=field_options['relevance'](field), kind=field,
                                  text=field_options['processing'](str(target_dict[field])),
                                  position=position, md_tm=md_time))

def update_search_table(target=None):

    if hasattr(target, 'search_fields'):
        if delete_from_search(target):
            add_to_search(target)
        else:
            add_to_search(target)


def delete_from_search(target):
    if hasattr(target, 'search_fields') and \
            db_session.query(Search).filter_by(index=target.id).count():
        db_session.query(Search).filter_by(index=target.id).delete()
        return True
    return False


if __name__ == '__main__':
    time = datetime.datetime.now()
    elem_count = 0
    quantity = 0
    percent_to_str = ''
    percents = []
    answer = input(
        "Are you sure? \n If you'l start this process, your database will be overwritten. "
        "Yes|No")
    prompt = True if answer in ['yes', 'Yes', 'y', 'YES', 'tak'] else False
    if not prompt:
        exit('The script has been closed.')
    for cls in classes:
        if hasattr(cls, 'search_fields'):
            elem_count += db_session.query(cls).count()
            quantity = elem_count

    for cls in classes:
        variables = vars(cls).copy()
        variables = variables.keys()

        for key in variables:
            if type(key) is not bool:
                keys = getattr(cls, str(key), None)
                try:
                    stripped_key = str(keys).split('.')[1]
                    type_of_field = str(cls.__table__.c[stripped_key].type)
                    chars_int = int(re.findall(r'\b\d+\b', type_of_field)[0])
                    if chars_int > 36:
                        for c in db_session.query(cls).all():
                            persent = int(100 * int(elem_count)/int(quantity))
                            elem_count -= 1
                            original_field = getattr(c, stripped_key)
                            modify_field = original_field + ' '
                            update_search_table(target=c)
                            if persent >= 0 and persent not in percents:
                                percents.append(persent)
                                percent_to_str += '='
                                print(percent_to_str+'>', str(persent-100).replace('-', '')+'%')
                        break
                except Exception as e:
                    pass
    execute_time = datetime.datetime.now()-time
    print('Updated successfully')
    print('Execution time: {time}'.format(time=execute_time))
    db_session.commit()
