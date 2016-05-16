from .pr_base import PRBase, Base, Grid
from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column, ForeignKey, text
from utils.db_utils import db
import datetime
import re
from flask import g, request, current_app
from sqlalchemy.sql import expression
from .portal import Portal
from sqlalchemy.orm import relationship


class TranslateTemplate(Base, PRBase):
    __tablename__ = 'translate'

    languages = ['uk', 'en']

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    ac_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])
    template = Column(TABLE_TYPES['short_name'], default='')
    allow_html = Column(TABLE_TYPES['text'], default='')
    name = Column(TABLE_TYPES['name'], default='')
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    url = Column(TABLE_TYPES['keywords'], default='')
    uk = Column(TABLE_TYPES['name'], default='')
    en = Column(TABLE_TYPES['name'], default='')

    portal = relationship(Portal, uselist=False)

    exemplary_portal_id = '560b9fee-3d87-4001-87d9-ad0d4582dd02'

    def __init__(self, id=None, template=None, portal_id=portal_id, url='', name=None, uk=None, en=None, allow_html=''):
        self.id = id
        self.template = template
        self.name = name
        self.allow_html = allow_html
        self.url = url
        self.uk = uk
        self.en = en
        self.portal_id = portal_id

    @staticmethod
    def try_to_get_phrase(template, phrase, url, portal_id=None, allow_html=''):

        exist = db(TranslateTemplate, template=template, name=phrase, portal_id=portal_id).first()

        if portal_id and not exist:
            exist_for_another = db(TranslateTemplate, template=template, name=phrase,
                                   portal_id=TranslateTemplate.exemplary_portal_id).first()
            if not exist_for_another:
                exist_for_another = db(TranslateTemplate, template=template, name=phrase).filter(
                    TranslateTemplate.portal != None).order_by(expression.desc(TranslateTemplate.cr_tm)).first()
            if exist_for_another:
                exist = TranslateTemplate(template=template, name=phrase, portal_id=portal_id,
                                          url=url,
                                          **{l: getattr(exist_for_another, l) for l in
                                             TranslateTemplate.languages}).save()
                return exist

        if not exist:
            exist = TranslateTemplate(template=template, name=phrase, portal_id=portal_id, allow_html=allow_html,
                                      url=url, **{l: phrase for l in TranslateTemplate.languages}).save()
        return exist

    @staticmethod
    def try_to_guess_lang(translation):
        # lang = TranslateTemplate.languages[0]
        # if g.user_dict['lang'] in TranslateTemplate.languages:
        #     lang = g.user_dict['lang']
        return getattr(translation, g.lang)

    @staticmethod
    def try_to_guess_url(url):

        url_adapter = g.get_url_adapter()

        if url is None:
            url_adapter = g.get_url_adapter()
            rules = url_adapter.map._rules_by_endpoint.get(request.endpoint, ())
            url = '' if len(rules) < 1 else rules[0].rule
        else:
            try:
                from werkzeug.urls import url_parse

                parsed_url = url_parse(url)
                rules = url_adapter.match(parsed_url.path, method='GET', return_rule=True)
                url = rules[0].rule
            except Exception:
                url = ''

        return url

    @staticmethod
    def getTranslate(template, phrase, url=None, allow_html=''):

        url = TranslateTemplate.try_to_guess_url(url)

        (phrase, template) = (phrase[2:], '__GLOBAL') if phrase[:2] == '__' else (phrase, template)

        translation = TranslateTemplate.try_to_get_phrase(template, phrase, url,
                                                          portal_id=g.portal_id,
                                                          allow_html=allow_html)

        if translation:
            if translation.allow_html != allow_html:
                translation.attr({'allow_html': allow_html})
            if current_app.config['DEBUG']:

                # TODO: OZ by OZ change ac without changing md (md changed by trigger)
                # ac updated without changing md

                i = datetime.datetime.now()
                if translation.ac_tm:
                    if i.timestamp() - translation.ac_tm.timestamp() > 86400:
                        translation.attr({'ac_tm': i})
                else:
                    translation.attr({'ac_tm': i})
            return TranslateTemplate.try_to_guess_lang(translation)
        else:
            return phrase

    @staticmethod
    def update_last_accessed(template, phrase):
        i = datetime.datetime.now()
        obj = db(TranslateTemplate, template=template, name=phrase).first()
        obj.attr({'ac_tm': i})
        return True

    @staticmethod
    def change_allowed_html(template, phrase, allow_html):
        obj = db(TranslateTemplate, template=template, name=phrase).first()
        obj.attr({'allow_html': allow_html})
        return 'True'

    @staticmethod
    def delete_translates(objects):
        for obj in objects:
            f = db(TranslateTemplate, template=obj['template'], name=obj['name']).first()
            f.delete()
        return 'True'

    @staticmethod
    def isExist(template, phrase):
        list = [f for f in db(TranslateTemplate, template=template, name=phrase)]
        return True if list else False

    @staticmethod
    def subquery_search(filters=None, sorts=None, edit=None):
        sub_query = db(TranslateTemplate)
        list_filters = []; list_sorts = []
        if edit:
            exist = db(TranslateTemplate, template=edit['template'], name=edit['name']).first()
            i = datetime.datetime.now()
            TranslateTemplate.get(exist.id).attr({edit['col']: edit['newValue'], 'md_tm':i}).save().get_client_side_dict()
        if 'url' in filters:
            list_filters.append({'type': 'select', 'value': filters['url'], 'field': TranslateTemplate.url})
        if 'template' in filters:
            list_filters.append({'type': 'select', 'value': filters['template'], 'field': TranslateTemplate.template})
        if 'name' in filters:
            list_filters.append({'type': 'text', 'value': filters['name'], 'field': TranslateTemplate.name})
        if 'uk' in filters:
            list_filters.append({'type': 'text', 'value': filters['uk'], 'field': TranslateTemplate.uk})
        if 'en' in filters:
            list_filters.append({'type': 'text', 'value': filters['en'], 'field': TranslateTemplate.en})
        if 'portal.name' in filters:
            sub_query = sub_query.join(Portal,
                                       Portal.id == TranslateTemplate.portal_id)
            list_filters.append({'type': 'text', 'value': filters['portal.name'], 'field': Portal.name})
        if 'cr_tm' in sorts:
            list_sorts.append({'type': 'date', 'value': sorts['cr_tm'], 'field': TranslateTemplate.cr_tm})
        elif 'ac_tm' in sorts:
            list_sorts.append({'type': 'date', 'value': sorts['ac_tm'], 'field': TranslateTemplate.ac_tm})
        else:
            list_sorts.append({'type': 'date', 'value': 'desc', 'field': TranslateTemplate.cr_tm})
        sub_query = Grid.subquery_grid(sub_query, list_filters, list_sorts)
        return sub_query

    def get_client_side_dict(self, fields='id|name|uk|en|ac_tm|md_tm|cr_tm|template|url|allow_html, portal.id|name',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

