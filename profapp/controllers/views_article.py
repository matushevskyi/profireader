from flask import render_template, g

from profapp.models.portal import PortalDivision, Portal, MemberCompanyPortal

from .blueprints_declaration import article_bp
from .. import utils
from ..models.company import Company
from ..models.materials import Material, Publication
from ..models.pr_base import PRBase, Grid
from ..models.tag import Tag
from ..models.permissions import UserIsActive, EmployeeHasRightAtCompany, RIGHT_AT_COMPANY, CheckFunction


def material_can_be_edited():
    return EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.ARTICLES_EDIT_OTHERS) | \
           (EmployeeHasRightAtCompany() &
            CheckFunction(lambda material_id, company_id: Material.get(material_id).editor_user_id == g.user_id))


@article_bp.route('/<string:company_id>/material_create/', methods=['GET'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY._ANY))
@article_bp.route('/<string:company_id>/material_update/<string:material_id>/', methods=['GET'],
                  permissions=material_can_be_edited())
def article_show_form(company_id, material_id=None):
    company = Company.get(company_id)
    return render_template('article/edit.html', material_id=material_id, company_id=company_id, company=company)


@article_bp.route('/<string:company_id>/material_update/<string:material_id>/', methods=['OK'],
                  permissions=UserIsActive())
@article_bp.route('/<string:company_id>/material_create/', methods=['OK'], permissions=UserIsActive())
def load_form_create(json_data, company_id=None, material_id=None):
    action = g.req('action', allowed=['load', 'validate', 'save'])

    if material_id:
        material = Material.get(material_id)
    else:
        material = Material(company=Company.get(company_id), company_id=company_id, editor=g.user)

    if action == 'load':
        return {'material': material.get_client_side_dict(more_fields='long|company|illustration')}
    else:
        parameters = utils.filter_json(json_data, 'material.title|subtitle|short|long|keywords|author')
        material.attr(parameters['material'])
        if action == 'validate':
            material.detach()
            return material.validate(material.id is not None)
        else:
            material.save()
            material.illustration = json_data['material']['illustration']

            return {'material': material.save().get_client_side_dict(more_fields='long|company|illustration')}


@article_bp.route('/material_details/<string:material_id>/', methods=['GET'], permissions=UserIsActive())
def material_details(material_id):
    company = Company.get(Material.get(material_id).company.id)
    return render_template('article/material_details.html',
                           article=Material.get(material_id).get_client_side_dict(),
                           company=company)


@article_bp.route('/material_details/<string:material_id>/', methods=['OK'], permissions=UserIsActive())
def material_details_load(json, material_id):
    material = Material.get(material_id)
    company = material.company

    return {
        'material': material.get_client_side_dict(more_fields='long'),
        'actions': {'EDIT': material_can_be_edited().check(company_id=company.id, material_id=material_id)},
        'portals': {
            'grid_data': [m.material_or_publication_grid_row(material) for m in company.memberships_active]
        }
    }


@article_bp.route('/submit_publish/<string:article_action>/', methods=['OK'],
                  permissions=UserIsActive())
# @check_right(UserIsActive)
def submit_publish(json, article_action):
    from profapp.models.permissions import ArticleActionsForMembership
    action = g.req('action', allowed=['load', 'validate', 'save'])

    portal = Portal.get(json['at_portal_id'])
    membership = MemberCompanyPortal.get_by_portal_id_company_id(
        portal.id,
        json.get('from_company_id') if json.get('from_company_id') else portal.own_company.id)

    if article_action == 'SUBMIT':
        publication = Publication(material=Material.get(json['material']['id']))
    else:
        publication = Publication.get(json['publication']['id'])

    if article_action == 'SUBMIT':
        more_data_to_ret = {
            'material': {'id': Material.get(json['material']['id']).get_client_side_dict()},
            'can_material_also_be_published':
                ArticleActionsForMembership(ArticleActionsForMembership.MATERIAL_ACTIONS['PUBLISH']).
                    check(membership_id=membership.id, material_id=json['material']['id'])
        }
    else:
        more_data_to_ret = {}

    if action == 'load':
        ret = {
            'publication': publication.get_client_side_dict(),
            'company': membership.company.get_client_side_dict(),
            'membership': membership.get_client_side_dict(fields='current_membership_plan_issued'),
            'publication_count': membership.get_publication_count(),
            'portal': portal.get_client_side_dict(fields='id,name,tags,divisions_publicable')
        }

        return utils.dict_merge(ret, more_data_to_ret)
    else:

        publication.portal_division = PortalDivision.get(json['publication']['portal_division_id'],
                                                         returnNoneIfNotExists=True)
        publication.visibility = json['publication']['visibility']
        publication.publishing_tm = PRBase.parse_timestamp(json['publication'].get('publishing_tm'))
        publication.event_begin_tm = PRBase.parse_timestamp(json['publication'].get('event_begin_tm'))
        publication.event_end_tm = PRBase.parse_timestamp(json['publication'].get('event_end_tm'))
        publication.tags = [Tag.get(t['id']) for t in json['publication']['tags']]

        publication.status = PublishUnpublishInPortal.STATUSES['SUBMITTED']

        if 'also_publish' in json and json['also_publish']:
            publication.status = PublishUnpublishInPortal.STATUSES['PUBLISHED']
            if by_company_by_portal_t_f:
                pass
                # membership.NOTIFY_ARTICLE_PUBLISHED_BY_PORTAL()
        else:
            if article_action in [PublishUnpublishInPortal.ACTIONS['PUBLISH'],
                                  PublishUnpublishInPortal.ACTIONS['REPUBLISH']]:
                publication.status = PublishUnpublishInPortal.STATUSES['PUBLISHED']
            elif article_action in [PublishUnpublishInPortal.ACTIONS['UNPUBLISH'],
                                    PublishUnpublishInPortal.ACTIONS['UNDELETE']]:
                publication.status = PublishUnpublishInPortal.STATUSES['UNPUBLISHED']
            elif article_action in [PublishUnpublishInPortal.ACTIONS['DELETE']]:
                publication.status = PublishUnpublishInPortal.STATUSES['DELETED']

        if action == 'validate':
            publication.detach()
            return (publication.validate(True if article_action == 'SUBMIT' else False)
                    if (
                article_action in ['SUBMIT', 'PUBLISH', 'REPUBLISH']) else publication.DEFAULT_VALIDATION_ANSWER())
        else:
            # if article_action == 'SUBMIT':
            #     publication.long = material.clone_for_portal_images_and_replace_urls(publication.portal_division_id,
            #                                                                          publication)
            publication.save()
            membership.NOTIFY_ARTICLE_SUBMITED_BY_COMPANY(material_title=publication.material.title)

            g.db().execute("SELECT tag_publication_set_position('%s', ARRAY ['%s']);" %
                           (publication.id, "', '".join([t.id for t in publication.tags])))

            return get_publication_dict_for_material(publication.portal_division.portal, company,
                                                     publication=publication,
                                                     submit=article_action == 'SUBMIT')
