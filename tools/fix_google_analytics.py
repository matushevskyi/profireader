import sys

sys.path.append('..')

import os
from profapp.models.portal import Portal
from profapp.models.third.google_analytics_management import GoogleAnalyticsManagement
from flask import g, url_for

from sqlalchemy.sql import text, and_
from sqlalchemy import func

from profapp import create_app, prepare_connections, utils
import argparse
import datetime

import logging
from fluent import handler

custom_format = {
  'host': '%(hostname)s',
  'where': '%(module)s.%(funcName)s',
  'type': '%(levelname)s',
  'stack_trace': '%(exc_text)s'
}

logging.basicConfig(level=logging.INFO)
l = logging.getLogger('fluent.test')
h = handler.FluentHandler('app.follow', host='host', port=24224)
formatter = handler.FluentRecordFormatter(custom_format)
h.setFormatter(formatter)
l.addHandler(h)
l.info({
  'from': 'userA',
  'to': 'userB'
})
l.info('{"from": "userC", "to": "userD"}')
l.info("This log entry will be logged with the additional key: 'message'.")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='activate requested (and confirmed) plans')
    args = parser.parse_args()

    app = create_app(apptype='profi', config='config.CommandLineConfig')

    with app.app_context():

        prepare_connections(app, echo=False)()
        os.chdir("..")
        portals = g.db.query(Portal).all()
        ga = GoogleAnalyticsManagement()

        g.log('fix_google_analytics', "%s ga accounts found" % (len(ga.accounts),))
        for account in ga.accounts:
            g.log('fix_google_analytics', 'checking google analytics account (id, name)', account['id'], account['name'])
            web_properties = ga.get_web_properties(account['id'])
            g.log('fix_google_analytics', "%s web_properties found" % (len(web_properties),))
            for wp in web_properties:
                g.log('fix_google_analytics', 'checking ga web_property (id, name)', wp['id'], wp['name'])
                if not g.db.query(Portal).filter(Portal.google_analytics_web_property_id == wp['id']).first():
                    pass
                # !!    g.log('fix_google_analytics', 'deleting ga web_property (id, name)', wp['id'], wp['name'])


        g.log('fix_google_analytics', "%s portals found" % (len(portals),))
        for portal in portals:
            g.log('fix_google_analytics', 'checking google analytics for (id, host)', portal.id, portal.host)

            try:
                portal.save()
            # g.db.commit()

            except Exception as e:
                g.log(e)
                raise e
