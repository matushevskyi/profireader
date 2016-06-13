from .blueprints_declaration import company_bp
from flask.ext.login import current_user
from flask import render_template, request, url_for, g, redirect, abort
from ..models.company import Company, UserCompany
from ..models.translate import TranslateTemplate
from .request_wrapers import check_right
from ..models.materials import Material, Publication
from ..models.portal import PortalDivision

# from ..models.bak_articles import ArticleCompany, ArticlePortalDivision
from utils.db_utils import db
from .pagination import pagination
from config import Config
from .. import utils
from ..models.pr_base import PRBase, Grid
from ..models.rights import EditCompanyRight, EmployeesRight, EditPortalRight, UserIsEmployee, EmployeeAllowRight, \
    CanCreateCompanyRight, UserIsActive, BaseRightsEmployeeInCompany

@company_bp.route('/search_to_submit_article/', methods=['POST'])
@check_right(UserIsActive)
def search_to_submit_article(json):
    companies = Company().search_for_company(g.user.id, json['search'])
    return companies




@company_bp.route('/', methods=['GET'])
@check_right(UserIsActive)
def companies():
    return render_template('company/companies.html')

@company_bp.route('/', methods=['OK'])
@check_right(UserIsActive)
def companies_load(json):
    companies, pages, page, count = pagination(query=db(Company)
        .filter(
            Company.id == db(UserCompany, user_id=g.user.id).subquery().c.company_id), page=1,
            items_per_page=6 * json.get('next_page') if json.get('next_page') else 6)
    return {'companies': [usr_cmp.get_client_side_dict() for usr_cmp in companies],'actions':{'create_company':CanCreateCompanyRight(user=g.user).is_allowed()},
            'user_id': g.user.id, 'end': True if pages == 1 or pages == 0 else False}


@company_bp.route('/<string:company_id>/materials/', methods=['GET'])
@check_right(UserIsEmployee, ['company_id'])
def materials(company_id):
    return render_template('company/materials.html', company=db(Company, id=company_id).one(),
            actions={'create_material': BaseRightsEmployeeInCompany(company=company_id).action_is_allowed(BaseRightsEmployeeInCompany.ACTIONS['CREATE_MATERIAL'])})


@company_bp.route('/<string:company_id>/materials/', methods=['OK'])
@check_right(UserIsEmployee, ['company_id'])
def materials_load(json, company_id):
    subquery = Material.subquery_company_materials(company_id, json.get('filter'), json.get('sort'))
    materials, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    grid_filters = {
        'portal.name': [{'value': portal, 'label': portal} for portal_id, portal in
                        Material.get_portals_where_company_send_article(company_id).items()],
        'material_status': Grid.filter_for_status(Material.STATUSES),
        'status': Grid.filter_for_status(Publication.STATUSES),
        'publication_visibility': Grid.filter_for_status(Publication.VISIBILITIES)


    }
    # PublishUnpublishInPortal(publication=publication, portal=publication.division.portal,
    #                          company=publication.division.portal.own_company).actions()
    return {'grid_data': Grid.grid_tuple_to_dict([Material.get_material_grid_data(material) for material in materials]),
            'grid_filters': {k: [{'value': None, 'label': TranslateTemplate.getTranslate('', '__-- all --')}] + v for
                             (k, v) in grid_filters.items()},
            'total': count
            }


# @company_bp.route('/<string:article_portal_division_id>/', methods=['OK'])
# @login_required
# @ok
# @check_right(PublishUnpublishInPortal, 'article_portal_division_id', PublishUnpublishInPortal.ACTIONS['DELETE'])
# def delete_atricle_from_portal(json, article_portal_division_id):
#     print('here')
#     g.sql_connection.execute("DELETE FROM article_portal_division WHERE id='%s';"
#                              % article_portal_division_id)
#     new_json = json.copy()
#     for article in json:
#         if json[article]['id'] == article_portal_division_id:
#             del new_json[article]
#     return new_json


# file_author_user_id_fkey	FOREIGN KEY (author_user_id) REFERENCES "user"(id)


@company_bp.route('/update_material_status/<string:company_id>/<string:article_id>', methods=['OK'])
@check_right(UserIsEmployee, ['company_id'])
def update_material_status(json, company_id, article_id):
    allowed_statuses = ArticleCompany.STATUSES.keys()
    # ARTICLE_STATUS_IN_COMPANY.can_user_change_status_to(json['new_status'])

    ArticleCompany.update_article(
            company_id=company_id,
            article_id=article_id,
            **{'status': json['new_status']})

    return {'article_new_status': json['new_status'],
            'allowed_statuses': allowed_statuses,
            'status': 'ok'}


