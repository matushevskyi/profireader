from flask import render_template, g

from profapp.models.portal import PortalDivision, Portal, MemberCompanyPortal

from .blueprints_declaration import article_bp
from .. import utils
from ..models.company import Company, UserCompany
from ..models.gallery import MaterialImageGallery, MaterialImageGalleryItem
from ..models.materials import Material, Publication
from ..models.pr_base import PRBase, Grid
from ..models.tag import Tag
from ..models.permissions import UserIsActive, EmployeeHasRightAtCompany, RIGHT_AT_COMPANY, RIGHT_AT_PORTAL, \
    CheckFunction
from profapp.models.permissions import ActionsForMaterialAtMembership, ActionsForPublicationAtMembership


def material_can_be_edited():
    return EmployeeHasRightAtCompany(RIGHT_AT_COMPANY.ARTICLES_EDIT_OTHERS) | \
           (EmployeeHasRightAtCompany() &
            CheckFunction(lambda material_id, company_id: Material.get(material_id).editor_user_id == g.user_id))


@article_bp.route('/<string:company_id>/material_create/', methods=['GET'],
                  permissions=EmployeeHasRightAtCompany(RIGHT_AT_COMPANY._ANY))
@article_bp.route('/<string:company_id>/material_update/<string:material_id>/', methods=['GET'],
                  permissions=material_can_be_edited())
def edit_material(company_id, material_id=None):
    company = Company.get(company_id)
    return render_template('article/edit.html', material_id=material_id, company_id=company_id, company=company)


@article_bp.route('/<string:company_id>/material_update/<string:material_id>/', methods=['OK'],
                  permissions=UserIsActive())
@article_bp.route('/<string:company_id>/material_create/', methods=['OK'], permissions=UserIsActive())
def edit_material_load(json_data, company_id=None, material_id=None):
    action = g.req('action', allowed=['load', 'validate', 'save'])

    if material_id:
        material = Material.get(material_id)
    else:
        material = Material(company=Company.get(company_id), company_id=company_id, editor=g.user)

    if action == 'load':
        return {'material': material.get_client_side_dict(more_fields='long|company|illustration,image_galleries.items,image_galleries.id')}
    else:
        parameters = utils.filter_json(json_data, 'material.title|subtitle|short|long|keywords|author')
        material.attr(parameters['material'])
        if action == 'validate':
            material.detach()
            return material.validate(material.id is not None)
        else:
            material.long = material.check_galleries(json_data['material']['image_galleries'], material.long)
            material.illustration = json_data['material']['illustration']
            material.save()

            return {'material': material.get_client_side_dict(more_fields='long|company|illustration')}


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


def publish_dialog_load(publication, publisher_membership):
    return {
        'publication': publication.get_client_side_dict(),
        'publisher_membership': publisher_membership.get_client_side_dict(
            fields='id, company, portal, portal.divisions_publicable, current_membership_plan_issued'),
        'publication_count': publisher_membership.get_publication_count()
    }


def publish_dialog_save(publication, jpublication, status):
    publication.portal_division = PortalDivision.get(jpublication['portal_division_id'], returnNoneIfNotExists=True)
    publication.visibility = jpublication['visibility']
    publication.tags = [Tag.get(t['id']) for t in jpublication['tags']]
    for d in ['publishing_tm', 'event_begin_tm', 'event_end_tm']:
        setattr(publication, d, PRBase.parse_timestamp(jpublication.get(d)))
    if status:
        publication.status = status


@article_bp.route(
    '/publication_change_status/<string:publication_id>/actor_membership_id/<string:actor_membership_id>/action/<string:action>/request_from/<string:request_from>/',
    methods=['OK'], permissions=UserIsActive())
def publication_change_status(json, publication_id, actor_membership_id, action, request_from):
    actor_membership = MemberCompanyPortal.get(actor_membership_id)
    publication = Publication.get(publication_id)

    if action == ActionsForPublicationAtMembership.ACTIONS['UNPUBLISH']:
        publication.status = Publication.STATUSES['UNPUBLISHED']
    elif action == ActionsForPublicationAtMembership.ACTIONS['UNDELETE']:
        publication.status = Publication.STATUSES['UNPUBLISHED']
    elif action == ActionsForPublicationAtMembership.ACTIONS['DELETE']:
        publication.status = Publication.STATUSES['DELETED']
    publication.save()

    actor_membership.NOTIFY_MATERIAL_ACTION_BY_COMPANY_OR_PORTAL(
        action=action, material_title=publication.material.title,
        company_or_portal='company' if request_from == 'company_material_details' else 'portal')

    if request_from == 'company_material_details':
        return actor_membership.material_or_publication_grid_row(publication.material)
    elif request_from == 'portal_publications':
        return publication.portal_publication_grid_row(actor_membership)


