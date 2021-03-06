from flask import render_template, request, url_for, g, redirect, abort
from sqlalchemy import and_, or_
from sqlalchemy.sql import expression

from .blueprints_declaration import company_bp
from .pagination import pagination, load_for_infinite_scroll
from .. import utils
from ..models.company import Company, UserCompany, NewsFeedCompany
from ..models.materials import Material, Publication
from ..models.pr_base import Grid
from ..models.translate import TranslateTemplate
from ..models.pr_base import PRBase
from ..models.portal import MemberCompanyPortal, MembershipPlan
from ..models.permissions import UserIsActive, CompanyIsActive, EmployeeHasRightAF, \
    EmployeeHasRightAtMembershipCompany, EmployeeHasRightAtCompany, RIGHT_AT_COMPANY, CheckFunction
from ..models.exceptions import UnauthorizedUser
from ..models import exceptions


@company_bp.route('/', methods=['GET'], permissions=UserIsActive())
def companies():
    return render_template('company/companies.html')


@company_bp.route('/', methods=['OK'], permissions=UserIsActive())
def companies_load(json):
    employments_query = utils.db.query_filter(UserCompany). \
        outerjoin(Company, and_(UserCompany.company_id == Company.id,
                                ~UserCompany.status.in_(UserCompany.DELETED_STATUSES),
                                Company.status == Company.STATUSES['COMPANY_ACTIVE'])). \
        filter(and_(UserCompany.user_id == g.user.id, Company.id != None, ~ UserCompany.id.in_(json['loaded']))). \
        order_by(expression.desc(UserCompany.md_tm))

    employments, there_is_more = load_for_infinite_scroll(employments_query, 3)

    return {'employments': [e.get_client_side_dict(fields='id,status, company, rights') for e in employments],
            'there_is_more': there_is_more,
            'actions': {'create_company': True}}


@company_bp.route('/search_for_company_to_join/', methods=['OK'], permissions=UserIsActive())
def search_for_company_to_join(json):
    companies, there_is_more = load_for_infinite_scroll(
        Company.search_for_company_to_employ(json['text'], json['loaded']), items=3)

    return {'companies': [company.get_client_side_dict() for company in companies],
            'there_is_more': there_is_more}


@company_bp.route('/join_to_company/', methods=['OK'],
                  permissions=UserIsActive() & CheckFunction(lambda json: CompanyIsActive().check(company_id = json['company_id'])))
def join_to_company(json):
    employment = \
        UserCompany.apply_user_to_company(company_id=json['company_id'])

    return {'employment': employment.get_client_side_dict(fields='id,status, company, rights')}


@company_bp.route('/create/', methods=['GET'], permissions=UserIsActive())
def update():
    return render_template('company/company_profile.html', rights_user_in_company={}, company=Company())


@company_bp.route('/<string:company_id>/profile/', methods=['GET'], permissions=UserIsActive())
def profile(company_id=None):
    company = utils.db.query_filter(Company, id=company_id).first()
    employment = UserCompany.get_by_user_and_company_ids(company_id=company_id)
    if employment:
        employment.md_tm = None
        employment.save()

    return render_template('company/company_profile.html', company=company)


@company_bp.route('/create/', methods=['OK'], permissions=UserIsActive())
@company_bp.route('/<string:company_id>/profile/', methods=['OK'],
                  permissions=EmployeeHasRightAF(load=True, validate=True,
                                                 save=RIGHT_AT_COMPANY.PORTAL_EDIT_PROFILE))
def profile_load_validate_save(json, company_id=None):
    action = g.req('action', allowed=['load', 'validate', 'save'])
    company = Company() if company_id is None else Company.get(company_id)
    if action == 'load':
        company_dict = company.get_client_side_dict()
        user_company = UserCompany.get_by_user_and_company_ids(company_id=company_id)
        if user_company:
            company_dict['actions'] = {
                'edit_company_profile': EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.COMPANY_EDIT_PROFILE).check(
                    company_id=company.id),
                'edit_portal_profile': EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.PORTAL_EDIT_PROFILE).check(
                    company_id=company.id)
            }
        return company_dict
    else:
        company.attr(
            utils.filter_json(json, 'about', 'address', 'country', 'email', 'web', 'name', 'phone', 'city', 'postcode',
                              'phone2', 'region', 'short_description', 'lon', 'lat'))
        if action == 'validate':
            if company_id is not None:
                company.detach()
            return company.validate(company_id is None)
        else:
            if company_id is None:
                company.setup_new_company().save()
            company.logo = json['logo']

        return utils.dict_merge(company.save().get_client_side_dict(), actions={'edit': True if company_id else False})


@company_bp.route('/<string:company_id>/employees/', methods=['GET'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY._ANY))
def employees(company_id):
    return render_template('company/company_employees.html',
                           employment=UserCompany.get_by_user_and_company_ids(company_id=company_id),
                           company=Company.get(company_id))


