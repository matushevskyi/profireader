from .blueprints_declaration import portal_bp
from flask import render_template, g, flash
from ..models.company import Company
from flask.ext.login import login_required
from profapp.controllers.errors import BadDataProvided
from ..models.portal import PortalDivisionType
from ..models.translate import TranslateTemplate
from tools.db_utils import db
from ..models.portal import MemberCompanyPortal, Portal, PortalLayout, PortalDivision, \
    PortalDivisionSettingsCompanySubportal, PortalAdvertisment, PortalAdvertismentPlace, MemberCompanyPortalPlan
from .request_wrapers import ok, check_right
# from ..models.bak_articles import Publication, ArticleCompany, Article
from ..models.company import UserCompany
from ..models.materials import Publication, Material
from ..models.tag import Tag, TagPortalDivision
from profapp.models.rights import RIGHTS
from ..controllers import errors
from ..models.pr_base import PRBase, Grid
import copy
from .. import utils
import re
from .pagination import pagination
from config import Config
from ..models.rights import PublishUnpublishInPortal, MembersRights, MembershipRights, RequireMembereeAtPortalsRight, \
    PortalManageMembersCompaniesRight, UserIsEmployee, EditPortalRight, UserIsActive


@portal_bp.route('/portal/<any(create,update):create_or_update>/company/<string:company_id>/', methods=['GET'])
@check_right(EditPortalRight, ['company_id'])
def profile(create_or_update, company_id):
    company = Company.get(company_id)
    if create_or_update == 'update':
        portal = g.db.query(Portal).filter_by(company_owner_id=company.id).first()
    else:
        portal = None

    return render_template('portal/portal_edit.html', company=company, portal_id=portal.id if portal else None)


@portal_bp.route('/portal/<any(create,update):create_or_update>/company/<string:company_id>/', methods=['OK'])
@check_right(EditPortalRight, ['company_id'])
def profile_load(json, create_or_update, company_id):
    action = g.req('action', allowed=['load', 'save', 'validate'])
    layouts = db(PortalLayout).all()
    division_types = PortalDivisionType.get_division_types()
    company = Company.get(company_id)
    if create_or_update == 'update':
        portal = g.db.query(Portal).filter_by(company_owner_id=company.id).first()
    else:
        portal = Portal(host='', lang=g.user.lang,
                    own_company=company,
                    company_owner_id=company.id,
                    company_memberships=[MemberCompanyPortal(company=company,
                    plan=db(MemberCompanyPortalPlan).first())])

    client_side = lambda: {
            'select': {
                'languages': Config.LANGUAGES,
                'layouts': utils.get_client_side_list(layouts),
                'division_types': utils.get_client_side_dict(division_types)
            },
            'portal': portal.get_client_side_dict(
                fields='name,host,logo,url_facebook,url_google,url_tweeter,url_linkedin,portal_layout_id,divisions,divisions.cr_tm,lang,host,own_company,company_memberships.company',
                get_own_or_profi_host=True)
        }

    if action == 'load':
        return client_side()
    else:
        jp = json['portal']

        jp['host'] = (jp['host_profi'] + '.' + Config.MAIN_DOMAIN) if jp['host_profi_or_own'] == 'profi' else jp[
            'host_own']

        portal.attr_filter(jp, 'name', 'lang', 'portal_layout_id', 'host',
                           *map(lambda x: 'url_' + x, ['facebook', 'google', 'tweeter', 'linkedin']))

        if set(portal.divisions) - set(utils.find_by_id(portal.divisions, d['id']) for d in jp['divisions']) != set():
            raise BadDataProvided('Information for some existing portal division is not provided by client')

        division_position = 0
        unpublish_warning = {}
        old_division_types = {}
        deleted_divisions = []
        for jd in jp['divisions']:
            ndi = utils.find_by_id(portal.divisions, jd['id']) or PortalDivision(portal=portal, id=jd['id'])
            if jd.get('remove_this_existing_division', None):
                deleted_divisions.append(ndi)
                if len(ndi.publications):
                    utils.dict_deep_replace('this division have %s published articles. they will be unpublished' % (len(ndi.publications),), unpublish_warning, ndi.id, 'actions')
                portal.divisions.remove(ndi)
            else:
                ndi.portal = portal
                ndi.position = division_position
                ndi.name = jd['name']
                if ndi in portal.divisions:
                    if len(ndi.publications) and jd['portal_division_type_id'] != ndi.portal_division_type.id:
                        old_division_types[ndi.id] = ndi.portal_division_type.id
                        utils.dict_deep_replace('this division have %s published articles. they will be unpublished becouse of division type changed' % (
                        len(ndi.publications),), unpublish_warning, ndi.id, 'type')
                else:
                    portal.divisions.append(ndi)

                ndi.portal_division_type = utils.find_by_id(division_types, jd['portal_division_type_id'])
                ndi.settings = jd.get('settings', {})


                division_position += 1
        if action == 'validate':
            ret = portal.validate(create_or_update  == 'create')
            if len(unpublish_warning.keys()):
                if 'divisions' not in ret['warnings']:
                    ret['warnings']['divisions'] = {}
                ret['warnings']['divisions'] = utils.dict_merge_recursive(ret['warnings']['divisions'], unpublish_warning)
            g.db.expunge_all()
            return ret
        else:
            for nd in portal.divisions:
                if not nd.cr_tm:
                    nd.id = None
            portal.logo = jp['logo']
            for del_div in deleted_divisions:
                del_div.notice_about_deleted_publications('division deleted')

            for div in portal.divisions:
                div.notice_about_deleted_publications('division type changed')

            portal.save()
            g.db.commit()
            return client_side()


