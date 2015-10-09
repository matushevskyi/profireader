from .blueprints import company_bp
from ..models.company import simple_permissions
from flask.ext.login import login_required, current_user
from flask import render_template, request, url_for, g, redirect
from ..models.company import Company, UserCompany, Right, RightHumnReadible
# from ..models.rights import list_of_RightAtomic_attributes
from .request_wrapers import ok, check_rights
from ..constants.STATUS import STATUS
from flask.ext.login import login_required
from ..models.articles import Article
from ..constants.ARTICLE_STATUSES import ARTICLE_STATUS_IN_COMPANY
from ..models.portal import CompanyPortal
from ..models.articles import ArticleCompany
from utils.db_utils import db
from collections import OrderedDict
# from ..models.rights import list_of_RightAtomic_attributes
from profapp.models.rights import RIGHTS
from ..models.files import File


@company_bp.route('/search_to_submit_article/', methods=['POST'])
@login_required
# @check_rights(simple_permissions(Right[RIGHTS.SUBMIT_PUBLICATIONS()]))
def search_to_submit_article(json):
    companies = Company().search_for_company(g.user_dict['id'], json['search'])
    return companies


@company_bp.route('/', methods=['GET'])
@login_required
# @check_rights(simple_permissions([]))
def show():
    return render_template('company/companies.html')