@company_bp.route('/<string:company_id>/employees/', methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY._ANY))
def employees_load(json, company_id):
    company = Company.get(company_id)
    return {
        'company': company.get_client_side_dict(fields='id,name'),
        'grid_data': [e.employees_grid_row() for e in company.employments_objectable_for_company]
    }


@company_bp.route('/<string:company_id>/employment/<string:employment_id>/change_status/<string:new_status>/',
                  methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE))
def change_employment_status_by_company(json, company_id, employment_id, new_status):
    employment = UserCompany.get(employment_id)
    if utils.find_by_keys(employment.status_changes_by_company(), new_status, 'status')['enabled'] is True:
        employment.NOTIFY_STATUS_CHANGED_BY_COMPANY(new_status=new_status, old_status=employment.status)
        employment.status = new_status
        return employment.employees_grid_row()
    else:
        raise UnauthorizedUser()


@company_bp.route('/<string:company_id>/employment/<string:employment_id>/set_rights/', methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS))
def set_rights(json, company_id, employment_id):
    employment = UserCompany.get(employment_id)
    employment.rights = json
    return employment.save().employees_grid_row()


@company_bp.route('/<string:company_id>/employment/<string:employment_id>/change_position/', methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS))
def employment_change_position(json, company_id, employment_id):
    employment = UserCompany.get(employment_id)
    employment.position = json['position']
    return employment.save().employees_grid_row()


@company_bp.route('/<string:company_id>/portal_memberees/', methods=['GET'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY._ANY))
def portal_memberees(company_id):
    return render_template('company/portals_memberees.html',
                           company=Company.get(company_id),
                           actions={'require_memberee':
                               EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS).check(
                                   company_id=company_id)})


@company_bp.route('/<string:company_id>/portal_memberees/', methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY._ANY))
def portal_memberees_load(json, company_id):
    subquery = Company.subquery_portal_partners(company_id, json.get('filter'),
                                                filters_exсept=MemberCompanyPortal.DELETED_STATUSES)
    memberships, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    return {'page': current_page,
            'grid_data': [membership.portal_memberee_grid_row() for membership in memberships],
            'grid_filters': {},
            'grid_filters_except': MemberCompanyPortal.DELETED_STATUSES,
            'total': count}


@company_bp.route('/<string:company_id>/search_for_portal_to_join/', methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS))
def search_for_portal_to_join(json, company_id):
    from ..models.portal import MemberCompanyPortal
    return MemberCompanyPortal.search_for_portal_to_join(company_id, json['search'])


@company_bp.route('/<string:company_id>/join_to_portal/', methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS))
def join_to_portal(json, company_id):
    return MemberCompanyPortal.apply_company_to_portal(company_id=company_id, portal_id=json['portal_id']) \
        .portal_memberee_grid_row()


from profapp.models.translate import Phrase


@company_bp.route('/membership/<string:membership_id>/change_status/<string:new_status>/', methods=['OK'],
                  permissions=EmployeeHasRightAtMembershipCompany(RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS))
def change_membership_status_by_company(json, membership_id, new_status):
    membership = MemberCompanyPortal.get(membership_id)

    if utils.find_by_keys(membership.status_changes_by_company(), new_status, 'status')['enabled'] is True:

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
        membership.NOTIFY_STATUS_CHANGED_BY_COMPANY(new_status=membership.status, old_status=old_status,
                                                    more_phrases_to_portal=more_phrases,
                                                    more_phrases_to_company=more_phrases)

        return membership.portal_memberee_grid_row()
    else:
        raise UnauthorizedUser()


@company_bp.route('/membership/<string:membership_id>/request_membership_plan/', methods=['OK'],
                  permissions=EmployeeHasRightAtMembershipCompany(RIGHT_AT_COMPANY.COMPANY_MANAGE_PARTICIPATION))
def request_membership_plan(json, membership_id):
    action = g.req('action', allowed=['load', 'save', 'validate'])
    membership = MemberCompanyPortal.get(membership_id)
    if action == 'load':
        return membership.get_client_side_dict_for_plan()
    else:
        immediately = True if json['membership']['request_membership_plan_issued_immediately'] else False
        requested_plan_id = json.get('selected_by_user_plan_id', None)
        if action == 'validate':
            ret = PRBase.DEFAULT_VALIDATION_ANSWER()
            # if we can apply it immediately and it have to be confirmed by portal company owner
            if (requested_plan_id is True and not membership.requested_membership_plan_issued.auto_apply) \
                    or (requested_plan_id is not False and requested_plan_id is not True and
                            not MembershipPlan.get(requested_plan_id).auto_apply and
                                requested_plan_id != membership.portal.default_membership_plan_id):
                ret['warnings']['general'] = 'plan must be confirmed by company owner before activation'
            return ret
        else:
            return membership.requested_new_plan_issued(requested_plan_id, immediately).portal_memberee_grid_row()


