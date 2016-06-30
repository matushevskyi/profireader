
import json
import math
from .. import utils
from utils.db_utils import db
from sqlalchemy import event

# engine = create_engine(ProductionDevelopmentConfig.SQLALCHEMY_DATABASE_URI)
# db_session = scoped_session(sessionmaker(autocommit=False,
#                                          autoflush=False,
#                                          bind=engine))

class PRElasticConnection:

    host = None

    def __init__(self, host):
        self.host = host



    def path(self, *args, params=None):
        return (self.host + '/' + '/'.join(args)) + '?' + \
               ('&'.join(["%s=%s" % (k, v) for k, v in params.items()]) if params else '')


    def rq(self, path='', req='', method='GET', returnstatusonly=False):
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
        elif method == 'HEAD':
            response = requests.head(path, data=json.dumps(req))
        else:
            raise Exception("unknown method `" + method + '`')
        if returnstatusonly:
            print('----------', response.status_code, '----------')
            return True if response.status_code == 200 else False
        else:
            print('++++++++++', response.text, '++++++++++')
            return json.loads(response.text)

    def index_exists(self, index_name):
        return self.rq(path=self.path(index_name), req={}, method='HEAD', returnstatusonly=True)

    def doctype_exists(self, index_name, doctype_name):
        ret = self.rq(path=self.path(index_name, '_mapping', doctype_name), req={}, method='GET')
        #          return True if len(ret.keys()) > 0 else False
        #     def doc_exists(self, indexname, doctype, id):
        #         return PRElastic.rq(path=PRElastic.path(indexname, doctype, id), req={}, method='HEAD', returnstatusonly=True)
        #
        #     def doc_delete(self, indexname, doctype, id):
        #         return PRElastic.rq(path=PRElastic.path(indexname, doctype, id), req={}, method='DELETE')
        #
        #     def doctype_exists(self, indexname, doctype):
        #          ret = PRElastic.rq(path=PRElastic.path(indexname, '_mapping', doctype), req={}, method='GET')
        #          return True if len(ret.keys()) > 0 else False


    def replace_document(self, index_name, document_type, id, document):
        return self.rq(path=self.path(index_name, document_type, id), req=document, method='PUT')


    def remove_index(self, index_name):
        return self.rq(path=self.path(index_name), req={}, method='DELETE')


    def search(self, index_name, document_type, sort=["_score"], filter=[], must=[], should=[], page=1, items_per_page=10):

        req = {
            "sort": sort,
            "query": {"bool": {"filter": filter, "must": must, "should": should}}}

        count = self.rq(path=self.path(index_name, document_type, '_count'),
                                       req=req, method='GET')['count']

        pages = int(math.ceil(count / items_per_page))

        p = utils.putInRange(page, 1, pages)
        p = 1 if p == 0 else p
        print(page, p, pages)
        items = utils.putInRange(items_per_page, 1, 100)

        res = self.rq(
            path=self.path(index_name, document_type, '_search', params={'size': items,
                                                                                        'from': (p - 1) * items}),
            req=req, method='GET')
        found = [h['_source'] for h in res['hits']['hits']]

        return (found, pages, p)

elasticsearch = PRElasticConnection('http://elastic.profi:9200')

