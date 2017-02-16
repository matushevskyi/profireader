import datetime
import re

from flask import g, request, current_app
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from profapp import utils
from .pr_base import PRBase, Base, Grid
from ..constants.TABLE_TYPES import TABLE_TYPES
from config import Config


class TranslateTemplate(Base, PRBase):
    __tablename__ = 'translate'

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

    portal = relationship('Portal', uselist=False)

    exemplary_portal_id = '5721ed5f-d35d-4001-ae46-cdfd372b322b'

    def __init__(self, id=None, template=None, portal_id=portal_id, url='', name=None, uk=None, en=None, allow_html='',
                 comment=''):
        self.id = id
        self.template = template
        self.name = name
        self.comment = comment
        self.allow_html = allow_html
        self.url = url
        self.uk = uk
        self.en = en
        self.portal_id = portal_id

    def update_record(self, allow_html=None, phrase_comment=None, phrase_default=None, ac_tm=None):
        from profapp.models.messenger import Socket

        params = {}

        if ac_tm is not None:
            params['ac_tm'] = datetime.datetime.now()
        if allow_html is not None and allow_html != self.allow_html:
            params['allow_html'] = allow_html
        if phrase_comment is not None and phrase_comment != self.comment:
            params['comment'] = phrase_comment
        if phrase_default is not None:
            for lng in Config.LANGUAGES:
                if getattr(self, lng['name']) == self.name:
                    params[lng['name']] = phrase_default

        if params:
            if 'ac_tm' in params:
                params['ac_tm'] = params['ac_tm'].timestamp()
            Socket.update_translation(self.id, params)

    @staticmethod
    def try_to_get_phrase(template, phrase, url, portal_id=None, allow_html='', phrase_comment=None,
                          phrase_default=None):

        def insert_record():
            from profapp.models.messenger import Socket

            Socket.insert_translation(utils.dict_merge(
                {l['name']: (phrase if phrase_default is None else phrase_default) for l in Config.LANGUAGES}, {
                    'phrase': phrase,
                    'template': template,
                    'allow_html': allow_html,
                    'url': url,
                    'portal_id': portal_id,
                    'comment': phrase_comment}))

            # TODO: OZ by OZ: we save via sockets because sometimes insert recort in flashing process (see on_value_changed decorator)
            # and we can`t use ORM nor raw sql in current database


            # from profapp import utils
            # g.db().execute(('INSERT INTO "%s" (template,   name,  portal_id,  allow_html,  comment,  url,   %s) '
            #                 'VALUES           (:template, :name, :portal_id, :allow_html, :comment, :url,  :%s)') %
            #                (TranslateTemplate.__tablename__, ', '.join(TranslateTemplate.languages),
            #                 ", :".join(TranslateTemplate.languages)),
            #                params=utils.dict_merge(a_filter, {'allow_html': allow_html, 'url': url,
            #                                                   'comment': '' if phrase_comment is None else ''},
            #                                        {l: phrase if phrase_default is None else phrase_default for l in
            #                                         TranslateTemplate.languages}, values))
            # return utils.db.query_filter(TranslateTemplate, **a_filter).first()

        # a_filter = dict(template=template, name=phrase, portal_id=portal_id)
        exist = utils.db.query_filter(TranslateTemplate, template=template, name=phrase, portal_id=portal_id).first()

        # TODO: OZ by OZ: borrow translation from portal with same template. maybe add field copy_translation_from_portal_id to portal gtable
        # if portal_id and not exist:
        #     exist_for_another = utils.db.query_filter(TranslateTemplate, template=template, name=phrase,
        #                                               portal_id=TranslateTemplate.exemplary_portal_id).first()
        #     # TODO: OZ by OZ: how to select template portal? now we grab phrases from most recent portal, and there can be some unappropriate values
        #     if not exist_for_another:
        #         exist_for_another = utils.db.query_filter(TranslateTemplate, template=template, name=phrase).filter(
        #             TranslateTemplate.portal != None).order_by(expression.asc(TranslateTemplate.cr_tm)).first()
        #     if exist_for_another:
        #         insert_record(**{l: getattr(exist_for_another, l) for l in TranslateTemplate.languages})
        #         return None


        if not exist:
            insert_record()
            return None
        else:
            return exist

    @staticmethod
    def try_to_guess_lang(translation, language=None):
        return getattr(translation,
                       language if (language and language in [lng['name'] for lng in Config.LANGUAGES]) else
                            getattr(g, 'lang', 'en'))

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
        url = TranslateTemplate.try_to_guess_url(url)

        (phrase, template) = (phrase[2:], '__GLOBAL') if phrase[:2] == '__' else (phrase, template)

        translation = TranslateTemplate.try_to_get_phrase(template, phrase, url,
                                                          phrase_comment=phrase_comment, phrase_default=phrase_default,
                                                          portal_id=getattr(g, "portal_id", None),
                                                          allow_html=allow_html)

        if translation:
            translation.update_record(allow_html=allow_html,
                                      phrase_comment=phrase_comment,
                                      phrase_default=phrase_default,
                                      ac_tm=True if ((current_app.debug or current_app.testing) and
                                                     (
                                                         not translation.ac_tm or datetime.datetime.now().timestamp() - translation.ac_tm.timestamp() > 86400)) else None)

            return TranslateTemplate.try_to_guess_lang(translation, language)
        else:
            return phrase

    @staticmethod
    def translate_and_substitute(template, phrase, dictionary={}, language=None, url=None, allow_html='',
                                 phrase_comment=None, phrase_default=None):

        translated = TranslateTemplate.getTranslate(template, phrase, url, allow_html, language,
                                                    phrase_comment=phrase_comment, phrase_default=phrase_default)
        r = re.compile("%\\(([^)]*)\\)s")

        def get_from_dict(context, indexes, default):
            d = context
            for i in indexes:
                if isinstance(d, dict):
                    d = d[i] if i in d else default
                else:
                    d = getattr(d, i, default)
            return d

        def replace_in_phrase(match):
            indexes = match.group(1).split('.')
            return str(get_from_dict(dictionary, indexes, match.group(1)))

        return r.sub(replace_in_phrase, translated)

    @staticmethod
    def update_translation(template, phrase, allow_html=None, phrase_comment=None, phrase_default=None):
        translation = utils.db.query_filter(TranslateTemplate, template=template, name=phrase).first()
        if translation:
            translation.update_record(allow_html=allow_html, phrase_comment=phrase_comment,
                                      phrase_default=phrase_default, ac_tm=True)
        return True

    @staticmethod
    def delete_translates(objects):
        for obj in objects:
            f = utils.db.query_filter(TranslateTemplate, template=obj['template'], name=obj['name']).first()
            f.delete()
        return 'True'

    @staticmethod
    def subquery_search(filters=None, sorts=None, edit=None):
        from .portal import Portal
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


class Phrase:
    name = None
    dict = {}
    comment = ''
    default = None

    def __init__(self, name, dict={}, comment='', default=None):
        self.name = name
        self.dict = dict
        self.comment = comment
        self.default = name if default is None else default

    def translate(self, template='', allow_html='', language=None, more_dictionary={}):
        return TranslateTemplate.translate_and_substitute(template, self.name,
                                                          utils.dict_merge(self.dict, more_dictionary),
                                                          language='en' if language is None else language,
                                                          allow_html=allow_html,
                                                          phrase_comment=self.comment, phrase_default=self.default)
