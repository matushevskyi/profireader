import sys

sys.path.append('..')

from profapp.models.materials import Material, FileImg
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from config import ProductionDevelopmentConfig
import datetime
from sqlalchemy.sql import or_, and_

engine = create_engine(ProductionDevelopmentConfig.SQLALCHEMY_DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
if __name__ == '__main__':
    # time = datetime.datetime.now()
    # elem_count = 0
    # quantity = 0
    # percent_to_str = ''
    # percents = []
    # answer = input(
    #     "Are you sure? \n If you'l start this process, your database will be overwritten. "
    #     "Yes|No")

    materials_without_illustrations = db_session.query(Material).filter(
        and_(Material.illustration_id == None, Material.image_file_id != None))
    for m in materials_without_illustrations:
        print(m)

        # prompt = True if answer in ['yes', 'Yes', 'y', 'YES', 'tak'] else False
        # if not prompt:
        #     exit('The script has been closed.')
        #
        #
        # for cls in classes:
        #     variables = vars(cls).copy()
        #     variables = variables.keys()
        #
        #     for key in variables:
        #         if type(key) is not bool:
        #             keys = getattr(cls, str(key), None)
        #             try:
        #                 stripped_key = str(keys).split('.')[1]
        #                 type_of_field = str(cls.__table__.c[stripped_key].type)
        #                 chars_int = int(re.findall(r'\b\d+\b', type_of_field)[0])
        #                 if chars_int > 36:
        #                     for c in db_session.query(cls).all():
        #                         persent = int(100 * int(elem_count)/int(quantity))
        #                         elem_count -= 1
        #                         original_field = getattr(c, stripped_key)
        #                         modify_field = original_field + ' '
        #                         update_search_table(target=c)
        #                         if persent >= 0 and persent not in percents:
        #                             percents.append(persent)
        #                             percent_to_str += '='
        #                             print(percent_to_str+'>', str(persent-100).replace('-', '')+'%')
        #                     break
        #             except Exception as e:
        #                 pass
        # execute_time = datetime.datetime.now()-time
        # print('Updated successfully')
        # print('Execution time: {time}'.format(time=execute_time))
        # db_session.commit()