@portal_bp.route('/apply_company/<string:company_id>', methods=['OK'])
@check_right(RequireMembereeAtPortalsRight, ['company_id'])
def apply_company(json, company_id):
    MemberCompanyPortal.apply_company_to_portal(company_id=company_id,
                                                portal_id=json['portal_id'])
    return {'portals_partners': [portal.get_client_side_dict(fields='name, company_owner_id,id')
                                 for portal in PublishUnpublishInPortal.get_portals_where_company_is_member(
            Company.get(company_id))], 'company_id': company_id}


@portal_bp.route('/portals_partners/<string:company_id>/', methods=['GET'])
@check_right(UserIsEmployee, ['company_id'])
def portals_partners(company_id):
    return render_template('company/portals_partners.html',
                           company=Company.get(company_id),
                           actions={'require_memberee': RequireMembereeAtPortalsRight(company=company_id).is_allowed()})


def membership_grid_row(membership):
    return utils.dict_merge(membership.get_client_side_dict(fields='id,status,portal.own_company,portal,rights,tags'),
                            {'actions': MembershipRights(company=membership.company_id,
                                                         member_company=membership).actions()},
                            {'who': MembershipRights.MEMBERSHIP})


@portal_bp.route('/portals_partners/<string:company_id>/', methods=['OK'])
@check_right(UserIsEmployee, ['company_id'])
def portals_partners_load(json, company_id):
    subquery = Company.subquery_portal_partners(company_id, json.get('filter'),
                                                filters_exсept=MembersRights.INITIALLY_FILTERED_OUT_STATUSES)
    partners_g, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    return {'page': current_page,
            'grid_data': [membership_grid_row(partner) for partner in partners_g],
            'grid_filters': {k: [{'value': None, 'label': TranslateTemplate.getTranslate('', '__-- all --')}] + v for
                             (k, v) in {'status': [{'value': status, 'label': status} for status in
                                                   MembershipRights.STATUSES]}.items()},
            'grid_filters_except': list(MembershipRights.INITIALLY_FILTERED_OUT_STATUSES),
            'total': count}


@portal_bp.route('/portal_banners/<string:company_id>/', methods=['GET'])
@check_right(UserIsEmployee, 'company_id')
def portal_banners(company_id):
    return render_template('company/portal_banners.html',
                           company=Company.get(company_id))


@portal_bp.route('/portal_banners/<string:company_id>/', methods=['OK'])
@check_right(UserIsEmployee, 'company_id')
def portal_banners_load(json, company_id):
    portal = Company.get(company_id).own_portal
    if 'action_name' in json:
        if json['action_name'] == 'create':
            place = db(PortalAdvertismentPlace, portal_layout_id=portal.portal_layout_id,
                       place=json['row']['place']).one()
            newrow = PortalAdvertisment(portal_id=portal.id, html=place.default_value if place.default_value else '',
                                        place=json['row']['place']).save()
            return {'grid_action': 'refresh_row', 'row': newrow.get_client_side_dict()}

        elif json['action_name'] == 'delete':
            PortalAdvertisment.get(json['id']).delete()
            return {'grid_action': 'delete_row'}
        elif json['action_name'] == 'set_default':
            adv = PortalAdvertisment.get(json['id'])
            place = db(PortalAdvertismentPlace, portal_layout_id=portal.portal_layout_id, place=adv.place).one()
            adv.html = place.default_value
            adv.save()
            return {}
    else:
        banners = PortalAdvertisment.get_portal_advertisments(portal)
        return {'page': 1,
                'grid_data': banners,
                'grid_filters': {},
                'total': len(banners)}