@company_bp.route('/<string:company_id>/employees/', methods=['GET'])
@check_right(UserIsEmployee, ['company_id'])
def employees(company_id):
    return render_template('company/company_employees.html', company=Company.get(company_id))


@company_bp.route('/<string:company_id>/employees/', methods=['OK'])
@check_right(UserIsEmployee, ['company_id'])
def employees_load(json, company_id):
    company = Company.get(company_id)
    employees_list = [
        utils.dict_merge(employment.employee.get_client_side_dict(), employment.get_client_side_dict(),
                           {'actions': EmployeesRight(company=company, employment=employment).actions()})
        for employment in company.employee_assoc]

    return {
        'company': company.get_client_side_dict(fields='id,name'),
        'grid_data': employees_list
    }


# @company_bp.route('/<string:company_id>/employee_details/<string:user_id>/', methods=['GET'])
# @tos_required
# @login_required
# # @check_rights(simple_permissions([]))
# def employee_details(company_id, user_id):
#     employment = UserCompany.get(user_id=user_id, company_id=company_id)
#     return render_template('company/company_employee_details.html',
#                            company=Company.get(company_id),
#                            employer=employment.employer.get_client_side_dict(),
#                            employee=employment.employee.get_client_side_dict(),
#                            employment=employment.get_client_side_dict(),
#                            user_right_in=UserCompany.get(company_id=company_id).has_rights(
#                                    UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS)
#                            )


@company_bp.route('/<string:company_id>/employee_update/<string:user_id>/', methods=['GET'])
@check_right(EmployeeAllowRight, ['company_id', 'user_id'])
def employee_update(company_id, user_id):
    return render_template('company/company_employee_update.html',
                           company=Company.get(company_id),
                           employment=UserCompany.get(user_id=user_id, company_id=company_id))
    # employer=employment.employer.get_client_side_dict(),
    # employee=employment.employee.get_client_side_dict())


@company_bp.route('/<string:company_id>/employee_update/<string:user_id>/', methods=['OK'])
@check_right(EmployeeAllowRight, ['company_id', 'user_id'])
def employee_update_load(json, company_id, user_id):
    action = g.req('action', allowed=['load', 'validate', 'save'])
    employment = UserCompany.get(user_id=user_id, company_id=company_id)

    if action == 'load':
        return {'employment': employment.get_client_side_dict(),
                'employee': employment.employee.get_client_side_dict(),
                'employer': employment.employer.get_client_side_dict(fields='id|logo_file_id|name'),
                # 'statuses_available': UserCompany.get_statuses_avaible(company_id),
                # 'rights_available': employment.get_rights_avaible()
                }
    else:
        employment.set_client_side_dict(json['employment'])
        if action == 'validate':
            employment.detach()
            return employment.validate(False)
        else:
            employment.save()
    return employment.get_client_side_dict()


@company_bp.route('/<string:company_id>/employment/<string:employment_id>/action/<string:action>/', methods=['OK'])
@check_right(EmployeesRight, ['company_id', 'employment_id'], action='action')
def employment_action(json, company_id, employment_id, action):
    employment = db(UserCompany).filter_by(id=employment_id).one()

    if action == EmployeesRight.ACTIONS['REJECT']:
        employment.status = EmployeesRight.STATUSES['REJECTED']
    elif action == EmployeesRight.ACTIONS['ENLIST']:
        employment.status = EmployeesRight.STATUSES['ACTIVE']
    elif action == EmployeesRight.ACTIONS['FIRE']:
        employment.status = EmployeesRight.STATUSES['FIRED']

    employment.save()

    return utils.dict_merge(employment.employee.get_client_side_dict(), employment.get_client_side_dict(),
                              {'actions': EmployeesRight(company=company_id, employment=employment).actions()})


@company_bp.route('/<string:company_id>/employment/<string:employment_id>/change_position/', methods=['OK'])
@check_right(EmployeesRight, ['company_id', 'employment_id'], action=EmployeesRight.ACTIONS['ALLOW'])
def employment_change_position(json, company_id, employment_id):
    employment = db(UserCompany).filter_by(id=employment_id).one()

    employment.position = json['position']
    employment.save()

    return utils.dict_merge(employment.employee.get_client_side_dict(), employment.get_client_side_dict(),
                              {'actions': EmployeesRight(company=company_id, employment=employment).actions()})


