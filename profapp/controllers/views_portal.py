from .blueprints_declaration import portal_bp
from flask import render_template, g, flash, redirect, url_for, jsonify
from ..models.company import Company
from flask.ext.login import current_user, login_required
from ..models.portal import PortalDivisionType
from ..models.files import File
from ..models.translate import TranslateTemplate
from utils.db_utils import db
from ..models.portal import MemberCompanyPortal, Portal, PortalLayout, PortalDivision, \
    PortalDivisionSettingsCompanySubportal, PortalConfig
from ..models.tag import Tag, TagPortal, TagPortalDivision
from .request_wrapers import ok, check_rights, tos_required
from ..models.articles import ArticlePortalDivision, ArticleCompany, Article
from ..models.company import UserCompany
from profapp.models.rights import RIGHTS
from ..controllers import errors
from ..models.pr_base import PRBase, Grid
import copy
import re
from .pagination import pagination
from config import Config


@portal_bp.route('/<any(create,update):create_or_update>/company/<string:company_id>/', methods=['GET'])
@portal_bp.route('/<any(create,update):create_or_update>/company/<string:company_id>/portal/<string:portal_id>/',
                 methods=['GET'])
@tos_required
@login_required
def profile(create_or_update, company_id, portal_id=None):
    return render_template('portal/portal_create.html', company=Company.get(company_id))


@portal_bp.route('/<any(create,update):create_or_update>/company/<string:company_id>/', methods=['POST'])
@portal_bp.route('/<any(create,update):create_or_update>/company/<string:company_id>/portal/<string:portal_id>/',
                 methods=['POST'])
@login_required
@ok
def profile_load(json, create_or_update, company_id, portal_id=None):
    action = g.req('action', allowed=['load', 'save', 'validate'])
    layouts = [x.get_client_side_dict() for x in db(PortalLayout).all()]
    types = {x.id: x.get_client_side_dict() for x in PortalDivisionType.get_division_types()}
    company = Company.get(company_id)

    if action == 'load':
        ret = {'company': company.get_client_side_dict(),
               'layouts': layouts, 'division_types': types}
        if create_or_update == 'update':
            ret['portal'] = {}
            ret['portal_company_members'] = company.portal_members
            ret['host_profi_or_own'] = 'profi' if re.match(r'^profireader\.', ret['portal']['hostname']) else 'own'
        else:
            ret['portal_company_members'] = [company.get_client_side_dict()]
            ret['portal'] = {'company_owner_id': company_id, 'name': '', 'host': '',
                             'logo_file_id': company.logo_file_id,
                             'host_profi_or_own': 'profi',
                             'host_own': '',
                             'host_profi': '',
                             'portal_layout_id': layouts[0]['id'],
                             'divisions': [
                                 {'name': 'index page', 'portal_division_type_id': 'index',
                                  'page_size': ''},
                                 {'name': 'news', 'portal_division_type_id': 'news', 'page_size': ''},
                                 {'name': 'events', 'portal_division_type_id': 'events',
                                  'page_size': ''},
                                 {'name': 'catalog', 'portal_division_type_id': 'catalog',
                                  'page_size': ''},
                                 {'name': 'our subportal',
                                  'portal_division_type_id': 'company_subportal',
                                  'page_size': '',
                                  'settings': {'company_id': ret['portal_company_members'][0]['id']}}]}
        return ret
    else:
        json_portal = json['portal']
        if create_or_update == 'update':
            pass
        elif create_or_update == 'create':
            page_size_for_config = dict()
            for a in json_portal['divisions']:
                page_size_for_config[a.get('name')] = a.get('page_size') \
                    if type(a.get('page_size')) is int and a.get('page_size') != 0 \
                    else Config.ITEMS_PER_PAGE
            # print(json)
            json_portal['host'] = (json_portal['host_profi'] + '.profireader.com') \
                if json_portal['host_profi_or_own'] == 'profi' else json_portal['host_own']

            portal = Portal(company_owner=company, **g.filter_json(json_portal, 'name', 'portal_layout_id', 'host'))
            divisions = []
            for division_json in json['portal']['divisions']:
                division = PortalDivision(portal, portal_division_type_id=division_json['portal_division_type_id'],
                                          position=len(json['portal']['divisions']) - len(divisions),
                                          name=division_json['name'])
                if division_json['portal_division_type_id'] == 'company_subportal':
                    division.settings = {'member_company_portal': portal.company_members[0]}
                divisions.append(division)
            # self, portal=portal, portal_division_type=portal_division_type, name='', settings={}
            portal.divisions = divisions
            PortalConfig(portal=portal, page_size_for_divisions=page_size_for_config)
        if action == 'save':
            return portal.setup_created_portal(g.filter_json(json_portal, 'logo_file_id')).save().get_client_side_dict()
        else:
            return portal.validate(create_or_update == 'create')