@portal_bp.route('/save_portal_banner/<string:company_id>/', methods=['OK'])
@check_right(UserIsEmployee, 'company_id')
def save_portal_banner(json, company_id):
    advertisment = PortalAdvertisment.get(json.get('editBanners')['id'])
    advertisment.html = json.get('editBanners')['html']
    advertisment.save()
    return advertisment.get_client_side_dict()


@portal_bp.route('/portals_partners_change_status/<string:company_id>/<string:portal_id>', methods=['OK'])
@check_right(RequireMembereeAtPortalsRight, ['company_id'])
def portals_partners_change_status(json, company_id, portal_id):
    partner = MemberCompanyPortal.get_by_portal_id_company_id(portal_id=portal_id, company_id=json.get('partner_id'))
    employee = UserCompany.get_by_user_and_company_ids(company_id=company_id)
    if MembershipRights(company=json.get('partner_id'), member_company=partner).action_is_allowed(json.get('action'),
                                                                                                  employee) == True:
        partner.set_client_side_dict(
            status=MembershipRights.STATUS_FOR_ACTION[json.get('action')])
        partner.save()
    return membership_grid_row(partner)


@portal_bp.route('/membership_set_tags/<string:company_id>/<string:portal_id>/', methods=['OK'])
# @check_right(RequireMembereeAtPortalsRight, ['company_id'])
def membership_set_tags(json, company_id, portal_id):
    membership = MemberCompanyPortal.get_by_portal_id_company_id(portal_id=portal_id, company_id=company_id)
    action = g.req('action', allowed=['load', 'validate', 'save'])
    if action == 'load':
        return membership.get_client_side_dict(fields='id,portal,portal.tags,company,tags')
    else:
        membership.tags = [Tag.get(t['id']) for t in json['tags']]

        if action == 'validate':
            membership.detach()
            return PRBase.DEFAULT_VALIDATION_ANSWER()
        else:
            membership.save().set_tags_positions()
            return {'membership': membership_grid_row(membership)}


@portal_bp.route('/<string:company_id>/company_partner_update/<string:member_id>/', methods=['GET'])
@check_right(PortalManageMembersCompaniesRight, ['company_id', 'member_id'])
def company_partner_update(company_id, member_id):
    return render_template('company/company_partner_update.html',
                           company=Company.get(company_id),
                           member=MemberCompanyPortal.get_by_portal_id_company_id(Company.get(company_id).own_portal.id,
                                                                                  company_id=member_id).company.get_client_side_dict(
                               'id, status'))


@portal_bp.route('/<string:company_id>/company_partner_update/<string:member_id>/', methods=['OK'])
@check_right(PortalManageMembersCompaniesRight, ['company_id', 'member_id'])
def company_update_load(json, company_id, member_id):
    action = g.req('action', allowed=['load', 'validate', 'save'])
    member = MemberCompanyPortal.get_by_portal_id_company_id(Company.get(company_id).own_portal.id, member_id)
    if action == 'load':
        return {'member': member.get_client_side_dict(more_fields='company'),
                'statuses_available': MembersRights.get_avaliable_statuses(),
                'employeer': Company.get(company_id).get_client_side_dict()}
    else:
        member.set_client_side_dict(status=json['member']['status'], rights=json['member']['rights'])
        if action == 'validate':
            member.detach()
            validate = member.validate(False)
            return validate
        else:
            member.save()
    return member.get_client_side_dict()


@portal_bp.route('/company_partners_change_status/<string:company_id>/<string:portal_id>', methods=['OK'])
@check_right(PortalManageMembersCompaniesRight, ['company_id'])
def company_partners_change_status(json, company_id, portal_id):
    partner = MemberCompanyPortal.get_by_portal_id_company_id(portal_id=portal_id, company_id=json.get('partner_id'))
    employee = UserCompany.get_by_user_and_company_ids(company_id=company_id)
    if MembersRights(company=json.get('partner_id'), member_company=partner).action_is_allowed(json.get('action'),
                                                                                               employee) == True:
        partner.set_client_side_dict(
            status=MembersRights.STATUS_FOR_ACTION[json.get('action')])
        partner.save()
    return {'member': partner.get_client_side_dict(more_fields='company'),
            'company_id': company_id,
            'portal_id': db(Portal, company_owner_id=company_id).first().id,
            'actions': MembersRights(company=company_id,
                                     member_company=partner).actions(),
            'id': partner.id}


@portal_bp.route('/companies_partners/<string:company_id>/', methods=['GET'])
@check_right(UserIsEmployee, ['company_id'])
def companies_partners(company_id):
    return render_template('company/companies_partners.html', company=Company.get(company_id),
                           rights_user_in=UserCompany.get_by_user_and_company_ids(company_id=company_id).has_rights(
                               UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES))


