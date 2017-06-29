"""A simple example of how to access the Google Analytics API."""

from profapp.models.portal import Portal
import argparse
from flask import g
import re
from profapp import utils

# from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools
from time import sleep

CUSTOM_DIMENSION = {'page_type': 'page_type',
                    'publication_visibility': 'publication_visibility',
                    'publication_reached': 'publication_reached',
                    'company_id': 'company_id',
                    'reader_plan': 'reader_plan'}

CUSTOM_METRIC = {'income': 'income'}


class PortalAnalytics:
    page_type = ''
    publication_visibility = ''
    company_id = ''
    publication_reached = 'False'
    income = 0

    def __init__(self, page_type, publication_visibility='__NA__', publication_reached='__NA__',
                 reader_plan='__NA__', company_id='__NA__',
                 income=0):
        self.page_type = page_type
        self.publication_visibility = publication_visibility
        self.publication_reached = publication_reached
        self.reader_plan = reader_plan
        self.company_id = company_id
        self.income = income


class GoogleAnalyticsReport:
    def __init__(self):
        # Define the auth scopes to request.
        scope = ['https://www.googleapis.com/auth/analytics.readonly']

        # Authenticate and construct service.
        self.service = self._get_service('analytics', 'v4', scope)

    def _get_service(self, api_name, api_version, scope):
        # Use the developer console and replace the values with your
        # service account email and relative location of your key file.
        service_account_email = '892582243019-compute@developer.gserviceaccount.com'
        key_file_location = 'scrt/Profireader analytics-1fe3311c276b.p12'
        DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest')

        """Get a service that communicates to a Google API.

        Args:
          api_name: The name of the api to connect to.
          api_version: The api version to connect to.
          scope: A list auth scopes to authorize for the application.
          key_file_location: The path to a valid service account p12 key file.
          service_account_email: The service account email address.

        Returns:
          A service that is connected to the specified API.
        """

        credentials = ServiceAccountCredentials.from_p12_keyfile(
            service_account_email, key_file_location, scopes=scope)

        http = credentials.authorize(httplib2.Http())

        # Build the service object.
        service = build('analytics', 'v4', http=http, discoveryServiceUrl=DISCOVERY_URI)

        return service