# member_company = Portal.companies


# @portal_bp.route('/confirm_create/<string:company_id>/', methods=['POST'])
# @login_required
# # @check_rights(simple_permissions([Right[RIGHTS.MANAGE_PORTAL()]]))
# @ok
# def confirm_create(json, company_id):
#
#
#
#
#     validation_result = portal.validate()
#
#     if '__validation' in json:
#         db = getattr(g, 'db', None)
#         db.rollback()
#         return validation_result
#     elif len(validation_result['errors'].keys()):
#         raise errors.ValidationException(validation_result)
#     else:
#
#
#     ret = {
#         'company_id': company_id,
#         'company_logo': company_logo,
#         'layouts': layouts,
#         'division_types': {x.id: x.get_client_side_dict() for x in
#                            PortalDivisionType.get_division_types()}
#     }
#
#     if action == 'create':
#         ret['portal'] = {'company_id': company_id, 'name': '', 'host': '',
#                          'portal_layout_id': layouts[0]['id'],
#                          'divisions': [
#                              {'name': 'index page', 'portal_division_type_id': 'index'},
#                              {'name': 'news', 'portal_division_type_id': 'news'},
#                              {'name': 'events', 'portal_division_type_id': 'events'},
#                              {'name': 'catalog', 'portal_division_type_id': 'catalog'},
#                              {'name': 'about', 'portal_division_type_id': 'about'},
#                          ]}
#     else:
#         ret['portal'] = {}
#
#     return ret


