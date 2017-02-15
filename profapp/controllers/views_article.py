from flask import render_template, g

from profapp.models.portal import PortalDivision, Portal, MemberCompanyPortal

from .blueprints_declaration import article_bp
from .. import utils
from ..models.company import Company
from ..models.materials import Material, Publication
from ..models.pr_base import PRBase, Grid
from ..models.tag import Tag
from ..models.permissions import UserIsActive, EmployeeHasRightAtCompany, RIGHT_AT_COMPANY, CheckFunction
from profapp.models.permissions import ActionsForMaterialAtMembership


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


@article_bp.route('/submit_or_publish_material/<string:material_id>/<string:SUBMIT_OR_PUBLISH>/', methods=['OK'],
                  permissions=UserIsActive())
def submit_or_publish_material(json, material_id, SUBMIT_OR_PUBLISH):
    action = g.req('action', allowed=['load', 'validate', 'save'])

    material = Material.get(material_id)
    publisher_membership = MemberCompanyPortal.get(json['publisher_membership']['id'])

    action_allowed = ActionsForMaterialAtMembership.actions(publisher_membership, material)
    publication = Publication(material=Material.get(json['publication']['material']['id']))

    if action == 'load':
        return {
            'publication': publication.get_client_side_dict(),
            'publisher_membership': publisher_membership.get_client_side_dict(
                fields='id, company, portal, portal.divisions_publicable, current_membership_plan_issued'),
            'publication_count': publisher_membership.get_publication_count(),
            'can_material_also_be_published': True if utils.find_by_keys(
                action_allowed, ActionsForMaterialAtMembership.ACTIONS['PUBLISH'], 'name') else False
        }
    else:
        jpublication = json['publication']
        publication.portal_division = PortalDivision.get(jpublication['portal_division_id'], returnNoneIfNotExists=True)
        publication.visibility = jpublication['visibility']
        publication.tags = [Tag.get(t['id']) for t in jpublication['tags']]
        for d in ['publishing_tm', 'event_begin_tm', 'event_end_tm']:
            setattr(publication, d, PRBase.parse_timestamp(jpublication.get(d)))

        if SUBMIT_OR_PUBLISH == ActionsForMaterialAtMembership.ACTIONS['PUBLISH']:
            publication.status = Publication.STATUSES['PUBLISHED']
        else:
            publication.status = Publication.STATUSES['SUBMITTED']

    if action == 'validate':
        publication.detach()
        return publication.validate(True)
    else:
        publication.save()
        return publisher_membership.material_or_publication_grid_row(material)
        # membership.NOTIFY_ARTICLE_SUBMITED_BY_COMPANY(material_title=publication.material.title)

        # g.db().execute("SELECT tag_publication_set_position('%s', ARRAY ['%s']);" %
        #                (publication.id, "', '".join([t.id for t in publication.tags])))


@article_bp.route('/republish_publication/', methods=['OK'], permissions=UserIsActive())
# @check_right(UserIsActive)
def republish_publication(json, publication_id, SUBMIT_OR_PUBLISH):
    from profapp.models.permissions import ActionsForPublicationAtMembership
    action = g.req('action', allowed=['load', 'validate', 'save'])

    publication = Material.get(publication_id)
    portal = publication.portal_division.portal
    membership = MemberCompanyPortal.get(json['membership_id'])

    action_allowed = ActionsForMaterialAtMembership.actions(membership, material)
    publication = Publication(material=Material.get(json['material']['id']))

    if 1:
        action_allowed = utils.find_by_keys(ActionsForPublicationAtMembership.article_actions_by_portal(publication),
                                            action, 'name')
    else:
        action_allowed = utils.find_by_keys(ArticleActionsForMembership.article_actions_by_company(
            membership, publication=publication), action, 'name')

    portal = Portal.get(json['at_portal']['id'])

    if json.get('from_company'):
        by_company_by_portal_t_f = True
        membership = MemberCompanyPortal.get_by_portal_id_company_id(
            portal.id,
            utils.dict_deep_get(json, 'from_company', 'id', on_error=portal.own_company.id))
    else:
        by_company_by_portal_t_f = False
        membership = MemberCompanyPortal.get_by_portal_id_company_id(
            portal.id, portal.company_owner_id)

    if article_action == 'SUBMIT':
        publication = Publication(material=Material.get(json['material']['id']))
        more_data_to_ret = {
            'material': Material.get(json['material']['id']).get_client_side_dict(),
            'can_material_also_be_published':
                ArticleActionsForMembership(ArticleActionsForMembership.MATERIAL_ACTIONS['PUBLISH']).
                    check(membership_id=membership.id, material_id=json['material']['id'])
        }
    else:
        publication = Publication.get(json['publication']['id'])
        more_data_to_ret = {}

    if action == 'load':
        ret = {
            'publication': publication.get_client_side_dict(),
            'from_company': membership.company.get_client_side_dict(),
            'membership': membership.get_client_side_dict(fields='current_membership_plan_issued'),
            'publication_count': membership.get_publication_count(),
            # 'at_portal': portal.get_client_side_dict(fields='id,name,tags,divisions_publicable')
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

        publication.status = Publication.STATUSES['SUBMITTED']

        if json.get('also_publish', None):
            publication.status = Publication.STATUSES['PUBLISHED']
            # if by_company_by_portal_t_f:
            #     pass
            # membership.NOTIFY_ARTICLE_PUBLISHED_BY_PORTAL()
        if by_company_by_portal_t_f:
            action_allowed = utils.find_by_keys(ArticleActionsForMembership.article_actions_by_portal(publication),
                                                action, 'name')
        else:
            action_allowed = utils.find_by_keys(ArticleActionsForMembership.article_actions_by_company(
                membership, publication=publication), action, 'name')

        if action['enabled']:

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
