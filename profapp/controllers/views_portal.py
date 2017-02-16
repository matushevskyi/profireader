from flask import render_template, g, redirect, url_for
from sqlalchemy import desc
from config import Config
from profapp.controllers.errors import BadDataProvided
from .blueprints_declaration import portal_bp
from .pagination import pagination
from .. import utils
from ..models.company import Company
from ..models.company import UserCompany
from ..models.dictionary import Currency
from ..models.materials import Publication
from ..models.portal import MemberCompanyPortal, Portal, PortalLayout, PortalDivision, \
    PortalAdvertisment, PortalAdvertismentPlace, MembershipPlan
from ..models.portal import PortalDivisionType
from ..models.pr_base import PRBase, Grid
from ..models.tag import Tag
from ..models.translate import TranslateTemplate
from ..models.exceptions import UnauthorizedUser
from profapp.models.translate import Phrase
from profapp.models import permissions


@portal_bp.route('/create/company/<string:company_id>/', methods=['GET'])
@portal_bp.route('/<string:portal_id>/profile/', methods=['GET'])
# @check_right(EditPortalRight, ['company_id'])
def profile(company_id=None, portal_id=None):
    if portal_id:
        portal = Portal.get(portal_id)
        company = portal.own_company
    else:
        company = Company.get(company_id)
        portal = None
    return render_template('portal/portal_edit.html', company=company, portal_id=portal.id if portal else None)


@portal_bp.route('/create/company/<string:company_id>/', methods=['OK'])
@portal_bp.route('/<string:portal_id>/profile/', methods=['OK'])
def profile_load(json, company_id=None, portal_id=None):
    action = g.req('action', allowed=['load', 'save', 'validate'])
    layouts = utils.db.query_filter(PortalLayout).all()
    division_types = PortalDivisionType.get_division_types()
    portal = Portal.get(portal_id) if portal_id else Portal.launch_new_portal(Company.get(company_id))

    client_side = lambda: {
        'select': {
            'languages': Config.LANGUAGES,
            'layouts': utils.get_client_side_list(layouts),
            'division_types': utils.get_client_side_dict(division_types)
        },
        'portal': portal.get_client_side_dict(
            fields='name,host, logo, favicon, lang, url_facebook, url_google, url_twitter, url_linkedin,'
                   'portal_layout_id,divisions,divisions.html_description|html_keywords|html_title|cr_tm|name,own_company,company_memberships.company',
            get_own_or_profi_host=True, get_publications_count=True)
    }

    if action == 'load':
        return client_side()
    else:
        jp = json['portal']

        jp['host'] = (jp['host_profi'] + '.' + Config.MAIN_DOMAIN) if jp['host_profi_or_own'] == 'profi' else jp[
            'host_own']

        portal.attr_filter(jp, 'name', 'lang', 'portal_layout_id', 'host',
                           *map(lambda x: 'url_' + x, ['facebook', 'google', 'twitter', 'linkedin']))

        if set(portal.divisions) - set(utils.find_by_id(portal.divisions, d['id']) for d in jp['divisions']) != set():
            raise BadDataProvided('Information for some existing portal division is not provided by client')

        division_position = 0
        unpublish_warning = {}
        changed_division_types = {}
        deleted_divisions = []
        for jd in jp['divisions']:
            ndi = utils.find_by_id(portal.divisions, jd['id']) or PortalDivision(portal=portal, id=jd['id'])
            if jd.get('remove_this_existing_division', None):
                deleted_divisions.append(ndi)
                if len(ndi.publications):
                    utils.dict_deep_replace(
                        'this division have %s published articles. they will be unpublished' % (len(ndi.publications),),
                        unpublish_warning, ndi.id, 'actions')
                portal.divisions.remove(ndi)
            else:
                ndi.portal = portal
                ndi.position = division_position
                ndi.attr_filter(jd, 'name', 'html_title', 'html_keywords', 'html_description')

                if ndi in portal.divisions:
                    if len(ndi.publications) and jd['portal_division_type_id'] != ndi.portal_division_type.id:
                        changed_division_types[ndi.id] = ndi.portal_division_type.id
                        utils.dict_deep_replace(
                            'this division have %s published articles. they will be unpublished becouse of division type changed' % (
                                len(ndi.publications),), unpublish_warning, ndi.id, 'type')
                else:
                    portal.divisions.append(ndi)

                ndi.portal_division_type = utils.find_by_id(division_types, jd['portal_division_type_id'])
                ndi.settings = jd.get('settings', {})

                division_position += 1

        if action == 'validate':
            ret = portal.validate(not portal_id)
            if len(unpublish_warning.keys()):
                if 'divisions' not in ret['warnings']:
                    ret['warnings']['divisions'] = {}
                ret['warnings']['divisions'] = utils.dict_merge_recursive(ret['warnings']['divisions'],
                                                                          unpublish_warning)
            g.db.expunge_all()
            return ret
        else:
            for nd in portal.divisions:
                if not nd.cr_tm:
                    nd.id = None
            portal.logo = jp['logo']
            portal.favicon = jp['favicon']
            for del_div in deleted_divisions:
                del_div.notify_company_about_deleted_publications('deleted')

            for div in portal.divisions:
                if div.id in changed_division_types:
                    div.notify_company_about_deleted_publications('type changed')
                    div.publications = []

            if not portal_id:
                g.db.add(portal)
                portal.company_memberships[0].current_membership_plan_issued = portal.company_memberships[
                    0].create_issued_plan()
                portal.company_memberships[0].current_membership_plan_issued.start()
                UserCompany.get_by_user_and_company_ids(company_id=company_id). \
                    NOTIFY_PORTAL_CREATED(portal_host=portal.host, portal_name=portal.name)
            #                portal.own_company.notifications_company_changes(
            #                    notification_type=NOTIFICATION_TYPES['PORTAL_ACTIVITY'],
            #                    what_happened="portal %s was created" % (utils.jinja.link_external()),
            #                    rights_at_company=RIGHT_AT_COMPANY.PORTAL_EDIT_PROFILE,
            #                    additional_dict={'portal': portal})

            portal.save()

            g.db.commit()
            return client_side()


