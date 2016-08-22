from .blueprints_declaration import messenger_bp
from flask import render_template, request, url_for, g, redirect, abort
from .request_wrapers import check_right

# # from ..models.bak_articles import ArticleCompany, ArticlePortalDivision
from utils.db_utils import db
# from .pagination import pagination
# from config import Config
# from .. import utils
from ..models.users import User
from ..models.company import Company, UserCompany
from ..models.portal import Portal, UserPortalReader
from ..models.pr_base import PRBase, Grid
from ..models.rights import EditCompanyRight, EmployeesRight, EditPortalRight, UserIsEmployee, EmployeeAllowRight, \
    CanCreateCompanyRight, UserIsActive, BaseRightsEmployeeInCompany


@messenger_bp.route('/', methods=['GET'])
@check_right(UserIsActive)
def messenger():
    return render_template('messenger/messenger.html')


@messenger_bp.route('/', methods=['OK'])
@check_right(UserIsActive)
def messenger_load(json):
    return {}


@messenger_bp.route('/community/', methods=['OK'])
@check_right(UserIsActive)
def community_search(json):
    portals_ids = []
    for p in g.user.active_portals_subscribed:
        portals_ids.append(p.id)

    companies_ids = []
    for c in g.user.active_companies_employers:
        companies_ids.append(c.id)

    from sqlalchemy import and_, or_

    query = g.db.query(User). \
        outerjoin(UserPortalReader,
                  and_(UserPortalReader.user_id == User.id, UserPortalReader.portal_id.in_(portals_ids))). \
        outerjoin(UserCompany,
                  and_(UserCompany.user_id == User.id, UserCompany.company_id.in_(companies_ids))). \
        filter(and_(User.full_name.ilike("%" + json['text'] + "%"),
            or_(UserPortalReader.id != None, UserCompany.id != None))). \
        group_by(User.id).\
        limit(10)



# )). \

    from sqlalchemy.dialects import postgresql

    print(str(query.statement.compile(compile_kwargs={"literal_binds": True}, dialect=postgresql.dialect())))
    users = query.all()

    print(users)

    ret = []

    for u in users:
        user_dict = u.get_client_side_dict(more_fields='avatar')
        user_dict['common_portals_subscribed'] = [p.get_client_side_dict() for p in u.active_portals_subscribed if
                                                  p.id in portals_ids]
        user_dict['common_companies_employers'] = [c.get_client_side_dict() for c in u.active_companies_employers if
                                                   c.id in companies_ids]
        ret.append(user_dict)

    return {
        'comp': [],
        'community': ret,
        'page': 1,
    }