# @article_bp.route(
#     '/material_change_status/<string:material_id>/action/<string:action>/',
#     methods=['OK'], permissions=UserIsActive())
# def material_change_status(json, material_id, action):
#     material = Material.get(material_id)
#
#     if action == ActionsForMaterialAtMembership.ACTIONS['UNDELETE']:
#         material.status = Material.STATUSES['NORMAL']
#     elif action == ActionsForMaterialAtMembership.ACTIONS['DELETE']:
#         material.status = Material.STATUSES['DELETED']
#     material.save()


@article_bp.route('/submit_or_publish_material/<string:material_id>/', methods=['OK'], permissions=UserIsActive())
def submit_or_publish_material(json, material_id):
    action = g.req('action', allowed=['load', 'validate', 'save'])

    publication = Publication(material=Material.get(material_id))
    publisher_membership = MemberCompanyPortal.get(json['publisher_membership']['id'])
    employment = UserCompany.get_by_user_and_company_ids(company_id=publication.material.company_id)
    also_publish = json.get('also_publish', None)

    if action == 'load':
        return utils.dict_merge(
            publish_dialog_load(publication, publisher_membership),
            {'can_material_also_be_published':
                 employment.rights[RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH] and \
                 publisher_membership.rights[RIGHT_AT_PORTAL.PUBLICATION_PUBLISH]
             })
    else:
        publish_dialog_save(
            publication, json['publication'],
            status=Publication.STATUSES['PUBLISHED'] if also_publish else Publication.STATUSES['SUBMITTED'])

    if action == 'validate':
        publication.detach()
        return publication.validate(True)
    else:
        publication.save()
        utils.db.execute_function("tag_publication_set_position('%s', ARRAY ['%s']);" %
                                  (publication.id, "', '".join([t.id for t in publication.tags])))

        publisher_membership.NOTIFY_MATERIAL_ACTION_BY_COMPANY_OR_PORTAL(
            action='PUBLISH' if also_publish else 'SUBMIT',
            company_or_portal='company', material_title=publication.material.title)

        return publisher_membership.material_or_publication_grid_row(publication.material)


@article_bp.route(
    '/publish/<string:publication_id>/actor_membership_id/<string:actor_membership_id>/request_from/<string:request_from>/',
    methods=['OK'], permissions=UserIsActive())
def publish(json, publication_id, actor_membership_id, request_from):
    action = g.req('action', allowed=['load', 'validate', 'save'])

    publication = Publication.get(publication_id)

    actor_membership = MemberCompanyPortal.get(actor_membership_id)
    publisher_membership = MemberCompanyPortal.get_by_portal_id_company_id(
        publication.portal_division.portal_id, publication.material.company_id)

    if action == 'load':
        return publish_dialog_load(publication, publisher_membership)
    else:
        publish_dialog_save(publication, json['publication'], status=Publication.STATUSES['PUBLISHED'])

    if action == 'validate':
        publication.detach()
        return publication.validate(True)
    else:
        publication.save()
        utils.db.execute_function("tag_publication_set_position('%s', ARRAY ['%s']);" %
                                  (publication.id, "', '".join([t.id for t in publication.tags])))

        actor_membership.NOTIFY_MATERIAL_ACTION_BY_COMPANY_OR_PORTAL(
            action='PUBLISH', material_title=publication.material.title,
            company_or_portal='company' if request_from == 'company_material_details' else 'portal')

        if request_from == 'company_material_details':
            return actor_membership.material_or_publication_grid_row(publication.material)
        elif request_from == 'portal_publications':
            return publication.portal_publication_grid_row(actor_membership)


# @article_bp.route('/<string:company_id>/gallery_save/<string:material_id>/', methods=['OK'], permissions=UserIsActive())
# @article_bp.route('/<string:company_id>/gallery_save/', methods=['OK'], permissions=UserIsActive())
# def gallery_save(json, company_id, material_id=None):
#     gallery = MaterialImageGallery.get(json['gallery_id']) if json.get('gallery_id') else MaterialImageGallery().save()
#     gallery.material = Material.get(material_id) if material_id else None
#     gallery.width = json['parameters']['gallery_width']
#     gallery.height = json['parameters']['gallery_height']
    #
    # for item in gallery.items:
    #     if len(list(filter(lambda x: x['id'] == item.id, json['images']))) < 1:
    #         item.delete()
    #
    # position = 0
    # for item_data in json['images']:
    #     position += 1
    #     if item_data['id']:
    #         item = MaterialImageGalleryItem.get(item_data['id'])
    #     else:
    #         item = MaterialImageGalleryItem(binary_data=item_data['binary_data'],
    #                                         material_image_gallery=gallery,
    #                                         name=item_data['title'])
    #         gallery.items.append(item)
    #
    #     item.position = position
    #     item.title = item_data['title']
    #     item.file.copyright_author_name = item_data['copyright']
    #
    # gallery.save()
    # return gallery.get_client_side_dict(more_fields='items')


# @article_bp.route('/gallery_load/<string:material_id>/', methods=['OK'], permissions=UserIsActive())
# def gallery_load(json, material_id):
#     gallery = MaterialImageGallery.get(json['gallery_id'])
#     return gallery.get_client_side_dict(more_fields='items')