@portal_bp.route('/<string:portal_id>/readers/', methods=['GET'])
@portal_bp.route('/<string:portal_id>/readers/<int:page>/', methods=['GET'])
def readers(portal_id, page=1):
    portal = Portal.get(portal_id)
    company = portal.own_company
    company_readers, pages, page, count = pagination(query=company.readers_query, page=page)

    reader_fields = ('id', 'email', 'nickname', 'first_name', 'last_name')
    company_readers_list_dict = list(map(lambda x: dict(zip(reader_fields, x)), company_readers))

    return render_template('portal/readers.html',
                           company=company, portal=portal,
                           companyReaders=company_readers_list_dict,
                           pages=pages,
                           current_page=page,
                           page_buttons=Config.PAGINATION_BUTTONS,
                           search_text=None,
                           )


@portal_bp.route('/<string:portal_id>/readers/', methods=['OK'])
# @check_right(UserIsEmployee, ['portal_id'])
def readers_load(json, portal_id):
    portal = Portal.get(portal_id)
    company = portal.own_company
    company_readers, pages, page, count = pagination(query=company.get_readers_for_portal(json.get('filter')),
                                                     **Grid.page_options(json.get('paginationOptions')))
    return {'grid_data': [reader.get_client_side_dict(
        'id,address_email,full_name,first_name,last_name') for reader in
                          company_readers],
            'total': count
            }


@portal_bp.route('/<string:portal_id>/plans/', methods=['GET'])
# @check_right(EditPortalRight, ['portal_id'])
def plans(portal_id):
    portal = Portal.get(portal_id)
    return render_template('portal/plans_edit.html', portal=portal, company=portal.own_company)