class GoogleAnalyticsManagement:
    service = None
    accounts = None

    def _s(self, retval=None, seconds=0.1):
        sleep(seconds)
        return retval

    def __init__(self):
        # Define the auth scopes to request.
        scope = ['https://www.googleapis.com/auth/analytics.readonly',
                 'https://www.googleapis.com/auth/analytics.edit']

        # Use the developer console and replace the values with your
        # service account email and relative location of your key file.
        service_account_email = '892582243019-compute@developer.gserviceaccount.com'
        key_file_location = 'scrt/Profireader analytics-1fe3311c276b.p12'

        # Authenticate and construct service.
        self.service = self._get_service('analytics', 'v3', scope, key_file_location, service_account_email)

        self.accounts = sorted(self.service.management().accounts().list().execute().get('items'),
                               key=lambda x: x['created'])

    def _get_service(self, api_name, api_version, scope, key_file_location,
                     service_account_email):
        """Get a service that communicates to a Google API.

        Args:
          api_name: The name of the api to connect to.
          api_version: The api version to connect to.
          scope: A list auth scopes to authorize for the application.
          key_file_location: The path to a valid service account p12 key file.
          service_account_email: The service account email address.

        Returns:
          A service that is connected to the specified API.
        """

        credentials = ServiceAccountCredentials.from_p12_keyfile(
            service_account_email, key_file_location, scopes=scope)

        http = credentials.authorize(httplib2.Http())

        # Build the service object.
        service = build(api_name, api_version, http=http)

        return service

    def get_account(self, account_id):
        if not account_id:
            return None
        for a in self.accounts:
            if a['id'] == account_id:
                return a
        return None

    def get_web_properties(self, account_id) -> list:
        if not account_id:
            return []
        return self.service.management().webproperties().list(accountId=account_id).execute().get('items')

    def get_web_property(self, account_id, web_property_id):
        if not account_id or not web_property_id:
            return None
        return utils.find_by_id(self.get_web_properties(account_id), web_property_id)

    def get_view(self, account_id, web_peroperty_id, view_id):
        if not web_peroperty_id or not view_id:
            # print('retutning none for web_peroperty_id={}, view_id{}'.format(web_peroperty_id, view_id))
            return None
        return utils.find_by_id(self.get_views(account_id, web_peroperty_id), view_id)

    def get_views(self, account_id, web_peroperty_id):
        if not account_id or not web_peroperty_id:
            return []
        return self.service.management().profiles().list(accountId=account_id,
                                                         webPropertyId=web_peroperty_id).execute().get('items')

    @staticmethod
    def websiteUrl(host):
        return 'https://' + host

    def create_web_property(self, account_id, host):
        return self._s(self.service.management().webproperties().insert(
            accountId=account_id, body={'websiteUrl': self.websiteUrl(host),
                                        'name': 'Property for ' + host}).execute())

    # there is no delete functions for web property in ga management api :(
    def delete_web_property(self, account_id, web_property_id):
        pass

    def delete_view(self, account_id, web_property_id, view_id):
        return self._s(
            self.service.management().profiles().delete(
                accountId=account_id,
                webPropertyId=web_property_id,
                profileId=view_id).execute())

    def create_view(self, account_id, web_property, name='View'):
        return self._s(
            self.service.management().profiles().insert(accountId=account_id,
                                                        webPropertyId=web_property['id'],
                                                        body={'name': name}).execute())

    def create_custom_dimension(self, account_id, web_property_id, dimension_name):
        return self._s(self.service.management().customDimensions().insert(
            accountId=account_id, webPropertyId=web_property_id, body={
                'name': dimension_name,
                'scope': 'HIT',
                'active': True
            }).execute()['index'])

    def create_custom_metric(self, account_id, web_property_id, metric_name):
        return self._s(self.service.management().customMetrics().insert(
            accountId=account_id, webPropertyId=web_property_id, body={
                'name': metric_name,
                'scope': 'HIT',
                'type': 'CURRENCY',
                'active': True
            }).execute()['index'])

    def create_custom_dimensions_and_metrics(self, account_id, web_property_id):
        custom_dimensions = {name: self.create_custom_dimension(account_id, web_property_id, name)
                             for name in CUSTOM_DIMENSION}
        custom_metrics = {name: self.create_custom_metric(account_id, web_property_id, name)
                          for name in CUSTOM_METRIC}
        return custom_dimensions, custom_metrics

    def get_custom_dimensions_and_metrics(self, account_id, web_property_id):
        custom_dimensions = self.service.management().customDimensions().list(
            accountId=account_id, webPropertyId=web_property_id).execute().get('items')
        custom_metrics = self.service.management().customMetrics().list(
            accountId=account_id, webPropertyId=web_property_id).execute().get('items')
        return [utils.dict_pluck(cd, 'index', 'id', 'name', 'scope') for cd in custom_dimensions], \
               [utils.dict_pluck(cm, 'index', 'id', 'name', 'scope', 'type') for cm in custom_metrics]

    def update_host_for_property(self, account_id, web_property_id, new_host):
        web_property = self.get_web_property(account_id, web_property_id)
        if web_property['websiteUrl'] == self.websiteUrl(new_host) and web_property['name'] == ('View for ' + new_host):
            return False
        return self._s(
            self.service.management().webproperties().patch(accountId=account_id, webPropertyId=web_property_id,
                                                            body={
                                                                'websiteUrl': self.websiteUrl(new_host),
                                                                'name': 'Property for ' + new_host
                                                            }).execute())

    def update_host_for_view(self, account_id, web_property_id, view_id, new_host):
        view = self.get_view(account_id, web_property_id, view_id)
        if view['websiteUrl'] == self.websiteUrl(new_host) and view['name'] == ('View for ' + new_host):
            return False
        return self._s(
            self.service.management().profiles().patch(accountId=account_id, webPropertyId=web_property_id,
                                                            profileId=view_id,
                                                            body={
                                                                'websiteUrl': self.websiteUrl(new_host),
                                                                'name': 'View for ' + new_host
                                                            }).execute())

    def create_web_property_and_view(self, host, name=None):
        for ac in self.accounts:
            if len(self.get_web_properties(ac['id'])) < 49:
                web_property_created = self.create_web_property(ac['id'], host)
                view_created = self.create_view(ac['id'], web_property_created,
                                                ('View for ' + host) if name is None else name)
                return ac['id'], web_property_created['id'], view_created['id']
        raise Exception('no available google analytics account. Please create more in ga control panel')

# def main():
#     from profapp import create_app, prepare_connections
#
#     parser = argparse.ArgumentParser(description='send greetings message')
#     parser.add_argument("--create_for_portal_host")
#     args = parser.parse_args()
#
#     app = create_app(apptype='profi', config='config.CommandLineConfig')
#     with app.app_context():
#         prepare_connections(app)(echo=True)
#         service = get_pr_service()
#         account = get_account(service)
#         if args.create_for_portal_host:
#             portal = g.db.query(Portal).filter(Portal.host == args.create_for_portal_host).one()
#             web_peroperties = get_web_properties(service, account)
#             for web_peroperty in web_peroperties:
#                 if re.sub('^https?://', '', web_peroperty['websiteUrl']) == portal.host:
#                     create_view(service, account, web_peroperty)
#                     raise Exception('we already have web_property(id={}) for host={}'.
#                                     format(web_peroperty['id'], portal.host))
#
#             create_web_property(portal.host, service, account)
#             web_peroperties = get_web_properties(service, account)
#             web_property_just_created = None
#             for web_peroperty in web_peroperties:
#                 if re.sub('^https?://', '', web_peroperty['websiteUrl']) == portal.host:
#                     web_property_just_created = web_peroperty
#             if not web_property_just_created:
#                 raise Exception('cant find just created web_property for portal={}'.format(portal.host))
#             create_view(service, account, web_property_just_created)
#
#             # http: // prominfo.com.ua.borshch.m.ntaxa.com /
#
#
#             # profile = get_first_profile_id(service)
#             # get_web_properties(service)
#             # print_results(get_results(service, profile))
#
# # if __name__ == '__main__':
# #     main()
# #