# @company_bp.route('/update_rights', methods=['POST'])
# @check_right(UserIsActive)
# def update_rights():
#     data = request.form
#     company_id, user_id, position = (data.get('company_id'), data.get('user_id'), data['position'])
#     if not db(Company, id=company_id, author_user_id=user_id).count():
#         UserCompany.update_rights(user_id=data['user_id'],
#                                   company_id=data['company_id'],
#                                   new_rights=data.getlist('right'),
#                                   position=data['position'])
#     else:
#         db(UserCompany, company_id=company_id, user_id=user_id).update(dict(position=position))
#     return redirect(url_for('company.employees',
#                             company_id=data['company_id']))


@company_bp.route('/create/', methods=['GET'])
@check_right(UserIsActive)
def update():
    # user_companies = [user_comp for user_comp in current_user.employer_assoc]
    # user_have_comp = True if len(user_companies) > 0 else False
    # company = db(Company, id=company_id).first()
    return render_template('company/company_profile.html', rights_user_in_company={},
                           company=Company())


@company_bp.route('/<string:company_id>/profile/', methods=['GET'])
@check_right(UserIsActive)
def profile(company_id=None):
    company = db(Company, id=company_id).first()
    user_company = UserCompany.get(company_id=company_id)
    return render_template('company/company_profile.html',
                           user_company_active=user_company is not None,
                           company=company)


@company_bp.route('/create/', methods=['OK'])
@company_bp.route('/<string:company_id>/profile/', methods=['OK'])
@check_right(UserIsActive)
def profile_load_validate_save(json, company_id=None):
    # if not user_can_edit:
    #     raise Exception('no PORTAL_EDIT_PROFILE')
    action = g.req('action', allowed=['load', 'validate', 'save'])
    company = Company() if company_id is None else Company.get(company_id)
    if action == 'load':
        company_dict = company.get_client_side_dict()
        company_dict['logo'] = company.get_logo_client_side_dict()
        user_company = UserCompany.get(company_id=company_id)
        if user_company:
            company_dict['actions'] = {'edit_company_profile': EditCompanyRight(company=company).is_allowed(),
                                       'edit_portal_profile':EditPortalRight(company=company_id).is_allowed()}
        return company_dict
    else:
        company.attr(g.filter_json(json, 'about', 'address', 'country', 'email', 'name', 'phone', 'city', 'postcode',
                                   'phone2', 'region', 'short_description', 'lon', 'lat'))
        if action == 'validate':
            if company_id is not None:
                company.detach()
            return company.validate(company_id is None)
        else:
            if company_id and EditCompanyRight(company=company_id).is_allowed() != True:
                return abort(403)
            if company_id is None:
                company.setup_new_company()
            company.set_logo_client_side_dict(json['logo'])
            company.save()
            company_dict = company.get_client_side_dict()
            company_dict['logo'] = company.get_logo_client_side_dict()
            company_dict['actions'] = {'edit': True if company_id else False}
            return company_dict


# @company_bp.route('/confirm_create/', methods=['OK'])
# @login_required
# # @check_rights(simple_permissions([]))
# @ok
# def confirm_create(json):


# @company_bp.route('/edit/<string:company_id>/', methods=['OK'])
# @login_required
# @ok
# # @check_rights(simple_permissions([RIGHTS.MANAGE_RIGHTS_COMPANY()]))
# def edit_load(json, company_id):
#     company = db(Company, id=company_id).one()
#     return company.get_client_side_dict()


# @company_bp.route('/confirm_edit/<string:company_id>', methods=['OK'])
# @login_required
# @ok
# # @check_rights(simple_permissions([RIGHTS.MANAGE_RIGHTS_COMPANY()]))
# def confirm_edit(json, company_id):
#
#     return {}



@company_bp.route('/search_for_company_to_join/', methods=['OK'])
@check_right(UserIsActive)
def search_for_company_to_join(json):
    companies, pages, page, count = pagination(
            query=Company().search_for_company_to_join(g.user.id, json['search']), page=1,
            items_per_page=5 * json.get('next_page') if json.get('next_page') else 5)
    return {'company_list': [company.get_client_side_dict() for company in
                             companies], 'end': pages == 1}


