import datetime
import re

from flask import g, request, current_app
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from profapp import utils
from .portal import Portal
from .pr_base import PRBase, Base, Grid
from ..constants.TABLE_TYPES import TABLE_TYPES


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

    comment = Column(TABLE_TYPES['text'], default='')

    portal = relationship(Portal, uselist=False)

    exemplary_portal_id = '5721ed5f-d35d-4001-ae46-cdfd372b322b'

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
    def try_to_get_phrase(template, phrase, url, portal_id=None, allow_html='', phrase_comment=None,
                          phrase_default=None):

        a_filter = dict(template=template, name=phrase, portal_id=portal_id)

        # TODO: OZ by OZ: this functions exists because we sometemes inmsert recort in flashing process (see on_value_changed decorator)
        # and we can`t use ORM
        def insert_record(**values):
            from profapp import utils
            g.db().execute(('INSERT INTO "%s" (template,   name,  portal_id,  allow_html,  comment,  url,   %s) '
                            'VALUES           (:template, :name, :portal_id, :allow_html, :comment, :url,  :%s)') %
                           (TranslateTemplate.__tablename__, ', '.join(TranslateTemplate.languages),
                            ", :".join(TranslateTemplate.languages)),
                           params=utils.dict_merge(a_filter, {'allow_html': allow_html, 'url': url,
                                                              'comment': '' if phrase_comment is None else ''},
                                                   {l: phrase if phrase_default is None else phrase_default for l in
                                                    TranslateTemplate.languages}, values))
            return utils.db.query_filter(TranslateTemplate, **a_filter).first()

        exist = utils.db.query_filter(TranslateTemplate, **a_filter).first()

        if portal_id and not exist:
            exist_for_another = utils.db.query_filter(TranslateTemplate, template=template, name=phrase,
                                                      portal_id=TranslateTemplate.exemplary_portal_id).first()
            # TODO: OZ by OZ: how to select template portal? now we grab phrases from most recent portal, and there can be some unappropriate values
            if not exist_for_another:
                exist_for_another = utils.db.query_filter(TranslateTemplate, template=template, name=phrase).filter(
                    TranslateTemplate.portal != None).order_by(expression.asc(TranslateTemplate.cr_tm)).first()
            if exist_for_another:
                return insert_record(**{l: getattr(exist_for_another, l) for l in TranslateTemplate.languages})
        if not exist:
            return insert_record()

        return exist

    @staticmethod
    def try_to_guess_lang(translation, language=None):
        from config import Config
        return getattr(translation,
                       language if (language and language in [lng['name'] for lng in Config.LANGUAGES]) else g.lang)

    @staticmethod
    def try_to_guess_url(url):

        url_adapter = g.get_url_adapter()

        try:
            # TODO: OZ by OZ: this try is because i don't understand how to check application/request context stack'
            if url is None:
                url_adapter = g.get_url_adapter()
                rules = url_adapter.map._rules_by_endpoint.get(request.endpoint, ())
                url = '' if len(rules) < 1 else rules[0].rule
            else:

                from werkzeug.urls import url_parse

                parsed_url = url_parse(url)
                rules = url_adapter.match(parsed_url.path, method='GET', return_rule=True)
                url = rules[0].rule

        except Exception:
            url = ''

        return url

    @staticmethod
    def getTranslate(template, phrase, url=None, allow_html='', language=None,
                     phrase_comment=None, phrase_default=None):

        from config import Config
        url = TranslateTemplate.try_to_guess_url(url)

        (phrase, template) = (phrase[2:], '__GLOBAL') if phrase[:2] == '__' else (phrase, template)

        translation = TranslateTemplate.try_to_get_phrase(template, phrase, url,
                                                          phrase_comment=phrase_comment, phrase_default=phrase_default,
                                                          portal_id=getattr(g, "portal_id", None),
                                                          allow_html=allow_html)

        if translation:
            phrase_comment = '' if phrase_comment is None else phrase_comment
            if translation.allow_html != allow_html or \
                            translation.comment != phrase_comment or \
                    (phrase_default is not None and [lng for lng in Config.LANGUAGES if
                                                     getattr(translation, lng['name']) == phrase]) or \
                    (current_app.config['DEBUG'] and (
                                not translation.ac_tm or datetime.datetime.now().timestamp() - translation.ac_tm.timestamp() > 86400)):
                # TODO: OZ by OZ change ac without changing md (md changed by trigger)
                # ac updated without changing md
                params = utils.dict_merge({'allow_html': allow_html, 'comment': phrase_comment,
                                           'ac_tm': datetime.datetime.now(), 'id': translation.id},
                                          {} if phrase_default is None else
                                          {lng['name']: phrase_default for lng in Config.LANGUAGES if
                                           getattr(translation, lng) == phrase})
                sql = 'UPDATE "%s" SET "allow_html" = :allow_html, "comment" = :comment, "ac_tm" = :ac_tm ' % (
                    translation.__tablename__,)

                for lng in Config.LANGUAGES:
                    if getattr(translation, lng['name']) == phrase and phrase_default is not None:
                        sql = sql + ', "' + lng['name'] + '" = :' + lng['name']
                g.db().execute(sql + ' WHERE id = :id', params=params)

            return TranslateTemplate.try_to_guess_lang(translation, language)
        else:
            return phrase

    @staticmethod
    def translate_and_substitute(template, phrase, dictionary={}, language=None, url=None, allow_html='',
                                 phrase_comment=None, phrase_default=None):

        translated = TranslateTemplate.getTranslate(template, phrase, url, allow_html, language,
                                                    phrase_comment=phrase_comment, phrase_default=phrase_default)
        r = re.compile("%\\(([^)]*)\\)s")

        def getFromDict(context, indexes, default):
            d = context
            for i in indexes:
                if isinstance(d, dict):
                    d = d[i] if i in d else default
                else:
                    d = getattr(d, i, default)
            return d

        def replaceinphrase(match):
            indexes = match.group(1).split('.')
            return str(getFromDict(dictionary, indexes, match.group(1)))

        return r.sub(replaceinphrase, translated)

    @staticmethod
    def update_translation(template, phrase, allow_html=None, phrase_comment=None, phrase_default=None):
        from config import Config
        i = datetime.datetime.now()
        obj = utils.db.query_filter(TranslateTemplate, template=template, name=phrase).first()
        if obj:
            obj.ac_tm = i
            obj.comment = obj.comment if phrase_comment is None else phrase_comment
            obj.allow_html = obj.allow_html if allow_html is None else allow_html
            if phrase_default is not None:
                for lng in Config.LANGUAGES:
                    if getattr(obj, lng['name']) == phrase:
                        setattr(obj, lng['name'], phrase_default)
        return True

    @staticmethod
    def delete_translates(objects):
        for obj in objects:
            f = utils.db.query_filter(TranslateTemplate, template=obj['template'], name=obj['name']).first()
            f.delete()
        return 'True'

    @staticmethod
    def isExist(template, phrase):
        list = [f for f in utils.db.query_filter(TranslateTemplate, template=template, name=phrase)]
        return True if list else False

    @staticmethod
    def subquery_search(filters=None, sorts=None, edit=None):
        sub_query = utils.db.query_filter(TranslateTemplate)
        list_filters = []
        list_sorts = []
        if edit:
            exist = utils.db.query_filter(TranslateTemplate, template=edit['template'], name=edit['name']).first()
            i = datetime.datetime.now()
            TranslateTemplate.get(exist.id).attr(
                {edit['col']: edit['newValue'], 'md_tm': i}).save().get_client_side_dict()
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