@portal_bp.route('/companies_partners/<string:company_id>/', methods=['OK'])
@check_right(UserIsEmployee, ['company_id'])
def companies_partners_load(json, company_id):
    subquery = Company.subquery_company_partners(company_id, json.get('filter'),
                                                 filters_exсept=MembersRights.INITIALLY_FILTERED_OUT_STATUSES)
    members, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))
    return {'grid_data': [utils.dict_merge({'member': member.get_client_side_dict(more_fields='company'),
                                            'company_id': company_id,
                                            'portal_id': db(Portal, company_owner_id=company_id).first().id},
                                           {'actions': MembersRights(company=company_id,
                                                                     member_company=member).actions()},
                                           {'id': member.id})
                          for member in members],
            'grid_filters': {k: [{'value': None, 'label': TranslateTemplate.getTranslate('', '__-- all --')}] + v for
                             (k, v) in {'member.status': [{'value': status, 'label': status} for status in
                                                          MembersRights.STATUSES]}.items()},
            'grid_filters_except': list(MembersRights.INITIALLY_FILTERED_OUT_STATUSES),
            'total': count,
            'page': current_page}


@portal_bp.route('/search_for_portal_to_join/', methods=['OK'])
@check_right(UserIsActive)
def search_for_portal_to_join(json):
    if RequireMembereeAtPortalsRight(company=json['company_id']).is_allowed() != True:
        return False
    portals_partners = Portal.search_for_portal_to_join(
        json['company_id'], json['search'])
    return portals_partners


@portal_bp.route('/company/<string:company_id>/publications/', methods=['GET'])
@check_right(UserIsEmployee, ['company_id'])
def publications(company_id):
    return render_template('portal/portal_publications.html', company=Company.get(company_id))


def get_publication_dict(publication):
    ret = {}
    ret['publication'] = publication.get_client_side_dict()
    if ret.get('long'):
        del ret['long']
    ret['id'] = publication.id
    ret['actions'] = PublishUnpublishInPortal(publication=publication, division=publication.division,
                                              company=publication.division.portal.own_company).actions()
    return ret


@portal_bp.route('/company/<string:company_id>/publications/', methods=['OK'])
@check_right(UserIsEmployee, ['company_id'])
def publications_load(json, company_id):
    company = Company.get(company_id)
    portal = company.own_portal

    publications = db(Publication).join(PortalDivision, PortalDivision.id == Publication.portal_division_id). \
        filter(PortalDivision.portal_id == portal.id).all()

    # subquery = Company.subquery_portal_articles(portal.id, json.get('filter'), json.get('sort'))
    # publications, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))




    # grid_filters = {
    #     'publication_status':Grid.filter_for_status(Publication.STATUSES),
    #     'company': [{'value': company_id, 'label': company} for company_id, company  in
    #                 Publication.get_companies_which_send_article_to_portal(portal).items()]
    # }
    return {'company': company.get_client_side_dict(),
            'portal': portal.get_client_side_dict(),
            'rights_user_in_company': UserCompany.get_by_user_and_company_ids(company_id=company_id).rights,
            'grid_data': list(map(get_publication_dict, publications)),
            'total': len(publications)}


@portal_bp.route('/company/<string:company_id>/tags/', methods=['GET'])
@check_right(UserIsEmployee, 'company_id')
def tags(company_id):
    return render_template('portal/tags.html', company=Company.get(company_id))


@portal_bp.route('/company/<string:company_id>/tags/', methods=['OK'])
@check_right(UserIsEmployee, 'company_id')
def tags_load(json, company_id):
    action = g.req('action', allowed=['load', 'save', 'validate'])
    company = Company.get(company_id)
    portal = company.own_portal

    def get_client_model(aportal):
        portal_dict = aportal.get_client_side_dict()
        portal_dict['divisions'] = [division for division in portal_dict['divisions']
                                    if division['portal_division_type_id'] == 'news' or division[
                                        'portal_division_type_id'] == 'events']
        ret = {'company': company.get_client_side_dict(),
               'portal': portal_dict}
        for division in ret['portal']['divisions']:
            division['tags'] = {tagdict['id']: True for tagdict in division['tags']}
        return ret

    if action == 'load':
        return get_client_model(portal)
    else:
        new_tags = {t['id']: {'text': t.get('text', ''), 'description': t.get('description', '')} for t in
                    json['portal']['tags']}
        validated = portal.validate_tags(new_tags)
        if action == 'save':
            if validated['errors']:
                raise ValueError
            portal.set_tags(new_tags, json['portal']['divisions']).save()
            return get_client_model(portal)
        else:
            return validated