@company_bp.route('/<string:company_id>/materials/', methods=['GET'],
                  permissions=EmployeeHasRightAtCompany())
def materials(company_id):
    return render_template('company/materials.html', company=utils.db.query_filter(Company, id=company_id).one(),
                           source_type='profireader',
                           actions={'CREATE_MATERIAL': EmployeeHasRightAtCompany().check(company_id=company_id)})


@company_bp.route('/<string:company_id>/materials/', methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY._ANY))
def materials_load(json, company_id):
    subquery = Material.subquery_company_materials(company_id, json.get('filter'), json.get('sort'), source_type='profireader').order_by(
        expression.desc(Material.cr_tm))
    materials, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    return {'grid_data': [material.material_grid_row() for material in materials],
            'grid_filters': {},
            'total': count
            }


@company_bp.route('/<string:company_id>/materials_from_feeds/', methods=['GET'],
                  permissions=EmployeeHasRightAtCompany())
def materials_from_feeds(company_id):
    return render_template('company/materials.html',
                           company=utils.db.query_filter(Company, id=company_id).one(),
                           source_type='rss',
                           actions={})


@company_bp.route('/<string:company_id>/materials_from_feeds/', methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY._ANY))
def materials_from_feeds_load(json, company_id):
    subquery = Material.subquery_company_materials(company_id, json.get('filter'), json.get('sort'), source_type='rss').order_by(
        expression.desc(Material.cr_tm))
    materials, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    return {'grid_data': [material.material_grid_row() for material in materials],
            'grid_filters': {},
            'total': count
            }


@company_bp.route('/<string:company_id>/news_feeds/', methods=['GET'], permissions=EmployeeHasRightAtCompany())
def news_feeds(company_id):
    return render_template('company/news_feeds.html', company=utils.db.query_filter(Company, id=company_id).one())




def del_news_feeds_load(json, company_id):


    subquery = NewsFeedCompany.subquery_company_news_feed(company_id, json.get('filter'), json.get('sort')).order_by(
        expression.desc(NewsFeedCompany.cr_tm))
    news_feeds, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    return {'news_feeds': [news_feeds.material_grid_row() for news_feed in news_feeds], 'total': count}


@company_bp.route('/<string:company_id>/news_feeds/', methods=['OK'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY._ANY))
def news_feeds_load(json, company_id):
    action = g.req('action', allowed=['load', 'save', 'validate'])



    company = Company.get(company_id)

    def client_side():
        client_dict = {
            'news_feeds': utils.get_client_side_list(company.news_feeds),
            'select': {
                'news_feed_types': ['rss']
            }
        }
        # for news_feed in client_dict['plans']:
        #     plan['duration'], plan['duration_unit'] = plan['duration'].split(' ')

        return client_dict

    if action != 'load':
        if set(company.news_feeds) - set(utils.find_by_id(company.news_feeds, d['id']) for d in json['news_feeds']) != set():
            raise exceptions.BadDataProvided('Information for some existing news_feeds is not provided by client')

        # plan_position = 0
        validation = PRBase.DEFAULT_VALIDATION_ANSWER()
        default_plan = 0

        for nf in json['news_feeds']:
            news_feed = utils.find_by_id(company.news_feeds, nf['id']) or NewsFeedCompany(company=company, id=nf['id'])

            if nf.get('status', '') == 'DELETED':
                company.news_feeds.remove(news_feed)
            else:
                news_feed.company = company
                # plan.position = plan_position
                news_feed.attr_filter(nf, 'name', 'source')
                news_feed.type = 'RSS'
                # plan.duration = "%s %s" % (nf['duration'], nf['duration_unit'])

                if news_feed not in company.news_feeds:
                    company.news_feeds.append(news_feed)

                # if nf['id'] == json['select']['portal'].get('default_membership_plan_id', None) and plan.status == \
                #         MembershipPlan.STATUSES['MEMBERSHIP_PLAN_ACTIVE']:
                #     default_plan += 1
                #     portal.default_membership_plan = plan
                #
                # plan_position += 1

        company.validation_append_by_ids(validation, company.news_feeds, 'news_feeds')
        # if default_plan != 1:
        #     validation['errors']['one_default_active_plan'] = 'You need one and only one default plan'

        if action == 'validate':
            g.db.expunge_all()
            return validation
        else:
            for news_feed in company.news_feeds:
                if not news_feed.cr_tm:
                    news_feed.id = None

            if not len(validation['errors']):
                company.save()
                g.db.commit()

    return client_side()