@portal_bp.route('/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def apply_company(json):
    MemberCompanyPortal.apply_company_to_portal(company_id=json['company_id'],
                                                portal_id=json['portal_id'])
    return {'portals_partners': [port.get_client_side_dict(fields='name, company_owner_id,id')
                                 for port in Company.get(json['company_id']).get_portals_where_company_is_member()],
            'company_id': json['company_id']}


# @portal_bp.route('/profile/<string:portal_id>/', methods=['GET'])
# @tos_required
# @login_required
# # @check_rights(simple_permissions([])portal_id)
# def profile(portal_id):
#     return render_template('portal/portal_profile.html', company=Portal.get(portal_id).own_company)
#
#
# @portal_bp.route('/profile/<string:portal_id>/', methods=['POST'])
# @login_required
# # @check_rights(simple_permissions([]))
# @ok
# def profile_load(json, portal_id):
#     portal = Portal.get(portal_id)
#     portal_bound_tags = portal.portal_bound_tags_select
#     tags = set(tag_portal_division.tag for tag_portal_division in portal_bound_tags)
#     tags_dict = {tag.id: tag.name for tag in tags}
#     return {'portal': portal.get_client_side_dict('id, '
#                                                   'name, '
#                                                   'divisions, '
#                                                   'own_company, '
#                                                   'portal_bound_tags_select.*, '
#                                                   'portal_notbound_tags_select.*'),
#             'tag': tags_dict}


@portal_bp.route('/profile_edit/<string:portal_id>/', methods=['GET'])
@tos_required
@login_required
# @check_rights(simple_permissions([]))
def profile_edit(portal_id):
    return render_template('portal/portal_profile_edit.html', company=Portal.get(portal_id).own_company)


@portal_bp.route('/profile_edit/<string:portal_id>/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def profile_edit_load(json, portal_id):
    portal = db(Portal, id=portal_id).one()

    if 'profile_tags_edit' in json.keys():  # here all changes with tags in db will be done
        # TODO (AA to AA): We have to consider the situation when divisions were changed while editting tags.
        def strip_new_tags(json):
            """ Strips tags have gotten from input prameter json
            :param json: {'bound_tags': [{'portal_division_id': '....', 'tag_name': '  sun  '}, ...],
                'notbound_tags': ['  moon  ', ...], 'confirm_profile_edit': True}
            :return:     {'bound_tags': [{'portal_division_id': '....', 'tag_name': 'sun'}, ...],
                'notbound_tags': ['moon', ...], 'confirm_profile_edit': True}
            """

            def stripping(json_new_value):
                new_list = []
                for elem in json_new_value:
                    new_elem = copy.deepcopy(elem)
                    new_elem['tag_name'] = new_elem['tag_name'].strip()
                    new_list.append(new_elem)
                return new_list

            json_new = {'bound_tags': [], 'notbound_tags': []}

            key = 'bound_tags'
            json_new[key] = stripping(json[key])

            key = 'notbound_tags'
            json_new[key] = list(map(lambda x: getattr(x, 'strip')(), json[key]))

            return json_new

        json_new = strip_new_tags(json)

        curr_portal_bound_tag_port_div_objects = portal.portal_bound_tags_select
        curr_portal_bound_tags = set(map(lambda x: x.tag, curr_portal_bound_tag_port_div_objects))
        curr_portal_bound_tag_names = set(map(lambda x: x.name, curr_portal_bound_tags))
        curr_portal_bound_tags_dict = {}
        for elem in curr_portal_bound_tags:
            curr_portal_bound_tags_dict[elem.name] = elem
        curr_portal_bound_port_div_id_tag_name_object_dict = {}
        for elem in curr_portal_bound_tag_port_div_objects:
            curr_portal_bound_port_div_id_tag_name_object_dict[
                frozenset({('portal_division_id', elem.portal_division_id),
                           ('tag_name', elem.tag.name)})
            ] = elem

        curr_portal_notbound_tag_port_objects = portal.portal_notbound_tags_select
        curr_portal_notbound_tags = set(map(lambda x: x.tag, curr_portal_notbound_tag_port_objects))
        curr_portal_notbound_tag_names = set(map(lambda x: x.name, curr_portal_notbound_tags))
        curr_portal_notbound_tags_dict = {}
        for elem in curr_portal_notbound_tags:
            curr_portal_notbound_tags_dict[elem.name] = elem
        curr_portal_notbound_tag_name_object_dict = {}
        for elem in curr_portal_notbound_tag_port_objects:
            curr_portal_notbound_tag_name_object_dict[elem.tag.name] = elem

        new_bound_tags = json_new['bound_tags']
        new_notbound_tags = json_new['notbound_tags']

        new_bound_tag_names = set(map(lambda x: x['tag_name'], new_bound_tags))
        new_notbound_tag_names = set(new_notbound_tags)

        curr_tag_names = curr_portal_bound_tag_names | curr_portal_notbound_tag_names
        new_tag_tames = new_bound_tag_names | new_notbound_tag_names

        deleted_tag_names = curr_tag_names - new_tag_tames
        added_tag_names = new_tag_tames - (new_tag_tames & curr_tag_names)

        # actually_deleted_tags = set()
        # for tag_name in deleted_tag_names:
        #     other_portal_with_deleted_tags = g.db.query(Portal.id).filter(Portal.id!=portal_id).\
        #         join(PortalDivision).\
        #         join(TagPortalDivision).\
        #         join(Tag).\
        #         filter(Tag.name==tag_name).first()
        #
        #     if not other_portal_with_deleted_tags:
        #         other_portal_with_deleted_tags = g.db.query(Portal.id).\
        #             filter(Portal.id!=portal_id).\
        #             join(TagPortal).\
        #             join(Tag).\
        #             filter(Tag.name==tag_name).first()
        #
        #         if not other_portal_with_deleted_tags:
        #             actually_deleted_tags.add(tag_name)

        actually_added_tags = set()
        for tag_name in added_tag_names:
            other_portal_with_added_tags = g.db.query(Portal.id).filter(Portal.id != portal_id). \
                join(PortalDivision). \
                join(TagPortalDivision). \
                join(Tag). \
                filter(Tag.name == tag_name).first()

            if not other_portal_with_added_tags:
                other_portal_with_added_tags = g.db.query(Portal.id). \
                    filter(Portal.id != portal_id). \
                    join(TagPortal). \
                    join(Tag). \
                    filter(Tag.name == tag_name).first()

                if not other_portal_with_added_tags:
                    actually_added_tags.add(tag_name)

        new_tags_dict = {}
        for tag_name in new_tag_tames:
            tag = g.db.query(Tag).filter_by(name=tag_name).join(TagPortal).first()
            if not tag:
                tag = g.db.query(Tag).filter_by(name=tag_name).join(TagPortalDivision).first()
            if not tag:
                tag = Tag(tag_name)
            new_tags_dict[tag_name] = tag

        # actually_added_tags_dict = {}
        # for tag_name in actually_added_tags:
        #     actually_added_tags_dict[tag_name] = Tag(tag_name)

        # user_company = UserCompany(status=STATUS.ACTIVE(), rights_int=COMPANY_OWNER_RIGHTS)
        # user_company.employer = self
        # g.user.employer_assoc.append(user_company)
        # g.user.companies.append(self)
        # self.youtube_playlists.append(YoutubePlaylist(name=self.name, company_owner=self))
        # self.save()

        # TODO: Now we have actually_deleted_tags and actually_added_tags

        # new_tags_dict = {}
        # for key in actually_added_tags_dict.keys():
        #     new_tags_dict[key] = actually_added_tags_dict[key]
        # for key in curr_portal_bound_tags_dict.keys():
        #     new_tags_dict[key] = curr_portal_bound_tags_dict[key]
        # for key in curr_portal_notbound_tags_dict.keys():
        #     new_tags_dict[key] = curr_portal_notbound_tags_dict[key]

        # curr_portal_bound_tag_port_div_objects
        # curr_portal_bound_port_div_id_tag_name_dict
        # new_bound_tags = json_new['bound_tags']
        # curr_portal_bound_port_div_id_tag_name_object_dict


        # curr_portal_bound_port_div_id_tag_name_object_dict = []
        # for elem in curr_portal_bound_tag_port_div_objects:
        #     curr_portal_bound_port_div_id_tag_name_object_dict.append(
        #         [{'portal_division_id': elem.portal_division_id,
        #          'tag_name': elem.tag.name},
        #          elem]
        #     )

        keys = list(map(dict, curr_portal_bound_port_div_id_tag_name_object_dict.keys()))
        add_tag_portal_bound_list = []
        for elem in json_new['bound_tags']:
            if elem not in keys:
                new_tag_port_div = TagPortalDivision(portal_division_id=elem['portal_division_id'])
                new_tag_port_div.tag = new_tags_dict[elem['tag_name']]
                add_tag_portal_bound_list.append(new_tag_port_div)

        delete_tag_portal_bound_list = []
        for elem in keys:
            if elem not in json_new['bound_tags']:
                delete_tag_portal_bound_list.append(
                        curr_portal_bound_port_div_id_tag_name_object_dict[frozenset(elem.items())]
                )

        add_tag_portal_notbound_list = []
        for elem in json_new['notbound_tags']:
            if elem not in curr_portal_notbound_tags:
                new_tag_port = TagPortal(portal_id=elem['portal_id'])
                new_tag_port.tag = new_tags_dict[elem['tag_name']]
                add_tag_portal_notbound_list.append(new_tag_port)

        delete_tag_portal_notbound_list = []
        for elem in curr_portal_notbound_tags:
            if elem not in json_new['notbound_tags']:
                delete_tag_portal_notbound_list.append(
                        curr_portal_notbound_tag_name_object_dict[elem.name]
                )

        g.db.add_all(add_tag_portal_bound_list + add_tag_portal_notbound_list)
        # read this: http://stackoverflow.com/questions/7892618/sqlalchemy-delete-subquery
        if delete_tag_portal_bound_list:
            g.db.query(TagPortalDivision). \
                filter(TagPortalDivision.id.in_([x.id for x in delete_tag_portal_bound_list])). \
                delete(synchronize_session=False)
        if delete_tag_portal_notbound_list:
            g.db.query(TagPortal). \
                filter(TagPortal.id.in_([x.id for x in delete_tag_portal_notbound_list])). \
                delete(synchronize_session=False)
        g.db.expire_all()

        # TODO (AA to AA): not to forget to delete unused tags... New tags well be added.

        # for elem in delete_tag_portal_bound_list:
        #     g.db.delete(elem)
        g.db.commit()

        # portal.portal_bound_tags_dynamic = ...
        # portal.portal_notbound_tags_dynamic = ...

        # added_bound_tag_names = new_bound_tag_names - (new_bound_tag_names & curr_portal_bound_tag_names)
        # added_notbound_tag_names = new_notbound_tag_names - (new_notbound_tag_names & curr_portal_notbound_tag_names)

        # tag0_name = curr_portal_bound_tag_port_div_objects[0].tag.name
        # y = list(curr_portal_bound_tag_port_div_objects)         # Operations with portal_bound_tags_dynamic...
        flash('Portal tags were successfully updated')

    tags = set(tag_portal_division.tag for tag_portal_division in portal.portal_bound_tags_select)
    tags_dict = {tag.id: tag.name for tag in tags}

    return {'portal': portal.get_client_side_dict('id, name, divisions, own_company, portal_bound_tags_select.*'),
            'tag': tags_dict}


@portal_bp.route('/portals_partners/<string:company_id>/', methods=['GET'])
@tos_required
@login_required
# @check_rights(simple_permissions([]))
def portals_partners(company_id):
    return render_template('company/portals_partners.html',
                           company=Company.get(company_id),
                           rights_user_in=UserCompany.get(company_id=company_id).has_rights(
                                   UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS))


@portal_bp.route('/portals_partners/<string:company_id>/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def portals_partners_load(json, company_id):
    subquery = Company.subquery_company_partners(company_id, json.get('filter'))
    partners_g, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))
    partner_list = [
        PRBase.merge_dicts(partner.get_client_side_dict(fields='id,status,portal.own_company,portal,rights'),
                           {'actions': partner.actions(company_id, partner)})
        for partner in partners_g]
    return {'page': current_page,
            'grid_data': partner_list,
            'total': count}


@portal_bp.route('/portals_partners_change_status/<string:company_id>/<string:portal_id>', methods=['POST'])
@login_required
@ok
# freeze our part in this company
def portals_partners_change_status(json, company_id, portal_id):
    partner = MemberCompanyPortal.get(portal_id=portal_id, company_id=company_id)
    employment = UserCompany.get(company_id=company_id)
    if partner.action_is_allowed(json.get('action'), employment,
                                 UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS,
                                 MemberCompanyPortal.ACTION_FOR_STATUS[partner.status]):
        partner.set_client_side_dict(
                status=MemberCompanyPortal.STATUSES['ACTIVE'] if json.get('action') == 'RESTORE' else
                MemberCompanyPortal.STATUS_FOR_ACTION[json.get('action')])
        partner.save()
    return partner.get_client_side_dict()


# @portal_bp.route('/<string:employeer_id>/company_partner_details/<string:member_id>/', methods=['GET'])
# @login_required
# def company_partner_details(member_id, employeer_id):
#     member = MemberCompanyPortal.get(Company.get(employeer_id).own_portal.id, member_id)
#     return render_template('company/company_partner_details.html',
#                            company=Company.get(employeer_id),
#                            employeer=Company.get(employeer_id).get_client_side_dict(),
#                            member = member.get_client_side_dict(more_fields='company'),
#                            user_right_in=UserCompany.get(company_id=employeer_id).has_rights(UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES)
#                            )

@portal_bp.route('/<string:employeer_id>/company_partner_update/<string:member_id>/', methods=['GET'])
@login_required
def company_partner_update(employeer_id, member_id):
    return render_template('company/company_partner_update.html',
                           company=Company.get(employeer_id),
                           member=MemberCompanyPortal.get(Company.get(employeer_id).own_portal.id,
                                                          company_id=member_id).company.get_client_side_dict(
                                   'id, status'))


@portal_bp.route('/<string:employeer_id>/company_partner_update/<string:member_id>/', methods=['POST'])
@tos_required
@login_required
@ok
# @check_rights(simple_permissions([]))
def company_update_load(json, employeer_id, member_id):
    action = g.req('action', allowed=['load', 'validate', 'save'])
    member = MemberCompanyPortal.get(Company.get(employeer_id).own_portal.id, member_id)
    if action == 'load':
        return {'member': member.get_client_side_dict(more_fields='company'),
                'statuses_available': MemberCompanyPortal.get_avaliable_statuses(),
                'employeer': Company.get(employeer_id).get_client_side_dict()}
    else:
        member.set_client_side_dict(status=json['member']['status'], rights=json['member']['rights'])
        if action == 'validate':
            member.detach()
            return member.validate(False)
        else:
            member.save()
    return member.get_client_side_dict()


@portal_bp.route('/companies_partners/<string:company_id>/', methods=['GET'])
@tos_required
@login_required
# @check_rights(simple_permissions([]))
def companies_partners(company_id):
    return render_template('company/companies_partners.html', company=Company.get(company_id),
                           rights_user_in=UserCompany.get(company_id=company_id).has_rights(
                                   UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS))


@portal_bp.route('/companies_partners/<string:company_id>/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def companies_partners_load(json, company_id):
    subquery = db(MemberCompanyPortal).filter(
            MemberCompanyPortal.portal_id == db(Portal, company_owner_id=company_id).subquery().c.id)
    members, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))
    return {'grid_data': [{'member': member.get_client_side_dict(more_fields='company'),
                           'company_id': company_id}
                          for member in members],
            'total': count,
            'page': current_page}