class PRElasticDocument:

    elastic_cached_index_doctype = {}

    def elastic_get_fields(self):
        return None

    def elastic_get_document(self):
        return {k: v.setter() for k, v in self.elastic_get_fields().items()}

    def elastic_replace(self):
        self.create_doctype_if_not_exists()
        return elasticsearch.replace_document(self.elastic_get_index(),
                                                    self.elastic_get_doctype(),
                                                    self.elastic_get_id(),
                                                    self.elastic_get_document(),
                                                    )

    def create_index_if_not_exist(self):
        index_name = self.elastic_get_index()
        if index_name in self.elastic_cached_index_doctype:
            return True
        else:
            if elasticsearch.index_exists(index_name):
                self.elastic_cached_index_doctype[index_name] = {}
                return True

            ret = elasticsearch.rq(path=elasticsearch.path(index_name), req={"settings": {}}, method='PUT')
            if ret:
                print('created index:', index_name)
                self.elastic_cached_index_doctype[index_name] = {}
            return True if ret else False

    def create_doctype_if_not_exists(self):
        index_name = self.elastic_get_index()
        doctype_name = self.elastic_get_doctype()
        self.create_index_if_not_exist()
        if doctype_name in self.elastic_cached_index_doctype[index_name]:
            return True
        else:
            if elasticsearch.doctype_exists(index_name, doctype_name):
                self.elastic_cached_index_doctype[index_name][doctype_name] = True
                return True

            ret = elasticsearch.rq(path=elasticsearch.path(index_name, '_mapping', doctype_name),
                          req=self.elastic_doctype_mappintg(), method='PUT')
            if ret:
                print('created doctype:', index_name, doctype_name)
                self.elastic_cached_index_doctype[index_name][doctype_name] = True
            return True if ret else False

    def elastic_doctype_mappintg(self):
        return {'properties': {f_name: field.generate_mapping() for f_name, field in self.elastic_get_fields().items()}}

    @classmethod
    def elastic_remove_all_indexes(cls):
        pass

    @classmethod
    def elastic_get_all_documents(cls):
        return db(cls).all()

    @classmethod
    def elastic_reindex_all(cls):
        for o in cls.elastic_get_all_documents():
            o.elastic_replace()

    def elastic_get_index(self):
        return None

    def elastic_get_doctype(self):
        return None

    def elastic_get_id(self):
        return None



