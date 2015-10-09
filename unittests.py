from profapp import create_app
from flask import g
# from cit.db import db
from unittest import TestCase as Base
# import init_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import drop_database
from sqlalchemy import create_engine
from config import database_uri, Config, TestingConfig
import sqlalchemy.exc as sqlalchemy_exc
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT,\
    ISOLATION_LEVEL_READ_COMMITTED
import json

engine = create_engine(database_uri(Config.host, Config.username,
                                    Config.password, 'postgres'))


class TestCase(Base):
    app = None

    @classmethod
    def setUpClass(cls):
        # cls.app = create_app(config='config.TestingConfig')
        cls.app = create_app(host=args.host, front=args.front, config='config.TestingConfig')
        cls.client = cls.app.test_client()
        cls._ctx = cls.app.test_request_context()
        cls._ctx.push()
        session = sessionmaker(bind=engine)()

    @classmethod
    def tearDownClass(cls):
        g.db.close()
        g.db.remove()
        message = 'All tests has been run. '
        print(message)

    def setUp(self):
        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def tearDown(self):
        g.db.rollback()
        g.db.close()
        self._ctx.pop()


class TestModel(TestCase):
    def test_add_comment_unauth_user(self):
        # comment = dict(issue_id=1, msg='test test')
        #
        # response = self.client.post('/comments/', data=comment)
        #
        # message_init = 'A problem with adding comment by unauthorised user.\n'
        #
        # message = message_init + \
        #     "response.status_code isn't equal to 401."
        # TestCase.assertEqual(self, response.status_code, 401, msg=message)
        #
        # message = message_init + \
        #     "response.data doesn't contain message 'Permission denied'."
        # TestCase.assertIn(self, 'Permission denied',
        #                   response.data, msg=message)
        return True

    def test_add_comment_auth_user_1(self):
        # user_id = 2  # this user doesn't have superuser rights
        # issue_id = 1
        # with self.client as c:
        #     with c.session_transaction() as sess:
        #         sess['user_id'] = user_id
        #     comment = dict(issue_id=issue_id, msg='test test')
        #     response = c.post('/comments/', data=comment)
        #     with c.session_transaction() as sess:
        #         sess.pop('user_id', None)
        #
        # response_in_json = json.loads(response.data)
        # comment_id = response_in_json['id']
        # comment_from_db = Comment.query.filter_by(id=comment_id).first()
        #
        # message = 'A problem with adding comment by authorised user.\n' + \
        #     "response.status_code isn't equal to 201."
        # TestCase.assertEqual(self, response.status_code, 201, msg=message)
        #
        # message = 'A problem with adding comment by authorised user to DB.'
        # expr = (str(comment['issue_id']) == comment_from_db.issue_id) and\
        #        (comment['msg'] == comment_from_db.message)
        # TestCase.assertTrue(self, expr, msg=message)
        return True


if __name__ == "__main__":
    import unittest
    import argparse

    parser = argparse.ArgumentParser()
    # parser = argparse.ArgumentParser(prog='unittests')
    parser.add_argument("--host", help="host", default='profi.ntaxa.com')
    parser.add_argument("--port", help="port", default='8080', type=int)
    parser.add_argument("--front", help="frontend", default='n')
    args = parser.parse_args()

    # unittest.main(host='0.0.0.0', port=args.port, debug=False)
    # --host=profi.ntaxa.com --port=8080 --front=n
    unittest.main()