@company_bp.route('/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def load_companies(json):

    return {'companies': [employer.get_client_side_dict()
                          for employer in current_user.employers]}


@company_bp.route('/materials/<string:company_id>/', methods=['GET'])
@login_required
# @check_rights(simple_permissions([]))
def materials(company_id):
    return render_template('company/materials.html',
                           company_id=company_id,
                           articles=[art.to_dict(
                               'id, title') for art in Article.
                               get_articles_submitted_to_company(
                                   company_id)])


@company_bp.route('/material_details/<string:company_id>/<string:article_id>/', methods=['GET'])
@login_required
# @check_rights(simple_permissions([]))
def material_details(company_id, article_id):
    return render_template('company/material_details.html',
                           company_id=company_id,
                           article_id=article_id)


@company_bp.route('/material_details/<string:company_id>/<string:article_id>/', methods=['POST'])
@login_required
@ok
#@check_rights(simple_permissions([]))
def load_material_details(json, company_id, article_id):
    article = Article.get_one_article(article_id)
    portals = {port.portal_id: port.portal.get_client_side_dict() for port in
               CompanyPortal.get_portals(company_id)}
    joined_portals = {}
    if article.portal_article:
        joined_portals = {articles.division.portal.id: portals.pop(articles.division.portal.id)
                          for articles in article.portal_article
                          if articles.division.portal.id in portals}

    article = article.to_dict('id, title,short, cr_tm, md_tm, '
                              'company_id, status, long,'
                              'editor_user_id, company.name|id,'
                              'portal_article.division.portal.id')

    status = ARTICLE_STATUS_IN_COMPANY.can_user_change_status_to(article['status'])
    user_rights = list(g.user.user_rights_in_company(company_id))

    return {'article': article,
            'status': status,
            'portals': portals,
            'company': Company.get(company_id).to_dict('id, employees.id|profireader_name'),
            'selected_portal': {},
            'selected_division': {},
            # 'user_rights': ['publish', 'unpublish', 'edit'],
            # TODO: uncomment the string below and delete above
            # TODO: when all works with rights are finished
            'user_rights': user_rights,
            'send_to_user': {},
            'joined_portals': joined_portals}


@company_bp.route('/update_article/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def update_article(json):

    ArticleCompany.update_article(
        company_id=json['company']['id'],
        article_id=json['article']['id'],
        **{'status': json['article']['status']})
    return {'article': json['article'], 'status': 'ok'}


@company_bp.route('/submit_to_portal/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def submit_to_portal(json):

    article = ArticleCompany.get(json['article']['id'])
    article_portal = article.clone_for_portal(json['selected_division'])
    article.save()
    portal = article_portal.get_article_owner_portal(portal_division_id=json['selected_division'])
    return {'portal': portal.name}


@company_bp.route('/create/')
@login_required
# @check_rights(simple_permissions([]))
def create():
    return render_template('company/company_edit.html', user=g.user_dict)

@company_bp.route('/create/', methods=['POST'])
@ok
def load_form_create(json):
    return {}


@company_bp.route('/confirm_create/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def confirm_create(json):
    return Company(**json).create_new_company().\
        get_client_side_dict()


@company_bp.route('/profile/<string:company_id>/')
@login_required
@check_rights(simple_permissions(['manage_rights_company']))
def profile(company_id):
    company = db(Company, id=company_id).one()
    user_rights = list(g.user.user_rights_in_company(company_id))
    # image = File.get(company.logo_file).url() \
    #     if company.logo_file else '/static/img/company_no_logo.png'
    image = company.logo_file_relationship.url() \
        if company.logo_file_id else '/static/img/company_no_logo.png'
    return render_template('company/company_profile.html',
                           company=company.to_dict('*, own_portal.*'),
                           user_rights=user_rights,
                           image=image,
                           company_id=company_id
                           )


@company_bp.route('/employees/<string:company_id>/')
@login_required
# @check_rights(simple_permissions([]))
def employees(company_id):

    company_user_rights = UserCompany.show_rights(company_id)
    ordered_rights = sorted(Right.keys(), key=lambda t: Right.RIGHT_POSITION()[t.lower()])
    ordered_rights = list(map((lambda x: getattr(x, 'lower')()), ordered_rights))

    for user_id in company_user_rights.keys():
        rights = company_user_rights[user_id]['rights']
        rez = OrderedDict()
        for elem in ordered_rights:
            rez[elem] = True if elem in rights else False
        company_user_rights[user_id]['rights'] = rez

    user_id = current_user.get_id()
    curr_user = {user_id: company_user_rights[user_id]}
    current_company = db(Company, id=company_id).one()

    return render_template('company/company_employees.html',
                           company=current_company,
                           company_id=company_id,
                           company_user_rights=company_user_rights,
                           curr_user=curr_user,
                           Right=Right,
                           RightHumnReadible=RightHumnReadible
                           )


@company_bp.route('/update_rights', methods=['POST'])
@login_required
# @check_rights(simple_permissions([RIGHTS.MANAGE_RIGHTS_COMPANY()]))
def update_rights():
    data = request.form
    UserCompany.update_rights(user_id=data['user_id'],
                              company_id=data['company_id'],
                              new_rights=data.getlist('right')
                              )
    return redirect(url_for('company.employees',
                            company_id=data['company_id']))


# todo: it must be checked!!!
@company_bp.route('/edit/<string:company_id>/', methods=['GET'])
@login_required
# @check_rights(simple_permissions([RIGHTS.MANAGE_RIGHTS_COMPANY()]))
def edit(company_id):
    return render_template('company/company_edit.html', company_id=company_id)

@company_bp.route('/edit/<string:company_id>/', methods=['POST'])
@login_required
@ok
# @check_rights(simple_permissions([RIGHTS.MANAGE_RIGHTS_COMPANY()]))
def edit_load(json, company_id):
    company = db(Company, id=company_id).one()
    return company.get_client_side_dict()


@company_bp.route('/confirm_edit/<string:company_id>', methods=['POST'])
@login_required
@ok
# @check_rights(simple_permissions([RIGHTS.MANAGE_RIGHTS_COMPANY()]))
def confirm_edit(json, company_id):
    Company().update_comp(company_id=company_id, data = json)
    return {}


@company_bp.route('/subscribe/<string:company_id>/')
@login_required
# @check_rights(simple_permissions([]))
def subscribe(company_id):
    company_role = UserCompany(user_id=g.user_dict['id'],
                               company_id=company_id,
                               status=STATUS.NONACTIVE())
    company_role.subscribe_to_company().save()

    return redirect(url_for('company.profile', company_id=company_id))


@company_bp.route('/search_for_company_to_join/', methods=['POST'])
@login_required
@ok
# @check_rights(simple_permissions([]))
def search_for_company_to_join(json):
    companies = Company().search_for_company_to_join(g.user_dict['id'], json['search'])
    return companies


@company_bp.route('/search_for_user/<string:company_id>', methods=['POST'])
@login_required
@ok
# @check_rights(simple_permissions([]))
def search_for_user(json, company_id):
    users = UserCompany().search_for_user_to_join(company_id, json['search'])
    return users


@company_bp.route('/send_article_to_user/', methods=['POST'])
@login_required
@ok
# @check_rights(simple_permissions([]))
def send_article_to_user(json):

    return {'user': json['send_to_user']}


@company_bp.route('/join_to_company/<string:company_id>/', methods=['POST'])
@login_required
@ok
#@check_rights(simple_permissions([]))
def join_to_company(json, company_id):
    company_role = UserCompany(user_id=g.user_dict['id'],
                               company_id=json['company_id'],
                               status=STATUS.NONACTIVE())
    company_role.subscribe_to_company().save()
    return {'companies': [employer.get_client_side_dict()
                          for employer in current_user.employers]}


@company_bp.route('/add_subscriber/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([RIGHTS.ADD_EMPLOYEE()]))
def confirm_subscriber():
    company_role = UserCompany()
    data = request.form
    company_role.apply_request(company_id=data['company_id'],
                               user_id=data['user_id'],
                               bool=data['req'])
    return redirect(url_for('company.profile',
                            company_id=data['company_id']))


@company_bp.route('/suspend_employee/', methods=['POST'])
@login_required
# @check_rights(simple_permissions([RIGHTS.SUSPEND_EMPLOYEE()]))
def suspend_employee():
    data = request.form
    UserCompany.change_status_employee(user_id=data['user_id'],
                                       company_id=data['company_id'])
    return redirect(url_for('company.employees',
                            company_id=data['company_id']))

@company_bp.route('/fire_employee/', methods=['POST'])
@login_required
def fire_employee():
    data = request.form
    UserCompany.change_status_employee(company_id=data.get('company_id'),
                                       user_id=data.get('user_id'),
                                       status=STATUS.DELETED())
    return redirect(url_for('company.employees',
                            company_id=data.get('company_id')))

@company_bp.route('/unsuspend/<string:user_id>,<string:company_id>')
@login_required
def unsuspend(user_id, company_id):

    UserCompany.change_status_employee(user_id=user_id,
                                       company_id=company_id,
                                       status=STATUS.ACTIVE())
    return redirect(url_for('company.employees', company_id=company_id))



@company_bp.route('/suspended_employees/<string:company_id>',
                  methods=['GET'])
@login_required
# @check_rights(simple_permissions([]))
def suspended_employees(company_id):
    return render_template('company/company_fired.html', company_id=company_id)


@company_bp.route('/suspended_employees/<string:company_id>', methods=['POST'])
@login_required
# @check_rights(simple_permissions([]))
@ok
def load_suspended_employees(json, company_id):

    suspend_employees = Company.query_company(company_id)
    suspend_employees = suspend_employees.suspended_employees()
    return suspend_employees
