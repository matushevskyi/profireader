"""A simple example of how to access the Google Analytics API."""

from profapp.models.portal import Portal
import argparse
from flask import g
import re
from profapp import utils

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

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
                 reader_plan='Anonymous', company_id='__NA__',
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
    account = None

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

        accounts = self.service.management().accounts().list().execute()
        if accounts.get('items'):
            # Get the first Google Analytics account.
            self.account = accounts.get('items')[0]

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

    def get_web_properties(self):
        return self.service.management().webproperties().list(accountId=self.account['id']).execute().get('items')

    def get_web_property(self, web_property_id):
        return utils.find_by_id(self.get_web_properties(), web_property_id)

    def get_view(self, view_id):
        return utils.find_by_id(self.get_views(), view_id)

    def get_views(self, web_peroperty):
        return self.service.management().profiles().list(accountId=self.account['id'],
                                                         webPropertyId=web_peroperty['id']).execute().get('items')

    @staticmethod
    def websiteUrl(host):
        return 'https://' + host

    def create_web_property(self, host):
        return self.service.management().webproperties().insert(
            accountId=self.account['id'],
            body={'websiteUrl': self.websiteUrl(host),
                  'name': 'Analytics for ' + host}).execute()

    def create_view(self, web_peroperty, name='View'):
        return self.service.management().profiles().insert(
            accountId=self.account['id'],
            webPropertyId=web_peroperty['id'],
            body={'name': name}).execute()

    def create_custom_dimensions_and_metrics(self, web_property_id):
        custom_dimensions = {name: self.service.management().customDimensions().insert(
            accountId=self.account['id'],
            webPropertyId=web_property_id,
            body={
                'name': name,
                'scope': 'HIT',
                'active': True
            }
        ).execute()['index'] for name in CUSTOM_DIMENSION}
        custom_metrics = {name: self.service.management().customMetrics().insert(
            accountId=self.account['id'],
            webPropertyId=web_property_id,
            body={
                'name': name,
                'scope': 'HIT',
                'type': 'CURRENCY',
                'active': True
            }
        ).execute()['index'] for name in CUSTOM_METRIC}
        return custom_dimensions, custom_metrics

    def update_host_for_property(self, web_property_id, new_host):
        web_property = self.get_web_property(web_property_id)
        if web_property['websiteUrl'] == self.websiteUrl(new_host):
            return False
        return self.service.management().webproperties().patch(
            accountId=self.account['id'],
            webPropertyId=web_property_id,
            body={
                'websiteUrl': self.websiteUrl(new_host),
                'name': 'Analytics for ' + new_host
            }
        ).execute()

    def create_web_property_and_view(self, host, name=None):
        web_property_created = self.create_web_property(host)
        view_created = self.create_view(web_property_created, ('View for ' + host) if name is None else name)
        return web_property_created['id'], view_created['id']



        # def get_results(self, profile_id):
        #     # Use the Analytics Service Object to query the Core Reporting API
        #     # for the number of sessions within the past seven days.
        #     return service.data().ga().get(
        #         ids='ga:' + profile_id,
        #         start_date='7daysAgo',
        #         end_date='today',
        #         metrics='ga:sessions').execute()



        # def get_first_profile_id(self):
        #     # Use the Analytics service object to get the first profile id.
        #
        #     # Get a list of all Google Analytics accounts for this user
        #     # accountsSummaries = service.management().accountSummaries().list().execute()
        #     accounts = service.management().accounts().list().execute()
        #
        #     if accounts.get('items'):
        #         # Get the first Google Analytics account.
        #         account = accounts.get('items')[0].get('id')
        #
        #         # Get a list of all the properties for the first account.
        #         properties = service.management().webproperties().list(
        #             accountId=account).execute()
        #
        #         if properties.get('items'):
        #             # Get the first property id.
        #             property = properties.get('items')[0].get('id')
        #
        #             # Get a list of all views (profiles) for the first property.
        #             profiles = service.management().profiles().list(
        #                 accountId=account,
        #                 webPropertyId=property).execute()
        #
        #             if profiles.get('items'):
        #                 # return the first view (profile) id.
        #                 return profiles.get('items')[0].get('id')
        #
        #     return None


def main():
    from profapp import create_app, prepare_connections

    parser = argparse.ArgumentParser(description='send greetings message')
    parser.add_argument("--create_for_portal_host")
    args = parser.parse_args()

    app = create_app(apptype='profi', config='config.CommandLineConfig')
    with app.app_context():
        prepare_connections(app)(echo=True)
        service = get_pr_service()
        account = get_account(service)
        if args.create_for_portal_host:
            portal = g.db.query(Portal).filter(Portal.host == args.create_for_portal_host).one()
            web_peroperties = get_web_properties(service, account)
            for web_peroperty in web_peroperties:
                if re.sub('^https?://', '', web_peroperty['websiteUrl']) == portal.host:
                    create_view(service, account, web_peroperty)
                    raise Exception('we already have web_property(id={}) for host={}'.
                                    format(web_peroperty['id'], portal.host))

            create_web_property(portal.host, service, account)
            web_peroperties = get_web_properties(service, account)
            web_property_just_created = None
            for web_peroperty in web_peroperties:
                if re.sub('^https?://', '', web_peroperty['websiteUrl']) == portal.host:
                    web_property_just_created = web_peroperty
            if not web_property_just_created:
                raise Exception('cant find just created web_property for portal={}'.format(portal.host))
            create_view(service, account, web_property_just_created)

            # http: // prominfo.com.ua.borshch.m.ntaxa.com /


            # profile = get_first_profile_id(service)
            # get_web_properties(service)
            # print_results(get_results(service, profile))

# if __name__ == '__main__':
#     main()
#
