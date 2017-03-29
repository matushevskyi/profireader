import sys

sys.path.append('..')

import os
from profapp.models.portal import Portal
from profapp.models.third.google_analytics_management import GoogleAnalyticsManagement, CUSTOM_DIMENSION, CUSTOM_METRIC
from flask import g, url_for

from profapp import create_app, prepare_connections, utils
import argparse

app = create_app(apptype='check_google_analytics', config='config.CommandLineConfig')

try:
    if __name__ == '__main__':

        parser = argparse.ArgumentParser(description='activate requested (and confirmed) plans')
        args = parser.parse_args()

        with app.app_context():
            prepare_connections(app, echo=False)()
            os.chdir("..")
            portals = g.db.query(Portal).all()
            ga = GoogleAnalyticsManagement()

            app.log.info("Start checking ga accounts/properties/views and portal (and theirs isomorphism)")

            app.log.debug("Checking portals")
            app.log.debug("%s portals found" % (len(portals),))
            for portal in portals:
                # if portal.status != Portal.STATUSES['PORTAL_ACTIVE']:
                #     continue
                app.log.info('checking google analytics for portal=(id={}, host={})'.format(portal.id, portal.host))
                portal_dict = portal.get_client_side_dict(fields='id,host,name')

                account = ga.get_account(portal.google_analytics_account_id)
                wp = ga.get_web_property(portal.google_analytics_account_id, portal.google_analytics_web_property_id)
                if not account or not wp:
                    app.log.error(
                        'Not existing account({}) or web_property({}). Recreating property/view'.format(account, wp),
                        **app.log.extra(portal=portal_dict, account=account, web_property=wp))
                    portal.setup_google_analytics(force_recreate=True)
                else:
                    if wp['name'] != ('Analytics for ' + portal.host) or wp['websiteUrl'] != ga.websiteUrl(
                            portal.host):
                        app.log.error('Wrong name or websiteUrl for analytics. Changing to proper name',
                                      **app.log.extra(account=account, web_property=wp, portal=portal_dict))
                        ga.update_host_for_property(account['id'], wp['id'], portal.host)
                    view = ga.get_view(account['id'], wp['id'], portal.google_analytics_view_id)
                    if not view:
                        app.log.error(
                            'cant find view={} (returned from ga = {}) for portal={},{}. Creating view'.format(
                                portal.google_analytics_view_id, view, portal.id, portal.host),
                            **app.log.extra(portal=portal_dict, account=account, web_property=wp))
                        view_created = ga.create_view(portal.google_analytics_account_id, wp, 'View for ' + portal.host)
                        portal.google_analytics_view_id = view_created['id']
                        app.log.error(
                            'Created view={} for portal={},{}'.format(view_created['id'], portal.id, portal.host),
                            **app.log.extra(portal=portal_dict, view=view_created, account=account, web_property=wp))

                    custom_dimensions, custom_metrics = ga.get_custom_dimensions_and_metrics(account['id'], wp['id'])

                    for cd in CUSTOM_DIMENSION:
                        exist_in_ga = utils.find_by_keys(custom_dimensions, cd, 'name')
                        exist_in_portal = portal.google_analytics_dimensions.get(cd, None)

                        if not exist_in_ga or not exist_in_portal or \
                                not exist_in_ga['index'] == exist_in_portal:
                            if not exist_in_ga and not exist_in_portal:
                                app.log.error(
                                    'custom dimension={} does not exist in ga nor portal={},{} creating'.
                                        format(cd, portal.id, portal.host),
                                    **app.log.extra(portal=portal_dict, account=account, web_property=wp))

                                portal.google_analytics_dimensions[cd] = ga.create_custom_dimension(
                                    account_id=account['id'], web_property_id=wp['id'], dimension_name=cd)
                            else:
                                app.log.critical(
                                    'something wrong with custom dimension {}, at ga we have={}, at portal we have={}'.
                                        format(cd, exist_in_ga, exist_in_portal),
                                    **app.log.extra(portal=portal_dict, account=account, web_property=wp))

                    for cm in CUSTOM_METRIC:
                        exist_in_ga = utils.find_by_keys(custom_metrics, cm, 'name')
                        exist_in_portal = portal.google_analytics_metrics.get(cm, None)

                        if not exist_in_ga or not exist_in_portal or \
                                not exist_in_ga['index'] == exist_in_portal:
                            if not exist_in_ga and not exist_in_portal:
                                app.log.error(
                                    'custom metric={} does not exist in ga nor portal={},{} creating'.
                                        format(cm, portal.id, portal.host),
                                    **app.log.extra(portal=portal_dict, account=account, web_property=wp))

                                portal.google_analytics_metrics[cm] = ga.create_custom_metric(
                                    account_id=account['id'], web_property_id=wp['id'], dimension_name=cm)
                            else:
                                app.log.critical(
                                    'something wrong with custom metric {}, at ga we have={}, at portal we have={}'.
                                        format(cm, exist_in_ga, exist_in_portal),
                                    **app.log.extra(portal=portal_dict, account=account, web_property=wp))

                try:
                    portal.save()
                    g.db.commit()

                except Exception as e:
                    app.log.error(e)
                    app.log.critical('Error processing portal={}, {}'.format(portal.id, portal.host),
                                     **app.log.extra(portal=portal_dict))

                    # app.log.debug("Checking ga accounts")
                    # app.log.debug("%s ga accounts found" % (len(ga.accounts),))
                    # for account in ga.accounts:
                    #     app.log.debug(
                    #         'checking google analytics account (id={}, name={})'.format(account['id'], account['name']))
                    #     web_properties = ga.get_web_properties(account['id'])
                    #     app.log.debug("%s web_properties found" % (len(web_properties),))
                    #     for wp in web_properties:
                    #         app.log.debug('checking ga web_property (id={}, name={})'.format(wp['id'], wp['name']))
                    #         portal = g.db.query(Portal).filter(Portal.google_analytics_web_property_id == wp['id']).first()
                    #         if not portal:
                    #             app.log.error(
                    #                 'Exist web property that is not attached to any portal. '
                    #                 'Google analytics management API have no delete method for web properties. '
                    #                 'You have to delete it manually', **app.log.extra(account=account, web_property=wp))
                    #         views = ga.get_views(account['id'], wp['id'])
                    #         for v in views:
                    #             if v['id'] != portal.google_analytics_view_id:
                    #                 app.log.error('Unknown view in property={}. ga returns view={} and '
                    #                               'Portal refer to view with id={}'.
                    #                               format(wp['id'], v['id'], portal.google_analytics_view_id),
                    #                               **app.log.extra(account=account, web_property=wp, view=v))
                    #             ga.delete_view(account['id'], wp['id'], v['id'])


except Exception as e:
    app.log.critical(e)
    raise e
