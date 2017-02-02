from flask import render_template, request, url_for, g, redirect, abort
from sqlalchemy import and_, or_
from sqlalchemy.sql import expression

from .blueprints_declaration import company_bp
from .pagination import pagination, load_for_infinite_scroll
from .. import utils
from ..models.company import Company, UserCompany
from ..models.materials import Material, Publication
from ..models.pr_base import Grid
from ..models.rights import CanCreateCompanyRight, BaseRightsEmployeeInCompany, \
    MembershipRights, RequireMembereeAtPortalsRight
from ..models.translate import TranslateTemplate
from ..models.pr_base import PRBase
from ..models.portal import MemberCompanyPortal, MembershipPlan
from ..models.permissions import user_is_active, company_is_active, employee_af, employee_have_right, RIGHT_AT_COMPANY
from ..models.exceptions import UnauthorizedUser


@company_bp.route('/', methods=['GET'], permissions=user_is_active)
def companies():
    return render_template('company/companies.html')


@company_bp.route('/', methods=['OK'], permissions=user_is_active)
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
            'actions': {'create_company': CanCreateCompanyRight(user=g.user).is_allowed()}}


@company_bp.route('/search_for_company_to_join/', methods=['OK'], permissions=user_is_active)
def search_for_company_to_join(json):
    companies, there_is_more = load_for_infinite_scroll(
        Company.search_for_company_to_employ(json['text'], json['loaded']),
        # utils.db.query_filter(Company).filter(
        #     ~g.db.query(UserCompany).filter(and_(UserCompany.user_id == g.user.id, UserCompany.company_id == Company.id,
        #                                          or_(UserCompany.status == UserCompany.STATUSES['APPLICANT'],
        #                                              UserCompany.status == UserCompany.STATUSES['SUSPENDED'],
        #                                              UserCompany.status == UserCompany.STATUSES['EMPLOYMENT_ACTIVE'],
        #                                              UserCompany.status == UserCompany.STATUSES['FROZEN']))).exists()). \
        #     filter(and_(
        #     Company.status == 'ACTIVE', Company.name.ilike("%" + json['text'] + "%")), ~Company.id.in_(json['loaded'])). \
        #     order_by(Company.name),
        items=3)

    return {'companies': [company.get_client_side_dict() for company in companies],
            'there_is_more': there_is_more}


@company_bp.route('/join_to_company/', methods=['OK'],
                  permissions=[user_is_active, utils.json2kwargs(company_is_active)])
def join_to_company(json):
    employment = \
        UserCompany.apply_user_to_company(company_id=json['company_id'])

    return {'employment': employment.get_client_side_dict(fields='id,status, company, rights')}


@company_bp.route('/create/', methods=['GET'], permissions=user_is_active)
def update():
    return render_template('company/company_profile.html', rights_user_in_company={}, company=Company())


@company_bp.route('/<string:company_id>/profile/', methods=['GET'], permissions=user_is_active)
def profile(company_id=None):
    company = utils.db.query_filter(Company, id=company_id).first()
    employment = UserCompany.get_by_user_and_company_ids(company_id=company_id)
    if employment:
        employment.md_tm = None
        employment.save()

    return render_template('company/company_profile.html',
                           user_is_employee=employment is not None,
                           company=company)


@company_bp.route('/create/', methods=['OK'], permissions=user_is_active)
@company_bp.route('/<string:company_id>/profile/', methods=['OK'],
                  permissions=employee_af(load=True, validate=True,
                                          save=RIGHT_AT_COMPANY.PORTAL_EDIT_PROFILE))