class PRElasticField:
    name = ''
    type = ''
    boost = ''
    setter = None

    def __init__(self, ftype='string', boost=1, analyzed=None, setter=lambda *args: ''):
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


        # import abc


        # class PRElasticDocumentType(metaclass = abc.ABCMeta):
        #
        #     cached_index_doctype = {}
        #
        #     def __init__(self):
        #         pass
        #
        #     def add_document_field(self, *args):
        #         for a in args:
        #             self.document_fields.append(a)
        #         return self
        #
        #     def generate_mapping(self):
        #         return {'properties': {f_name: field.generate_mapping() for f_name, field in self.get_all_fields().items()}}
        #
        #     @abc.abstractmethod
        #     def all_alchemys(self):
        #         pass
        #
        #     @abc.abstractmethod
        #     def alchemy2index(self, *alchemyobgects):
        #         pass
        #
        #     @abc.abstractmethod
        #     def alchemy2doctype(self, *alchemyobgects):
        #         pass
        #
        #     @abc.abstractmethod
        #     def delete_all_indexes(self):
        #         pass
        #
        #     @abc.abstractmethod
        #     def alchemy2id(self, *alchemyobgects):
        #         pass
        #
        #     def doc_exists(self, indexname, doctype, id):
        #         return PRElastic.rq(path=PRElastic.path(indexname, doctype, id), req={}, method='HEAD', returnstatusonly=True)
        #
        #     def doc_delete(self, indexname, doctype, id):
        #         return PRElastic.rq(path=PRElastic.path(indexname, doctype, id), req={}, method='DELETE')
        #
        #     def doctype_exists(self, indexname, doctype):
        #          ret = PRElastic.rq(path=PRElastic.path(indexname, '_mapping', doctype), req={}, method='GET')
        #          return True if len(ret.keys()) > 0 else False
        #
        #     def index_exists(self, indexname):
        #         return PRElastic.rq(path=PRElastic.path(indexname), req={}, method='HEAD', returnstatusonly=True)
        #
        #     def create_index_if_not_exist(self, *alchemyobgects):
        #         index_name = self.alchemy2index(*alchemyobgects)
        #         if index_name in self.cached_index_doctype:
        #             return True
        #         else:
        #             if self.index_exists(index_name):
        #                 self.cached_index_doctype[index_name] = {}
        #                 return True
        #
        #             ret = PRElastic.rq(path=PRElastic.path(index_name), req={"settings": {}}, method='PUT')
        #             if ret:
        #                 print('created index:', index_name)
        #                 self.cached_index_doctype[index_name] = {}
        #             return True if ret else False
        #
        #     def create_doctype_if_not_exists(self, *alchemyobgects):
        #         self.create_index_if_not_exist(*alchemyobgects)
        #         index_name = self.alchemy2index(*alchemyobgects)
        #         doctype_name = self.alchemy2doctype(*alchemyobgects)
        #         if doctype_name in self.cached_index_doctype[index_name]:
        #             return True
        #         else:
        #             if self.doctype_exists(index_name, doctype_name):
        #                 self.cached_index_doctype[index_name][doctype_name] = True
        #                 return True
        #
        #             ret = PRElastic.rq(path=PRElastic.path(index_name, '_mapping', doctype_name),
        #                                req=self.generate_mapping(), method='PUT')
        #             if ret:
        #                 print('created doctype:', index_name, doctype_name)
        #                 self.cached_index_doctype[index_name][doctype_name] = True
        #             return True if ret else False
        #
        #     def alchemy2elastic(self, *alchemyobgects):
        #         return (
        #             self.alchemy2index(*alchemyobgects),
        #             self.alchemy2doctype(*alchemyobgects),
        #             self.alchemy2id(*alchemyobgects),
        #             {k: v.setter(*alchemyobgects) for k, v in self.get_all_fields().items()}
        #         )
        #
        #     def replace(self, index_name, document_type, id, document):
        #         return PRElastic.rq(path=PRElastic.path(index_name, document_type, id), req=document, method='PUT')
        #
        #     def recreate_all_documents(self):
        #         for alcemyobjects in self.all_alchemys():
        #             index, doctype, id, doc = self.alchemy2elastic(*alcemyobjects)
        #             self.create_doctype_if_not_exists(*alcemyobjects)
        #             self.replace(index, doctype, id, doc)
        #
        #     def get_all_fields(self):
        #         return {k: v for k, v in self.__dict__.items() if isinstance(v, PRElasticField)}


        # class PRElasticDocumentArticle(PRElasticDocumentType):
        #
        #     def all_alchemys(self):
        #         return [[a, a.portal, a.division] for a in db_session.query(ArticlePortalDivision).all()]
        #
        #     def alchemy2index(self, a, p, d):
        #         return 'articles'
        #
        #     def alchemy2doctype(self, a, p, d):
        #         return 'articles'
        #
        #     def alchemy2id(self, a, p, d):
        #         return a.id
        #



        # class PRElasticIndex:
        #     name = ''
        #     document_types = []
        #     settings = {}
        #
        #     def __init__(self, name, document_types=[]):
        #         self.document_types = document_types
        #         self.name = name
        #
        #     def add_document_type(self, *args):
        #         for a in args:
        #             self.document_types.append(a)
        #         return self
        #
        #     def create(self):
        #         return PRElastic.rq(path=PRElastic.path(self.name), req={
        #             "settings": self.settings,
        #             "mappings": self.generate_mapping()
        #         }, method='PUT')
        #
        #     def delete(self):
        #         return PRElastic.rq(path=PRElastic.path(self.name), req={}, method='DELETE')
        #
        #     def insert_all_documents(self):
        #         return [d.insert_all_documents(self.name) for d in self.document_types]

        # def search_elastic(type, body):
        #     es = Elasticsearch(hosts='elastic.profi')
        #     return ([utils.dict_merge(r['_source'], {'id': r['_id']}) for r in es.search(index='profireader',
        #                                                                                   doc_type=type,
        #                                                                                   body=body)['hits']['hits']], 10, 1)

        # def get_structure():
        #     return [PRElasticDocumentArticle()]