@portal_bp.route('/search_for_portal_to_join/', methods=['POST'])
@ok
@login_required
# @check_rights(simple_permissions([]))
def search_for_portal_to_join(json):
    portals_partners = Portal.search_for_portal_to_join(
            json['company_id'], json['search'])
    return portals_partners


@portal_bp.route('/company/<string:company_id>/publications/', methods=['GET'])
@tos_required
@login_required
# @check_rights(simple_permissions([]))
def publications(company_id):
    return render_template('portal/portal_publications.html', company=Company.get(company_id))


def get_publication_dict(publication):
    ret = publication.get_client_side_dict()
    if ret.get('long'):
        del ret['long']

    ret['actions'] = publication.get_actions_for_status(publication.division.portal.company_owner_id)

    return ret


@portal_bp.route('/company/<string:company_id>/publications/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def publications_load(json, company_id):
    company = Company.get(company_id)
    portal = company.own_portal
    subquery = ArticlePortalDivision.subquery_portal_articles(portal.id, json.get('filter'), json.get('sort'))
    publications, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))
    # grid_filters = {
    #     'publication_status':Grid.filter_for_status(ArticlePortalDivision.STATUSES),
    #     'company': [{'value': company_id, 'label': company} for company_id, company  in
    #                 ArticlePortalDivision.get_companies_which_send_article_to_portal(portal).items()]
    # }
    return {
        'company': company.get_client_side_dict(),
        'portal': portal.get_client_side_dict(),
        'rights_user_in_company': UserCompany.get(company_id=company_id).rights,
        'grid_data': list(map(get_publication_dict, publications))}