def profile_load_validate_save(json, company_id=None):
    action = g.req('action', allowed=['load', 'validate', 'save'])
    company = Company() if company_id is None else Company.get(company_id)
    if action == 'load':
        company_dict = company.get_client_side_dict()
        user_company = UserCompany.get_by_user_and_company_ids(company_id=company_id)
        if user_company:
            company_dict['actions'] = {
                'edit_company_profile': employee_have_right(RIGHT_AT_COMPANY.COMPANY_EDIT_PROFILE)(
                    company_id=company.id),
                'edit_portal_profile': employee_have_right(RIGHT_AT_COMPANY.PORTAL_EDIT_PROFILE)(company_id=company.id)
            }
        return company_dict
    else:
        company.attr(
            utils.filter_json(json, 'about', 'address', 'country', 'email', 'name', 'phone', 'city', 'postcode',
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


@company_bp.route('/<string:company_id>/employees/', methods=['GET'], permissions=employee_have_right())
def employees(company_id):
    return render_template('company/company_employees.html',
                           employment=UserCompany.get_by_user_and_company_ids(company_id=company_id),
                           company=Company.get(company_id))


@company_bp.route('/<string:company_id>/employees/', methods=['OK'], permissions=employee_have_right())
def employees_load(json, company_id):
    company = Company.get(company_id)
    return {
        'company': company.get_client_side_dict(fields='id,name'),
        'grid_data': [e.employees_grid_row() for e in company.employments_objectable_for_company]
    }


@company_bp.route('/<string:company_id>/employment/<string:employment_id>/change_status/<string:new_status>/',
                  methods=['OK'],
                  permissions=employee_have_right(RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE))
def change_employment_status_by_company(json, company_id, employment_id, new_status):
    employment = UserCompany.get(employment_id)
    if utils.find_by_key(employment.status_changes_by_company(), 'status', new_status)['enabled'] is True:
        employment.NOTIFY_STATUS_CHANGED_BY_COMPANY(new_status=new_status, old_status=employment.status)
        employment.status = new_status
        return employment.employees_grid_row()
    else:
        raise UnauthorizedUser()


@company_bp.route('/<string:company_id>/employment/<string:employment_id>/set_rights/', methods=['OK'],
                  permissions=employee_have_right(RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS))
def set_rights(json, company_id, employment_id):
    employment = UserCompany.get(employment_id)
    employment.rights = json
    return employment.save().employees_grid_row()


@company_bp.route('/<string:company_id>/employment/<string:employment_id>/change_position/', methods=['OK'],
                  permissions=employee_have_right(RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS))
def employment_change_position(json, company_id, employment_id):
    employment = UserCompany.get(employment_id)
    employment.position = json['position']
    return employment.save().employees_grid_row()


# @company_bp.route('/search_for_user/<string:company_id>', methods=['OK'])
# # @check_right(UserIsActive)
# def search_for_user(json, company_id):
#     users = UserCompany().search_for_user_to_join(company_id, json['search'])
#     return users


# @company_bp.route('/send_article_to_user/', methods=['OK'])
# # @check_right(UserIsActive)
# def send_article_to_user(json):
#     return {'user': json['send_to_user']}


# @company_bp.route('/add_subscriber/', methods=['POST'])
# # @check_right(UserIsActive)
# def confirm_subscriber():
#     company_role = UserCompany()
#     data = request.form
#     company_role.apply_request(company_id=data['company_id'],
#                                user_id=data['user_id'],
#                                bool=data['req'])
#     return redirect(url_for('company.profile', company_id=data['company_id']))

# @company_bp.route('/search_to_submit_article/', methods=['POST'])
# # @check_right(UserIsActive)
# def search_to_submit_article(json):
#     companies = Company().search_for_company(g.user.id, json['search'])
#     return companies


@company_bp.route('/<string:company_id>/portal_memberees/', methods=['GET'], permissions=employee_have_right())
def portal_memberees(company_id):
    return render_template('company/portals_memberees.html',
                           company=Company.get(company_id),
                           actions={'require_memberee':
                               employee_have_right(RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS)(
                                   company_id=company_id)})


@company_bp.route('/<string:company_id>/portal_memberees/', methods=['OK'], permissions=employee_have_right())
def portal_memberees_load(json, company_id):
    subquery = Company.subquery_portal_partners(company_id, json.get('filter'),
                                                filters_exсept=MemberCompanyPortal.DELETED_STATUSES)
    memberships, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    return {'page': current_page,
            'grid_data': [membership.portal_memberee_grid_row() for membership in memberships],
            'grid_filters': {k: [{'value': None, 'label': TranslateTemplate.getTranslate('', '__-- all --')}] + v for
                             (k, v) in {'status': [{'value': status, 'label': status} for status in
                                                   MembershipRights.STATUSES]}.items()},
            'grid_filters_except': MemberCompanyPortal.DELETED_STATUSES,
            'total': count}


@company_bp.route('/<string:company_id>/search_for_portal_to_join/', methods=['OK'],
                  permissions=employee_have_right(RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS))
def search_for_portal_to_join(json, company_id):
    from ..models.portal import Portal
    return Portal.search_for_portal_to_join(company_id, json['search'])


@company_bp.route('/<string:company_id>/join_to_portal/', methods=['OK'],
                  permissions=employee_have_right(
                      RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS))
def join_to_portal(json, company_id):
    return MemberCompanyPortal.apply_company_to_portal(company_id=company_id, portal_id=json['portal_id']) \
        .portal_memberee_grid_row()


def employee_have_right_at_membership(right):
    return lambda json, membership_id, *args, **kwargs: employee_have_right(right)(
        company_id=MemberCompanyPortal.get(membership_id).company_id)


@company_bp.route('/membership/<string:membership_id>/change_status/<string:new_status>/', methods=['OK'],
                  permissions=employee_have_right_at_membership(
                      RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS))
def change_membership_status_by_company(json, membership_id, new_status):
    membership = MemberCompanyPortal.get(membership_id)

    if utils.find_by_key(membership.status_changes_by_company(), 'status', new_status)['enabled'] is True:

        old_status = membership.status
        membership.status = new_status

        membership.NOTIFY_STATUS_CHANGED_BY_COMPANY(new_status=membership.status, old_status=old_status)

        if new_status in MemberCompanyPortal.DELETED_STATUSES:
            membership.current_membership_plan_issued.stop()

        elif new_status == MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE'] and old_status != new_status and \
                not membership.current_membership_plan_issued.started_tm:
            membership.current_membership_plan_issued.start()

            membership.NOTIFY_PLAN_STARTED_BY_MEMBERSHIP_ACTIVATION_BY_COMPANY(
                new_plan_name=membership.current_membership_plan_issued.name)

        membership.save()

        return membership.portal_memberee_grid_row()
    else:
        raise UnauthorizedUser()


@company_bp.route('/membership/<string:membership_id>/request_membership_plan/', methods=['OK'],
                  permissions=employee_have_right_at_membership(
                      RIGHT_AT_COMPANY.COMPANY_MANAGE_PARTICIPATION))
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


@company_bp.route('/<string:company_id>/materials/', methods=['GET'], permissions=employee_have_right())
def materials(company_id):
    return render_template('company/materials.html', company=utils.db.query_filter(Company, id=company_id).one(),
                           actions={
                               'create_material': employee_have_right(RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH)(
                                   company_id=company_id)
                           })


@company_bp.route('/<string:company_id>/materials/', methods=['OK'], permissions=employee_have_right())
def materials_load(json, company_id):
    subquery = Material.subquery_company_materials(company_id, json.get('filter'), json.get('sort')).order_by(
        expression.desc(Material.cr_tm))
    materials, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    grid_filters = {
        'portal_division.portal.name': [{'value': portal, 'label': portal} for portal_id, portal in
                                        Material.get_portals_where_company_send_article(company_id).items()],
        # 'material_status': Grid.filter_for_status(Material.STATUSES),
        'status': Grid.filter_for_status(Publication.STATUSES),
        'publication_visibility': Grid.filter_for_status(Publication.VISIBILITIES)

    }

    return {'grid_data': Grid.grid_tuple_to_dict([Material.get_material_grid_data(material) for material in materials]),
            'grid_filters': {k: [{'value': None, 'label': TranslateTemplate.getTranslate('', '__-- all --')}] + v for
                             (k, v) in grid_filters.items()},
            'total': count
            }