@portal_bp.route('/<string:portal_id>/plans/', methods=['OK'])
# @check_right(EditPortalRight, ['portal_id'])
def plans_load(json, portal_id):
    action = g.req('action', allowed=['load', 'save', 'validate'])
    portal = Portal.get(portal_id)

    def client_side():
        client_dict = {
            'plans': utils.get_client_side_list(portal.plans),
            'select': {
                'portal': portal.get_client_side_dict(more_fields='default_membership_plan_id'),
                'currency': Currency.get_all_active_ordered_by_position(),
                'duration_unit': MembershipPlan.DURATION_UNITS
            }
        }
        for plan in client_dict['plans']:
            plan['duration'], plan['duration_unit'] = plan['duration'].split(' ')

        return client_dict

    if action != 'load':
        if set(portal.plans) - set(utils.find_by_id(portal.plans, d['id']) for d in json['plans']) != set():
            raise BadDataProvided('Information for some existing plans is not provided by client')

        plan_position = 0
        validation = PRBase.DEFAULT_VALIDATION_ANSWER()
        default_plan = 0

        for jp in json['plans']:
            plan = utils.find_by_id(portal.plans, jp['id']) or MembershipPlan(portal=portal, id=jp['id'])

            plan.portal = portal
            plan.position = plan_position
            plan.attr_filter(jp, 'name', 'default', 'price', 'currency_id', 'status', 'auto_apply',
                             *['publication_count_' + t for t in ['open', 'payed', 'registered']])
            plan.duration = "%s %s" % (jp['duration'], jp['duration_unit'])

            if plan not in portal.plans:
                portal.plans.append(plan)

            if jp['id'] == json['select']['portal'].get('default_membership_plan_id', None) and plan.status == \
                    MembershipPlan.STATUSES['MEMBERSHIP_PLAN_ACTIVE']:
                default_plan += 1
                portal.default_membership_plan = plan

            plan_position += 1

        portal.validation_append_by_ids(validation, portal.plans, 'plans')
        if default_plan != 1:
            validation['errors']['one_default_active_plan'] = 'You need one and only one default plan'

        if action == 'validate':
            g.db.expunge_all()
            return validation
        else:
            for plan in portal.plans:
                if not plan.cr_tm:
                    plan.id = None

            if not len(validation['errors']):
                portal.save()
                g.db.commit()

    return client_side()


@portal_bp.route('/membership/<string:membership_id>/set_membership_plan/', methods=['OK'])
def set_membership_plan(json, membership_id):
    action = g.req('action', allowed=['load', 'save', 'validate'])
    membership = MemberCompanyPortal.get(membership_id)
    if action == 'load':
        return membership.get_client_side_dict_for_plan()
    else:
        immediately = True if json['membership']['request_membership_plan_issued_immediately'] else False
        requested_plan_id = json.get('selected_by_user_plan_id', None)
        if action == 'validate':
            ret = PRBase.DEFAULT_VALIDATION_ANSWER()
            if not requested_plan_id:
                ret['errors']['general'] = 'pls select membership plan'
            return ret
        else:
            return membership.set_new_plan_issued(requested_plan_id, immediately).company_member_grid_row()


@portal_bp.route('/<string:portal_id>/banners/', methods=['GET'])
# @check_right(UserIsEmployee, 'portal_id')
def banners(portal_id):
    portal = Portal.get(portal_id)
    return render_template('portal/banners.html', portal=portal, company=portal.own_company)


@portal_bp.route('/<string:portal_id>/banners/', methods=['OK'])
# @check_right(UserIsEmployee, 'portal_id')
def banners_load(json, portal_id):
    portal = Portal.get(portal_id)
    if 'action_name' in json:
        if json['action_name'] == 'create':
            place = utils.db.query_filter(PortalAdvertismentPlace, portal_layout_id=portal.portal_layout_id,
                                          place=json['row']['place']).one()
            newrow = PortalAdvertisment(portal_id=portal.id, html=place.default_value if place.default_value else '',
                                        place=json['row']['place']).save()
            return {'grid_action': 'refresh_row', 'row': newrow.get_client_side_dict()}

        elif json['action_name'] == 'delete':
            PortalAdvertisment.get(json['id']).delete()
            return {'grid_action': 'delete_row'}
        elif json['action_name'] == 'set_default':
            adv = PortalAdvertisment.get(json['id'])
            place = utils.db.query_filter(PortalAdvertismentPlace, portal_layout_id=portal.portal_layout_id,
                                          place=adv.place).one()
            adv.html = place.default_value
            adv.save()
            return {}
    else:
        banners = PortalAdvertisment.get_portal_advertisments(portal)
        return {'page': 1,
                'grid_data': banners,
                'grid_filters': {},
                'total': len(banners)}


