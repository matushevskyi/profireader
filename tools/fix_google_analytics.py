import sys

sys.path.append('..')

import os
from profapp.models.portal import Portal
from profapp.models.third.google_analytics_management import GoogleAnalyticsManagement
from flask import g, url_for

from profapp import create_app, prepare_connections, utils
import argparse


app = create_app(apptype='fix_google_analytics', config='config.CommandLineConfig')

try:
    if __name__ == '__main__':

        parser = argparse.ArgumentParser(description='activate requested (and confirmed) plans')
        args = parser.parse_args()


        with app.app_context():
            prepare_connections(app, echo=False)()
            os.chdir("..")
            portals = g.db.query(Portal).all()
            ga = GoogleAnalyticsManagement()

            app.log.info("Checking ga")
            app.log.info("%s ga accounts found" % (len(ga.accounts),))
            for account in ga.accounts:
                app.log.info('checking google analytics account (id={}, name={})'.format(account['id'], account['name']))
                web_properties = ga.get_web_properties(account['id'])
                app.log.info("%s web_properties found" % (len(web_properties),))
                for wp in web_properties:
                    app.log.info('checking ga web_property (id={}, name={})'.format(wp['id'], wp['name']))
                    if not g.db.query(Portal).filter(Portal.google_analytics_web_property_id == wp['id']).first():
                        pass
                    # !!    g.log('fix_google_analytics', 'deleting ga web_property (id, name)', wp['id'], wp['name'])

            app.log.info("Checking portals")
            app.log.info("%s portals found" % (len(portals),))
            for portal in portals:
                app.log.info('checking google analytics for (id={}, host={})'.format(portal.id, portal.host))

                try:
                    portal.save()
                # g.db.commit()

                except Exception as e:
                    app.log.error(e)
                    raise e

except Exception as e:
    app.log.critical(e)
    raise e
