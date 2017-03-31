import sys
sys.path.append('..')

from oauth2client.service_account import ServiceAccountCredentials
from profapp import create_app, prepare_connections
from profapp.models.config import Config
from flask import g


app = create_app(apptype='profi', config='config.CommandLineConfig')
with app.app_context():
    prepare_connections(app)(echo=True)
    # The scope for the OAuth2 request.
    SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
    # The location of the key file with the key data.
    KEY_FILEPATH = '../scrt/Profireader_project_google_service_account_key.json'


    # Defines a method to get an access token from the ServiceAccount object.
    def get_access_token():
        return ServiceAccountCredentials.from_json_keyfile_name(
            KEY_FILEPATH, SCOPE).get_access_token().access_token


    token = Config.get('access_token_for_analytics')
    token.value = get_access_token()
    token.save()
    g.db.commit()

