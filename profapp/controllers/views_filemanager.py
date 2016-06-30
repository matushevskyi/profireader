import os
import re
from flask import render_template, g, make_response
from profapp.models.files import File, YoutubeApi
from .blueprints_declaration import filemanager_bp
from .request_wrapers import ok, tos_required, check_right
from functools import wraps
from flask import jsonify, json
import json as jsonmodule
from flask.ext.login import login_required
from flask import session, redirect, request, url_for
from ..models.google import GoogleAuthorize, GoogleToken
from utils.db_utils import db
from ..models.company import Company, UserCompany
import urllib.parse
from ..models.rights import FilemanagerRights, UserIsActive
import time


def parent_folder(func):
    @wraps(func)
    def function_parent_folder(json, *args, **kwargs):
        ret = func(json, *args, **kwargs)
        return ret

    return function_parent_folder


# TODO: VK by OZ: what is that (root)?
root = os.getcwd() + '/profapp/static/filemanager/tmp'
json_result = {"result": {"success": True, "error": None}}


@filemanager_bp.route('/')
@login_required
@check_right(UserIsActive)
def filemanager():
    last_visit_root_name = ''
    if 'last_root' in request.cookies:
        last_root_id = request.cookies['last_root']
    else:
        last_root_id = ''

    filemanager_company_list = []
    members, main_companies = Company.get_members_for_company()
    uniq = set()
    for n, user_company in enumerate(g.user.employer_assoc):
        if user_company.has_rights(UserCompany.RIGHT_AT_COMPANY.FILES_BROWSE) == True:
            filemanager_company_list.insert(n, File.folder_dict(user_company.employer,
                                               {'can_upload': FilemanagerRights(company=user_company.company_id).action_is_allowed(FilemanagerRights.ACTIONS['UPLOAD'])}))
            uniq.update({user_company.employer.name})
            if user_company.employer.journalist_folder_file_id == last_root_id:
                last_visit_root_name = user_company.employer.name
            if user_company.employer.name in members:
                for member in members[user_company.employer.name]:
                    if member.company.name not in uniq and member.company.name not in main_companies:
                        filemanager_company_list.append(File.folder_dict(member.company,
                                                        {'can_upload': FilemanagerRights(company=member.company.id).action_is_allowed(FilemanagerRights.ACTIONS['UPLOAD'])}))
                        uniq.update({member.company.name})
                        if member.company.journalist_folder_file_id == last_root_id:
                            last_visit_root_name = member.company.name
    # filemanager_company_list.sort(key=lambda k: k['name'])
    file_manager_called_for = request.args[
        'file_manager_called_for'] if 'file_manager_called_for' in request.args else ''
    file_manager_on_action = jsonmodule.loads(
        request.args['file_manager_on_action']) if 'file_manager_on_action' in request.args else {}
    file_manager_default_action = request.args[
        'file_manager_default_action'] if 'file_manager_default_action' in request.args else 'download'
    get_root = request.args[
        'get_root'] if 'get_root' in request.args else None
    if get_root:
        root = Company.get(get_root)
        last_visit_root_name = (root.name) if root else ''
        last_root_id = root.journalist_folder_file_id if root else ''
    err = True if len(filemanager_company_list) == 0 else False
    return render_template('filemanager.html', filemanager_company_list=json.dumps(filemanager_company_list), err=err, last_visit_root=last_visit_root_name.replace(
        '"', '_').replace('*', '_').replace('/', '_').replace('\\', '_').replace('\'', '_'),
                           last_root_id=last_root_id,
                           file_manager_called_for=file_manager_called_for,
                           file_manager_on_action=file_manager_on_action,
                           file_manager_default_action=file_manager_default_action)


@filemanager_bp.route('/list/', methods=['OK'])
@check_right(UserIsActive)
def list(json):
    ancestors = File.ancestors(json['params']['folder_id'])
    company = db(Company, journalist_folder_file_id=ancestors[0]).first()
    if len(json['params'].get('search_text'))>0:
        list = File.list(json['params']['folder_id'], json['params']['file_manager_called_for'],
                         json['params']['search_text'], company_id=company.id)
    else:
        list = File.list(json['params']['folder_id'], json['params']['file_manager_called_for'],company_id=company.id)
    return {'list': list, 'ancestors': ancestors}