@portal_bp.route('/<string:portal_id>/save_banners/', methods=['OK'])
# @check_right(UserIsEmployee, 'portal_id')
def save_portal_banner(json, portal_id):
    advertisment = PortalAdvertisment.get(json.get('editBanners')['id'])
    advertisment.html = json.get('editBanners')['html']
    advertisment.save()
    return advertisment.get_client_side_dict()


@portal_bp.route('/membership/<string:membership_id>/set_tags/', methods=['OK'])
# @check_right(RequireMembereeAtPortalsRight, ['company_id'])
def membership_set_tags(json, membership_id):
    membership = MemberCompanyPortal.get(membership_id)
    action = g.req('action', allowed=['load', 'validate', 'save'])
    if action == 'load':
        # catalog_division = g.db.query(PortalDivision).filter(and_(PortalDivision.portal_id == portal_id,
        #                                                     PortalDivision.portal_division_type_id == 'catalog')).first()
        return {
            'membership': membership.get_client_side_dict(fields='id,portal,company,tags,portal.divisions'),
        }
    else:
        membership.tags = [Tag.get(t['id']) for t in json['membership']['tags']]

        if action == 'validate':
            membership.detach()
            return PRBase.DEFAULT_VALIDATION_ANSWER()
        else:
            membership.save().set_tags_positions()
            return {'membership': membership.portal_memberee_grid_row()}

@portal_bp.route('/membership/<string:membership_id>/change_status/<string:new_status>/', methods=['OK'])
def membership_change_status(json, membership_id, new_status):
    membership = MemberCompanyPortal.get(membership_id)

    if utils.find_by_keys(membership.status_changes_by_portal(), 'status', new_status)['enabled'] is True:
        old_status = membership.status
        membership.status = new_status

        more_phrases = []
        if new_status in MemberCompanyPortal.DELETED_STATUSES:
            membership.current_membership_plan_issued.stop()

        elif new_status == MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE'] and old_status != new_status and \
                not membership.current_membership_plan_issued.started_tm:
            membership.current_membership_plan_issued.start()
            more_phrases = Phrase("started new plan `%(new_plan_name)s` by membership activation by portal",
                                  dict={'new_plan_name': membership.current_membership_plan_issued.name})

        membership.save()
        membership.NOTIFY_STATUS_CHANGED_BY_PORTAL(new_status=new_status, old_status=old_status,
                                                   more_phrases_to_portal=more_phrases,
                                                   more_phrases_to_company=more_phrases
                                                   )

        return membership.company_member_grid_row()
    else:
        raise UnauthorizedUser()


@portal_bp.route('/<string:portal_id>/companies_members/', methods=['GET'])
# @check_right(UserIsEmployeeAtPortalOwner, ['portal_id'])
def companies_members(portal_id):
    portal = Portal.get(portal_id)
    return render_template('portal/companies_members.html',
                           portal=portal,
                           employment=UserCompany.get_by_user_and_company_ids(
                               company_id=portal.company_owner_id).get_client_side_dict()
                           )


@portal_bp.route('/<string:portal_id>/companies_members/', methods=['OK'])
# @check_right(UserIsEmployeeAtPortalOwner, ['portal_id'])
def companies_members_load(json, portal_id):
    portal = Portal.get(portal_id)
    subquery = Company.subquery_company_partners(portal.company_owner_id, json.get('filter'),
                                                 filters_exсept=MemberCompanyPortal.DELETED_STATUSES)
    memberships, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))
    return {'grid_data': [membership.company_member_grid_row() for membership in memberships],
            'grid_filters': {},
            'grid_filters_except': MemberCompanyPortal.DELETED_STATUSES,
            'total': count,
            'page': current_page}


