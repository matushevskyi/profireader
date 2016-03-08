import os
import re
from flask import render_template, g, make_response
from flask.ext.login import current_user
from profapp.models.files import File, FileContent, YoutubeApi
from .blueprints_declaration import filemanager_bp
from .request_wrapers import ok
from functools import wraps
from time import sleep
from flask import jsonify
import json as jsonmodule
from flask import session, redirect, request, url_for
from ..models.google import GoogleAuthorize, GoogleToken
from utils.db_utils import db
from ..models.company import Company, UserCompany
from ..models.users import User
from ..models.translate import TranslateTemplate
import urllib.parse
import collections
import http.cookies


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
def filemanager():
    last_visit_root_n = ''
    if 'last_root' in request.cookies:
        last_root_id = request.cookies['last_root']
    else:
        last_root_id = ''
    # library = {g.user.personal_folder_file_id:
    # {'name': 'My personal files',
    # 'icon': current_user.gravatar(size=18)}}
    library = []
    can_upload = True
    for user_company in g.user.employer_assoc:
        # TODO VK by OZ: we need function that get all emploees with specific right
        # Company.get_emploees('can_read', status = 'active')
        # Company.get_emploees(['can_read', 'can_write'], status = ['active','banned'])
        # similar function User.get_emploers ...
        can_upload = user_company.has_rights(UserCompany.RIGHT_AT_COMPANY.FILES_BROWSE)
        if user_company.has_rights(UserCompany.RIGHT_AT_COMPANY.FILES_BROWSE):
            library.append({'id': user_company.employer.journalist_folder_file_id,
            'name': "%s files" % (user_company.employer.name,), 'icon': ''})
            if user_company.employer.journalist_folder_file_id == last_root_id:
                last_visit_root_n = user_company.employer.name + " files"
    library.sort(key=lambda k: k['name'])
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
        last_visit_root_n = root.name + " files"
        last_root_id = root.journalist_folder_file_id
    err = True if len(library) == 0 else False
    return render_template('filemanager.html', library=library, err=err, last_visit_root=last_visit_root_n,
                           last_root_id=last_root_id,
                           file_manager_called_for=file_manager_called_for,
                           file_manager_on_action=file_manager_on_action,
                           file_manager_default_action=file_manager_default_action)


@filemanager_bp.route('/list/', methods=['POST'])
@ok
# @parent_folder
def list(json):
    ancestors = File.ancestors(json['params']['folder_id'])
    company = db(Company, journalist_folder_file_id=ancestors[0]).first()
    list = File.list(json['params']['folder_id'], json['params']['file_manager_called_for'],company_id=company.id)
    return {'list': list, 'ancestors': ancestors, 'can_upload': File.if_action_allowed('upload', company.id)}


@filemanager_bp.route('/search/', methods=['POST'])
@ok
def search_list(json):
    if json['params']['search_text'] != '':
        list = File.list(json['params']['folder'], json['params']['file_manager_called_for'],
                         json['params']['search_text'])
        ancestors = File.ancestors(json['params']['folder'])
    else:
        list = []
        ancestors = File.ancestors(json['params']['folder'])
    return {'list': list, 'ancestors': ancestors}


@filemanager_bp.route('/createdir/', methods=['POST'])
@ok
def createdir(json, parent_id=None):
    return File.createdir(name=request.json['params']['name'],
                          root_folder_id=request.json['params']['root_id'],
                          parent_id=request.json['params']['folder_id'])


@filemanager_bp.route('/properties/', methods=['POST'])
@ok
def set_properties(json):
    file = File.get(request.json['params']['id'], )
    return File.set_properties(file, request.json['params']['add_all'], name=request.json['params']['name'],
                               copyright_author_name=request.json['params']['author_name'],
                               description=request.json['params']['description'])


@filemanager_bp.route('/rename/', methods=['POST'])
@ok
def rename(json):
    file = File.get(request.json['params']['id'], )
    return File.rename(file, request.json['params']['name'])


@filemanager_bp.route('/copy/', methods=['POST'])
@ok
def copy(json):
    file = File.get(request.json['params']['id'])
    file.copy_file(request.json['params']['folder_id'])
    return file.id


@filemanager_bp.route('/cut/', methods=['POST'])
@ok
def cut(json):
    file = File.get(request.json['params']['id'])
    return File.move_to(file, request.json['params']['folder_id'])


@filemanager_bp.route('/auto_remove/', methods=['POST'])
@ok
def auto_remove(json):
    return File.auto_remove(json.get('name'), json.get('folder_id'))



@filemanager_bp.route('/remove/<string:file_id>', methods=['POST'])
@ok
def remove(json, file_id):
    file = File.get(file_id)
    ancestors = File.ancestors(file.parent_id)
    return file.remove(db(Company, journalist_folder_file_id=ancestors[0]).first().id)


@filemanager_bp.route('/uploader/', methods=['GET', 'POST'])
@filemanager_bp.route('/uploader/<string:company_id>', methods=['GET', 'POST'])
def uploader(company_id=None):
    token_db_class = GoogleToken()
    credentials_exist = token_db_class.check_credentials_exist()
    google = GoogleAuthorize()
    if not credentials_exist and google.check_admins():
        if 'code' in request.args:
            session['auth_code'] = request.args['code']
            token_db_class.save_credentials()
        return redirect(url_for('company.show')) if 'code' in request.args \
            else redirect(google.get_auth_code())
    return render_template('file_uploader.html', company_id=company_id)


@filemanager_bp.route('/send/<string:parent_id>/', methods=['POST'])
def send(parent_id):
    parent = File.get(parent_id)
    root = parent.root_folder_id
    if parent.mime == 'root':
        root = parent.id
    company = db(Company, journalist_folder_file_id=root).one()
    if File.if_action_allowed('upload', company.id) == False:
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
    return jsonify({'result': {'size': 0}, 'error': True if file=='error' else False})


@filemanager_bp.route('/resumeupload/', methods=['GET'])
def resumeupload():
    return jsonify({'size': 0})
