from config import Config
import httplib2
from flask import session
from oauth2client import client
from oauth2client.client import Credentials
from urllib import request as req
from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column
from .pr_base import Base, PRBase
from tools.db_utils import db
from ..controllers.errors import TooManyCredentialsInDb


class GoogleToken(Base, PRBase):
    __tablename__ = 'google_token'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    credentials = Column(TABLE_TYPES['credentials'], nullable=False)

    def __init__(self, credentials=None):
        super(GoogleToken, self).__init__()
        self.credentials = credentials

    @staticmethod
    def check_credentials_exist():
        """ Method check rather credentials is exist in db. Can be only one credentials in db.
         kind should be update, playlist
         If None you should to redirect admin to google auth page.
         If >1 some think is wrong . Raise exception"""
        try:
            credentials = db(GoogleToken).count()
            if credentials < 2:
                return credentials
            else:
                raise TooManyCredentialsInDb({'message': 'credentials >1'})
        except TooManyCredentialsInDb as e:
            e = e.args[0]
            print(e['message'])

    def save_credentials(self):
        """ This method save and return your credentials to/from db in json format.
         When you will need credentials you have to convert json to object(
         method: Credentials().new_from_json ) """
        google = GoogleAuthorize()
        flow = google.get_auth_code(ret_flow=True)
        credentials = flow.step2_exchange(session['auth_code'])
        self.credentials = credentials.to_json()
        self.save()
        return self.credentials

    @staticmethod
    def get_credentials_from_db():
        """ Static method. This method make query from db to get json-credentials, and
         then return object correct credentials which has been made from json.
          Set httplib2.debuglevel = 4 to debug http"""
        # httplib2.debuglevel = 4
        json = db(GoogleToken).one().credentials
        cred = Credentials()
        credentials = cred.new_from_json(json)
        http = httplib2.Http()
        http = credentials.authorize(http)
        credentials.refresh(http)
        session['access_token'] = credentials.access_token
        return credentials

    @staticmethod
    def get_authorize_http():
        """ Method which is helpful to get authorize http from your credentials.
         Can be used for make some service from google api """
        json = db(GoogleToken).first().credentials
        cred = Credentials()
        credentials = cred.new_from_json(json)
        http = httplib2.Http()
        http = credentials.authorize(http)
        return http

class GoogleAuthorize(object):
    """ This class can apply api_service name and api_version to build service which you want.
     Default youtube upload service. Method authorize return service with necessary token
     server-server . If you need to get token, use flask.session['credentials'] """

    __project_secret = Config.GOOGLE_API_SECRET_JSON

    def __init__(self, google_service_name=Config.YOUTUBE_API_SERVICE_NAME,
                 google_service_version=Config.YOUTUBE_API_VERSION,
                 scope=Config.YOUTUBE_API['SCOPE'],
                 redirect_uri=Config.YOUTUBE_API['UPLOAD']['REDIRECT_URI']):
        self.google_service_name = google_service_name
        self.google_service_version = google_service_version
        self.scope = scope
        self.redirect_uri = redirect_uri

    def get_auth_code(self, ret_flow=False):

        """ This method return link for google auth service if ret_flow parameter is not produced,
        else - return flow object. Helpful when you need to have code to make credentials """
        flow = client.flow_from_clientsecrets(self.__project_secret, self.scope,
                                              redirect_uri=self.redirect_uri)
        flow.params['access_type'] = 'offline'
        flow.params['approval_prompt'] = 'force'
        auth_uri = flow.step1_get_authorize_url()
        request_for_token = req.urlopen(auth_uri)
        url = request_for_token.geturl()
        return url if not ret_flow else flow

    @staticmethod
    def check_admins():
        """ This method check if current user is profireader admin. Return True or False.
         If you will change dg, you should to change id admins in db """
        return True if session.get('user_id') in Config.PROFIREADER_ADMINS else False

