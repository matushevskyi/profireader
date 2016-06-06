from elasticsearch import Elasticsearch
from .articles import ArticlePortalDivision
from .portal import Portal, PortalDivision
from .tag import TagPublication
from .pr_base import PRBase
import requests
import json
import math
from .. import utils
from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker
from config import ProductionDevelopmentConfig

elastic_host = 'http://elastic.profi:9200'

engine = create_engine(ProductionDevelopmentConfig.SQLALCHEMY_DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))


class PRElastic:
    uri = ''

    def __init__(self, host):
        self.uri = host
        pass

    @staticmethod
    def get_structure():

        return [
            PRElasticIndex('articles').add_document_type(
                PRElasticDocumentType('articles',
                                      elastic2alchemy=lambda id, d: ArticlePortalDivision.get(id),
                                      all_alchemys=lambda: {a.id: [a, a.portal, a.division] for a in
                                                            db_session.query(
                                                                ArticlePortalDivision).all()}
                                      ).add_document_field(
                    *[
                        PRElasticField('title', ftype='string', setter=lambda a, p, d: a.title, boost=10),
                        PRElasticField('subtitle', ftype='string', setter=lambda a, p, d: a.subtitle, boost=4),
                        PRElasticField('keywords', ftype='string', setter=lambda a, p, d: a.keywords, boost=3),
                        PRElasticField('short', ftype='string', setter=lambda a, p, d: a.short, boost=2),
                        PRElasticField('long', ftype='string', setter=lambda a, p, d: a.long),
                        PRElasticField('id', ftype='string', analyzed=False, setter=lambda a, p, d: a.id),
                        PRElasticField('tags', ftype='string', analyzed=False,
                                       setter=lambda a, p, d: ' '.join([t.text for t in a.tags])),
                        PRElasticField('user', ftype='string', analyzed=False),
                        PRElasticField('user_id', ftype='string', analyzed=False),
                        PRElasticField('portal', ftype='string', setter=lambda a, p, d: p.name),
                        PRElasticField('portal_id', ftype='string', analyzed=False, setter=lambda a, p, d: p.id),
                        PRElasticField('division', ftype='string', setter=lambda a, p, d: d.name),
                        PRElasticField('portal_division_id', ftype='string', analyzed=False,
                                       setter=lambda a, p, d: a.division.id)
                    ]
                )
            )
        ]

    @staticmethod
    def path(*args, params=None):
        return (elastic_host + '/' + '/'.join(args)) + '?' + \
               ('&'.join(["%s=%s" % (k, v) for k, v in params.items()]) if params else '')

    # def search(self, index, doc_type, filter = {}, search = {}):
    #     return (self.rq(path=self.path(index_name, document_type, id), req={}, method='PUT'), 1, 1)
    #     """Simple Elasticsearch Query"""
    #     query = json.dumps({
    #         "query": {
    #             "match": {
    #                 "content": term
    #             }
    #         }
    #     })
    #     response = requests.get(self.uri, data=query)
    #     results = json.loads(response.text)
    #
    #     return results

    @staticmethod
    def rq(path='', req='', method='GET'):
        print(method + ' - ' + path)
        print(req)
        if method == 'POST':
            response = requests.post(path, data=json.dumps(req))
        elif method == 'PUT':
            response = requests.put(path, data=json.dumps(req))
        elif method == 'DELETE':
            response = requests.delete(path, data=json.dumps(req))
        elif method == 'GET':
            response = requests.get(path, data=json.dumps(req))
        else:
            raise Exception("unknown method `" + method + '`')

        print(response.text)
        return json.loads(response.text)

    @staticmethod
    def search(index_name, document_type, filter={}, must={}, should={}, page=1, items_per_page=10):

        f = [{"term": {k: v}} for k, v in filter.items()]
        m = [{"multi_match": {'query': v, 'fields': list(k)}} for k, v in must.items()]
        s = [{"multi_match": {'query': v, 'fields': list(k)}} for k, v in should.items()]

        req = {"query": {"bool": {"filter": f, "must": m, "should": s}}}

        count = PRElastic.rq(path=PRElastic.path(index_name, document_type, '_count'),
                             req=req, method='GET')['count']

        pages = int(math.ceil(count / items_per_page))

        p = utils.putInRange(page, 1, pages)
        items = utils.putInRange(items_per_page, 1, 100)

        res = PRElastic.rq(path=PRElastic.path(index_name, document_type, '_search', params={'size': items,
                                                                                             'from': (p - 1) * items}),
                           req=req, method='GET')
        found = [h['_source'] for h in res['hits']['hits']]

        return (found, pages, p)


class PRElasticField:
    name = ''
    type = ''
    boost = ''
    setter = None

    def __init__(self, name, ftype='string', boost=1, analyzed=None, setter=lambda *args: ''):
        self.name = name
        self.type = ftype
        self.boost = boost
        self.analyzed = ('analyzed' if self.type == 'string' else 'not_analyzed') if analyzed is None else analyzed
        self.setter = setter

    def generate_mapping(self):
        return {
            "type": self.type,
            "index": 'analyzed' if self.analyzed is True else ('not_analyzed' if self.analyzed is False else
                                                               self.analyzed),
            "boost": self.boost
        }


class PRElasticDocumentType:
    name = ''
    document_fields = []
    class_dependent = {}
    all_alchemys = lambda: []

    def __init__(self, name, document_fields=[], class_dependent={}, all_alchemys=lambda: [], elastic2alchemy=
    lambda: None):
        self.name = name
        self.document_fields = document_fields
        self.class_dependent = class_dependent
        self.all_alchemys = all_alchemys
        self.elastic2alchemy = elastic2alchemy

    def add_document_field(self, *args):
        for a in args:
            self.document_fields.append(a)
        return self

    def generate_mapping(self):
        return {'properties': {f.name: f.generate_mapping() for f in self.document_fields}}

    def generate_document(self, *objects):
        return {f.name: f.setter(*objects) for f in self.document_fields}

    def add(self, index_name, document_type, id, document):
        return PRElastic.rq(path=PRElastic.path(index_name, document_type, id), req=document, method='PUT')

    def insert_all_documents(self, index_name):
        return {id: self.add(index_name, self.name, id, self.generate_document(*objects)) for id, objects in
                self.all_alchemys().items()}


class PRElasticIndex:
    name = ''
    document_types = []
    settings = {}

    def __init__(self, name, document_types=[]):
        self.document_types = document_types
        self.name = name

    def generate_mapping(self):
        return {d.name: d.generate_mapping() for d in self.document_types}
        # return document_mapping[field_name] = {
        #     "type": field_prop['type'] if field_prop['type'] else 'string',
        #     "index": 'analyzed' if field_prop['analyzed'] else 'not_analyzed',
        #     "boost": field_prop.get('boost', 1)
        # }

    def add_document_type(self, *args):
        for a in args:
            self.document_types.append(a)
        return self

    def create(self):
        return PRElastic.rq(path=PRElastic.path(self.name), req={
            "settings": self.settings,
            "mappings": self.generate_mapping()
        }, method='PUT')

    def delete(self):
        return PRElastic.rq(path=PRElastic.path(self.name), req={}, method='DELETE')

    def insert_all_documents(self):
        return [d.insert_all_documents(self.name) for d in self.document_types]

# def search_elastic(type, body):
#     es = Elasticsearch(hosts='elastic.profi')
#     return ([utils.merge_dicts(r['_source'], {'id': r['_id']}) for r in es.search(index='profireader',
#                                                                                   doc_type=type,
#                                                                                   body=body)['hits']['hits']], 10, 1)
