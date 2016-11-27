import sys

sys.path.append('..')

from profapp.models.materials import Publication
from profapp.models.files import File
from profapp.models.users import User
from profapp.models.portal import Portal
from sqlalchemy import create_engine, event
from profapp.models.pr_base import Search
from profapp.constants.SEARCH import RELEVANCE
import re
from sqlalchemy.orm import scoped_session, sessionmaker
from config import ProductionDevelopmentConfig
import datetime
import sys

import os
import argparse


from os import listdir
from os.path import isfile, join

engine = create_engine(ProductionDevelopmentConfig.SQLALCHEMY_DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

parser = argparse.ArgumentParser()
parser.add_argument("vhostdir", help="directory with virtual host names")
parser.add_argument("--disable-inactive", help="disable inactive virtual hosts")
parser.add_argument("--apache-template", help="apache template file")
parser.add_argument("--skip-existing-vhost", help="do not create vhost conf file if exists")
parser.add_argument("--www-dir", help="directory with run.wsgi")
parser.add_argument("--force-existing-ssl", help="get ssl even if exists")


parser.add_argument("--template", help="template file")
args = parser.parse_args()

def disable_inactive_vhosts():
    print('disabling inactive virtual hosts')
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    pass 

def create_active_vhosts():
    
    all_portals = db_session.query(Portal).filter_by(status='ACTIVE')
    with open(args.apache_template, 'r') as content_file:
        template = content_file.read()

    # print(template)

    for portal in all_portals:
        destination_conf = args.vhostdir + '/' + portal.host + '-front.conf'
        if not args.skip_existing_vhost or not os.path.isfile(destination_conf):
            conf_file = re.sub(r'----domain----', portal.host, re.sub(r'----directory----', args.www_dir, template))
            if portal.aliases and portal.aliases != '':
                conf_file = re.sub(r'----aliases----', portal.aliases, conf_file)
            else:
                conf_file = re.sub(r'.*----aliases----.*', '', conf_file)
        
            with open(destination_conf, 'w') as host_file:
                host_file.write(conf_file)
        
        destination_ssl = '/etc/letsencrypt/live/' + portal.host
        if args.force_existing_ssl or not os.path.isdir(destination_ssl):
            retvalue = os.system("./get_ssl_for_domain.sh %s/letsencryptrequests/ %s %s" % (args.www_dir, portal.host, portal.aliases))

        # pass

#        retvalue = os.system("./get_ssl_for_domain.sh %s/letsencryptrequests/ %s %s" % (
#        '/home/oles/profireader', portal.host, portal.aliases))
#
#        with open('/etc/apache2/sites-enabled/' + portal.host + '.conf', 'w') as host_file:
#            host_file.write(conf_file)


if __name__ == '__main__':
    if args.disable_inactive:
        disable_inactive_vhosts()
    create_active_vhosts()

else:    
    all_portals = db_session.query(Portal).filter_by(status='ACTIVE')
    with open('../conf/front-wsgi-apache2.conf', 'r') as content_file:
        template = content_file.read()

    # print(template)

    for portal in all_portals:
        conf_file = re.sub(r'----domain----', portal.host, template)
        if portal.aliases and portal.aliases != '':
            conf_file = re.sub(r'----aliases----', portal.aliases, conf_file)
        else:
            conf_file = re.sub(r'.*----aliases----.*', '', conf_file)
        # pass

        retvalue = os.system("./get_ssl_for_domain.sh %s/letsencryptrequests/ %s %s" % (
        '/home/oles/profireader', portal.host, portal.aliases))

        with open('/etc/apache2/sites-enabled/' + portal.host + '.conf', 'w') as host_file:
            host_file.write(conf_file)



        # print(retvalue)
        # print(portal.aliases)
        # time = datetime.datetime.now()
        # elem_count = 0
        # quantity = 0
        # percent_to_str = ''
        # percents = []
        # answer = input(
        #     "Are you sure? \n If you'l start this process, your database will be overwritten. "
        #     "Yes|No")
        # prompt = True if answer in ['yes', 'Yes', 'y', 'YES', 'tak'] else False
        # if not prompt:
        #     exit('The script has been closed.')
        # for cls in classes:
        #     if hasattr(cls, 'search_fields'):
        #         elem_count += db_session.query(cls).count()
        #         quantity = elem_count
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
