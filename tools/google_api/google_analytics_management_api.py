"""A simple example of how to access the Google Analytics API."""
import sys
sys.path.append('../..')

from profapp.models.portal import Portal
import argparse
from flask import g
import re

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools


def get_service(api_name, api_version, scope, key_file_location,
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


def get_account(service):
    accounts = service.management().accounts().list().execute()
    if accounts.get('items'):
        # Get the first Google Analytics account.
        account = accounts.get('items')[0]
        return account if account else None
    return None


def get_web_properties(service, account=None):
    account = account if account else get_account(service)
    web_properties = service.management().webproperties().list(accountId=account['id']).execute().get('items')
    return web_properties


def create_web_property(host, service, account=None):
    account = account if account else get_account(service)

    service.management().webproperties().insert(
        accountId=account['id'],
        body={'websiteUrl': 'https://' + host, 'name': 'Analytics for ' + host}).execute()


def create_view(service, account, web_peroperty):
    account = account if account else get_account(service)

    service.management().profiles().insert(
        accountId=account['id'],
        webPropertyId=web_peroperty['id'],
        body={
            'name': 'View'
        }).execute()


def get_first_profile_id(service):
    # Use the Analytics service object to get the first profile id.

    # Get a list of all Google Analytics accounts for this user
    # accountsSummaries = service.management().accountSummaries().list().execute()
    accounts = service.management().accounts().list().execute()

    if accounts.get('items'):
        # Get the first Google Analytics account.
        account = accounts.get('items')[0].get('id')

        # Get a list of all the properties for the first account.
        properties = service.management().webproperties().list(
            accountId=account).execute()

        if properties.get('items'):
            # Get the first property id.
            property = properties.get('items')[0].get('id')

            # Get a list of all views (profiles) for the first property.
            profiles = service.management().profiles().list(
                accountId=account,
                webPropertyId=property).execute()

            if profiles.get('items'):
                # return the first view (profile) id.
                return profiles.get('items')[0].get('id')

    return None


def get_results(service, profile_id):
    # Use the Analytics Service Object to query the Core Reporting API
    # for the number of sessions within the past seven days.
    return service.data().ga().get(
        ids='ga:' + profile_id,
        start_date='7daysAgo',
        end_date='today',
        metrics='ga:sessions').execute()


def print_results(results):
    # Print data nicely for the user.
    if results:
        print('View (Profile): %s' % results.get('profileInfo').get('profileName'))
        # print
        # 'Total Sessions: %s' % results.get('rows')[0][0]

    else:
        print
        'No results found'


def get_pr_service():
    # Define the auth scopes to request.
    scope = ['https://www.googleapis.com/auth/analytics.readonly', 'https://www.googleapis.com/auth/analytics.edit']

    # Use the developer console and replace the values with your
    # service account email and relative location of your key file.
    service_account_email = '892582243019-compute@developer.gserviceaccount.com'
    key_file_location = '../../scrt/Profireader analytics-1fe3311c276b.p12'

    # Authenticate and construct service.
    service = get_service('analytics', 'v3', scope, key_file_location, service_account_email)
    return service


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


if __name__ == '__main__':
    main()