@portal_bp.route('/publication_delete_unpublish/', methods=['POST'])
@ok
# @check_rights(simple_permissions([]))
def publication_delete_unpublish(json):
    action = g.req('action', allowed=['delete', 'unpublish', 'undelete'])

    publication = ArticlePortalDivision.get(json['publication_id'])
    publication.status = ArticlePortalDivision.STATUSES['DELETED' if action == 'delete' else 'UNPUBLISHED']

    return get_publication_dict(publication.save())


@portal_bp.route('/publication_details/<string:article_id>/<string:company_id>', methods=['GET'])
@tos_required
@login_required
def publication_details(article_id, company_id):
    return render_template('company/publication_details.html', company_id=company_id,
                           company=db(Company, id=company_id).one())


@portal_bp.route('/publication_details/<string:article_id>/<string:company_id>', methods=['POST'])
@login_required
@ok
def publication_details_load(json, article_id, company_id):
    article = db(ArticlePortalDivision, id=article_id).one().get_client_side_dict()
    allowed_statuses = ArticlePortalDivision.STATUSES.keys()

    return {'article': article,
            'rights_user_in_company': UserCompany.get(company_id=company_id).rights,
            'allowed_statuses': allowed_statuses}


@portal_bp.route('/update_article_portal/<string:article_id>', methods=['POST'])
@login_required
@ok
def update_article_portal(json, article_id):
    db(ArticlePortalDivision, id=article_id).update({'status': json.get('new_status')})
    article = db(ArticlePortalDivision, id=article_id).one().get_client_side_dict()
    allowed_statuses = ArticlePortalDivision.STATUSES.keys()
    json['allowed_statuses'] = allowed_statuses
    json['article']['status'] = json.get('new_status')
    return json

# @portal_bp.route('/submit_to_portal/<any(validate,save):action>/', methods=['POST'])
# @ok
# def submit_to_portal(json, action):
#     json['tags'] = ['money', 'sex', 'rock and roll']; tag position is important
#
# article = ArticleCompany.get(json['article']['id'])
# if action == 'validate':
#     return article.validate('update')
# if action == 'save':
#     portal_division_id = json['selected_division']
#     article_portal = article.clone_for_portal(portal_division_id, json['tags'])
#     article.save()
#     portal = article_portal.get_article_owner_portal(portal_division_id=portal_division_id)
#     return {'portal': portal.name}