@company_bp.route('/search_for_user/<string:company_id>', methods=['OK'])
@check_right(UserIsActive)
def search_for_user(json, company_id):
    users = UserCompany().search_for_user_to_join(company_id, json['search'])
    return users


@company_bp.route('/send_article_to_user/', methods=['OK'])
@check_right(UserIsActive)
def send_article_to_user(json):
    return {'user': json['send_to_user']}


@company_bp.route('/join_to_company/<string:company_id>/', methods=['OK'])
@check_right(UserIsActive)
def join_to_company(json, company_id):
    UserCompany(user_id=g.user.id, company_id=json.get('company_id')).save()
    return {'companies': [employer.get_client_side_dict() for employer in current_user.employers]}


@company_bp.route('/add_subscriber/', methods=['POST'])
@check_right(UserIsActive)
def confirm_subscriber():
    company_role = UserCompany()
    data = request.form
    company_role.apply_request(company_id=data['company_id'],
                               user_id=data['user_id'],
                               bool=data['req'])
    return redirect(url_for('company.profile', company_id=data['company_id']))


# TODO: VK by OZ: following 3 functions would have to be joined into one
# @company_bp.route('/suspend_employee/', methods=['POST'])
# @login_required
# # @check_rights(simple_permissions([RIGHTS.SUSPEND_EMPLOYEE()]))
# def suspend_employee():
#     data = request.form
#     UserCompany.change_status_employee(user_id=data['user_id'],
#                                        company_id=data['company_id'])
#     return redirect(url_for('company.employees',
#                             company_id=data['company_id']))
#
#
# @company_bp.route('/fire_employee/', methods=['POST'])
# @login_required
# def fire_employee():
#     data = request.form
#     UserCompany.change_status_employee(company_id=data.get('company_id'),
#                                        user_id=data.get('user_id'),
#                                        status=UserCompany.STATUSES['FIRED'])
#     return redirect(url_for('company.employees', company_id=data.get('company_id')))
#
#
# @company_bp.route('/unsuspend/<string:user_id>,<string:company_id>')
# @login_required
# def unsuspend(user_id, company_id):
#     UserCompany.change_status_employee(user_id=user_id,
#                                        company_id=company_id,
#                                        status=UserCompany.STATUSES['ACTIVE'])
#     return redirect(url_for('company.employees', company_id=company_id))
#
#
# @company_bp.route('/suspended_employees/<string:company_id>',
#                   methods=['GET'])
# @tos_required
# @login_required
# # @check_rights(simple_permissions([]))
# def suspended_employees(company_id):
#     company = db(Company, id=company_id).one()
#     return render_template('company/company_fired.html', company_id=company_id, company=company)
#
#
# @company_bp.route('/suspended_employees/<string:company_id>', methods=['POST'])
# @login_required
# # @check_rights(simple_permissions([]))
# @ok
# def load_suspended_employees(json, company_id):
#     suspend_employees = Company.query_company(company_id)
#     suspend_employees = suspend_employees.suspended_employees()
#     return suspend_employees


@company_bp.route('/readers/<string:company_id>/', methods=['GET'])
@company_bp.route('/readers/<string:company_id>/<int:page>/', methods=['GET'])
@check_right(UserIsEmployee, ['company_id'])
def readers(company_id, page=1):
    company = Company.get(company_id)
    company_readers, pages, page, count = pagination(query=company.readers_query, page=page)

    reader_fields = ('id', 'email', 'nickname', 'first_name', 'last_name')
    company_readers_list_dict = list(map(lambda x: dict(zip(reader_fields, x)), company_readers))

    return render_template('company/company_readers.html',
                           company=company,
                           companyReaders=company_readers_list_dict,
                           pages=pages,
                           current_page=page,
                           page_buttons=Config.PAGINATION_BUTTONS,
                           search_text=None,
                           )


@company_bp.route('/readers/<string:company_id>/', methods=['OK'])
@check_right(UserIsEmployee, ['company_id'])
def readers_load(json, company_id):
    company = Company.get(company_id)
    company_readers, pages, page, count = pagination(query=company.get_readers_for_portal(json.get('filter')),
                                                     **Grid.page_options(json.get('paginationOptions')))

    return {'grid_data': [reader.get_client_side_dict(
            'id,profireader_email,profireader_name,profireader_first_name,profireader_last_name') for reader in
                          company_readers],
            'total': count
            }