@filemanager_bp.route('/createdir/', methods=['OK'])
@check_right(UserIsActive)
def createdir(json):
    if FilemanagerRights(company=get_company_from_folder(json['params']['root_id'])).action_is_allowed(FilemanagerRights.ACTIONS['CREATE_FOLDER']) != True:
        return False
    return File.createdir(name=json['params']['name'],
                          root_folder_id=json['params']['root_id'],
                          parent_id=json['params']['folder_id'])


@filemanager_bp.route('/properties/', methods=['OK'])
@check_right(UserIsActive)
def set_properties(json):
    file = File.get(json['params']['id'])
    if not file or FilemanagerRights(company=get_company_from_folder(json['params']['id'])).action_is_allowed(FilemanagerRights.ACTIONS['UPLOAD']) != True:
        return False
    return File.set_properties(file, json['params']['add_all'], name=json['params']['name'],
                               copyright_author_name=json['params']['author_name'],
                               description=json['params']['description'])


@filemanager_bp.route('/copy/', methods=['OK'])
@check_right(UserIsActive)
def copy(json):
    file = File.get(json['params']['id'])
    if not file or FilemanagerRights(company=get_company_from_folder(json['params']['folder_id'])).action_is_allowed(FilemanagerRights.ACTIONS['UPLOAD']) != True:
        return False
    return file.copy_file(json['params']['folder_id']).id


@filemanager_bp.route('/cut/', methods=['OK'])
@check_right(UserIsActive)
def cut(json):
    file = File.get(json['params']['id'])
    if not file or FilemanagerRights(company=get_company_from_folder(json['params']['id'])).action_is_allowed(FilemanagerRights.ACTIONS['UPLOAD']) != True:
        return False
    return file.move_to(json['params']['folder_id'])


@filemanager_bp.route('/auto_remove/', methods=['OK'])
@check_right(UserIsActive)
def auto_remove(json):
    return File.auto_remove(json.get('list'))

def get_company_from_folder(file_id):
    ancestors = File.ancestors(file_id)
    return db(Company, journalist_folder_file_id=ancestors[0]).first()

@filemanager_bp.route('/remove/<string:file_id>', methods=['OK'])
@check_right(UserIsActive)
def remove(json, file_id):
    file = File.get(file_id)
    ancestors = File.ancestors(file.parent_id)
    if not file or FilemanagerRights(company=db(Company, journalist_folder_file_id=ancestors[0]).first()).action_is_allowed(FilemanagerRights.ACTIONS['REMOVE'], file) != True:
        return False
    return file.remove()

@filemanager_bp.route('/send/<string:parent_id>/', methods=['POST'])
@check_right(UserIsActive)
def send(parent_id):
    parent = File.get(parent_id)
    root = parent.root_folder_id
    if parent.mime == 'root':
        root = parent.id
    company = db(Company, journalist_folder_file_id=root).one()
    if FilemanagerRights(company=company).action_is_allowed(FilemanagerRights.ACTIONS['UPLOAD']) != True:
        return jsonify({'error': True })
    data = request.form
    uploaded_file = request.files['file']
    name = File.get_unique_name(urllib.parse.unquote(uploaded_file.filename).replace(
        '"', '_').replace('*', '_').replace('/', '_').replace('\\', '_'), data.get('ftype'), parent.id)
    data.get('ftype')
    if re.match('^video/.*', data.get('ftype')):
        body = {'title': uploaded_file.filename,
                'description': '',
                'status': 'public'}
        youtube = YoutubeApi(body_dict=body,
                             video_file=uploaded_file.stream.read(-1),
                             chunk_info=dict(chunk_size=int(data.get('chunkSize')),
                                             chunk_number=int(data.get('chunkNumber')),
                                             total_size=int(data.get('totalSize'))),
                             company_id=company.id,
                             root_folder_id=company.journalist_folder_file_id,
                             parent_folder_id=parent_id)
        file = youtube.upload()
    else:
        file = File.upload(name, data, parent.id, root, company, content=uploaded_file.stream.read(-1))
    return jsonify({'result': {'size': 0}, 'error': True if file=='error' else False, 'file_id':file})


@filemanager_bp.route('/resumeupload/', methods=['GET'])
@check_right(UserIsActive)
def resumeupload():
    return jsonify({'size': 0})
