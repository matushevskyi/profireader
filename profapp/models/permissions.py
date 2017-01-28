from ..models import exceptions
from flask import g


def user_is_active(*args, **kwargs):
    from ..models.users import User
    if 'user_id' in kwargs:
        user = User.get(kwargs['user_id'])
    else:
        if not getattr(g, 'user', False) or not getattr(g.user, 'id', False):
            raise exceptions.NotLoggedInUser()
        user = g.user
    if user.status != User.STATUSES['USER_ACTIVE']:
        raise exceptions.BannedUser()
    if not user.email_confirmed:
        raise exceptions.UnconfirmedEmailUser()
    return user


def company_is_active(*args, **kwargs):
    from ..models.company import Company

    company = Company.get(kwargs.get('company_id', ''), returnNoneIfNotExists=True)
    if not company:
        raise Exception("No company found `%s`" % kwargs.get('company_id', ''))

    if not company.is_active():
        raise Exception("company `%s` is not active" % company.id)

    return company


def employment_is_active(*args, **kwargs):
    from ..models.company import UserCompany

    user = user_is_active(kwargs)
    employment = UserCompany.get_by_user_and_company_ids(user_id=user.id, company_id=kwargs.get('company_id', ''))

    if not employment:
        raise Exception("No employment found by company_id and user_id")

    if not employment.is_active():
        raise Exception("employment `%s` is not active" % employment.id)

    return employment


def employee_have_right(right=None):
    from ..models.company import RIGHT_AT_COMPANY

    def allowed(*args, **kwargs):
        employment = employment_is_active(*args, **kwargs)
        aright = RIGHT_AT_COMPANY._ANY if right is None else right
        if aright == RIGHT_AT_COMPANY._ANY:
            return employment
        elif aright == RIGHT_AT_COMPANY._OWNER and employment.company.user_owner.id == employment.user_id:
            return employment
        elif employment.rights[aright]:
            return employment
        else:
            return False

    return allowed


def employee_af(load=None, validate=None, save=None):
    from ..models.company import RIGHT_AT_COMPANY
    perm_for_actions = {
        'load': RIGHT_AT_COMPANY._ANY if load is None else load,
        'validate': RIGHT_AT_COMPANY._ANY if validate is None else validate,
        'save': RIGHT_AT_COMPANY._OWNER if save is None else save,
    }

    def allowed(json, company_id, user_id=None):
        user_id = g.user.id if user_id is None else user_id
        action = g.req('action', allowed=['load', 'validate', 'save'])
        if action not in perm_for_actions:
            raise Exception('action should be one of `' + '`,`'.join(perm_for_actions.keys()) + "`")

        if perm_for_actions[action] is True or perm_for_actions[action] is False:
            return perm_for_actions[action]

        return employment_is_active(user_id=user_id, company_id=company_id)

    return allowed