@portal_bp.route('/company/<string:company_id>/publications/', methods=['GET'])
def old_publications_url(company_id):
    # this url is presented in sent notificatuions
    return redirect(url_for('portal.publications', portal_id=Company.get(company_id).own_portal.id))


@portal_bp.route('/<string:portal_id>/publications/', methods=['GET'])
# @check_right(UserIsEmployee, ['company_id'])
def publications(portal_id):
    portal = Portal.get(portal_id)
    membership = MemberCompanyPortal.get_by_portal_id_company_id(company_id=portal.company_owner_id, portal_id=portal.id)
    return render_template('portal/portal_publications.html', company=portal.own_company,
                           portal=portal, membership = membership)


@portal_bp.route('/<string:portal_id>/publications/', methods=['OK'])
def publications_load(json, portal_id):
    portal = Portal.get(portal_id)
    company = portal.own_company
    membership = MemberCompanyPortal.get_by_portal_id_company_id(company_id=company.id, portal_id=portal.id)

    publications = utils.db.query_filter(Publication).join(PortalDivision,
                                                           PortalDivision.id == Publication.portal_division_id). \
        filter(PortalDivision.portal_id == portal.id).order_by(desc(Publication.publishing_tm)).all()

    return {'company': company.get_client_side_dict(),
            'portal': portal.get_client_side_dict(),
            'rights_user_in_company': UserCompany.get_by_user_and_company_ids(company_id=company.id).rights,
            'grid_data': [p.portal_publication_grid_row(membership) for p in publications],
            'total': len(publications)}


@portal_bp.route('/<string:portal_id>/tags/', methods=['GET'])
# @check_right(UserIsEmployee, 'portal_id')
def tags(portal_id):
    portal = Portal.get(portal_id)
    return render_template('portal/tags.html', portal=portal, company=portal.own_company)


@portal_bp.route('/<string:portal_id>/tags/', methods=['OK'])
# @check_right(UserIsEmployee, 'portal_id')
def tags_load(json, portal_id):
    action = g.req('action', allowed=['load', 'save', 'validate'])
    portal = Portal.get(portal_id)
    company = portal.own_company

    def get_client_model(aportal):
        portal_dict = aportal.get_client_side_dict()
        portal_dict['divisions'] = [division for division in portal_dict['divisions']
                                    if division['portal_division_type_id'] in ['news', 'events', 'catalog']]
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


@portal_bp.route('/<string:company_id>/translations/', methods=['GET'])
# @check_right(UserIsActive)
def translations(company_id):
    company = Company.get(company_id)
    portal = company.own_portal
    return render_template('portal/translations.html', portal=portal)


@portal_bp.route('/<string:company_id>/translations/', methods=['OK'])
# @check_right(UserIsActive)
def translations_load(json, company_id):
    company = Company.get(company_id)
    portal = company.own_portal
    subquery = TranslateTemplate.subquery_search({'portal.name': portal.name}, json.get('sort'), json.get('editItem'))

    translations, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    # grid_filters = {
    #     'template': [{'value': portal[0], 'label': portal[0]} for portal in
    #                  db(TranslateTemplate.template).group_by(TranslateTemplate.template) \
    #                      .order_by(expression.asc(expression.func.lower(TranslateTemplate.template))).all()],
    #     'url': [{'value': portal[0], 'label': portal[0]} for portal in
    #             db(TranslateTemplate.url).group_by(TranslateTemplate.url) \
    #                 .order_by(expression.asc(expression.func.lower(TranslateTemplate.url))).all()]
    # }
    return {'grid_data': [translation.get_client_side_dict() for translation in translations], 'total': count}


@portal_bp.route('/membership/<string:membership_id>/set_rights/', methods=['OK'])
# @check_right(RequireMembereeAtPortalsRight, ['company_id'])
def membership_set_rights(json, membership_id):
    membership = MemberCompanyPortal.get(membership_id)
    membership.rights = json
    return membership.company_member_grid_row()
