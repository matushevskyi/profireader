import os
from flask import request, render_template, make_response, send_file, g
from flask.ext.login import current_user
from db_init import db_session
from profapp.models.files import File, FileContent
from .blueprints import filemanager_bp
from io import BytesIO
from .request_wrapers import json, parent_folder


root = os.getcwd()+'/profapp/static/filemanager/tmp'
json_result = {"result": {"success": True, "error": None}}

@filemanager_bp.route('/')
def filemanager():
    library = {g.user.personal_folder_file_id: {'name': 'My personal files', 'icon': current_user.gravatar(size=18)}}
    for company in g.user.companies:
        library[company.journalist_folder_file_id]={'name': "%s materisals" % (company.name, ), 'icon': ''}
        library[company.corporate_folder_file_id]={'name': "%s corporate files" % (company.name, ), 'icon': ''}
    return render_template('filemanager.html', library = library)

@filemanager_bp.route('/list/', methods=['POST'])
@json
@parent_folder
def list(parent_id=None):
    return File.list(parent_id=parent_id)


@filemanager_bp.route('/createdir/', methods=['POST'])
@json
@parent_folder
def createdir(parent_id=None):
    return File.createdir(name=request.json['params']['name'],  parent_id=parent_id)

@filemanager_bp.route('/upload/', methods=['POST'])
@json
def upload():
    parent_id = (None if (request.form['parent_id'] == '') else (request.form['parent_id']))
    return File.upload(file=request.files['file-0'], parent_id=parent_id)

# # # #
#
# def upload(result#)# :
#
#     file = request.files['file-1# ']
#     filename = file.filena# me
#     file_db = File# ()
#     file.save(os.path.join(root, filename# ))
#     for tmp_file in os.listdir(root# ):
#         st = os.stat(root+'/'+filenam# e)
#         file_db.name = filena# me
#         file_db.md_tm = time.ctime(os.path.getmtime(root+'/'+filename# ))
#         file_db.ac_tm = time.ctime(os.path.getctime(root+'/'+filename# ))
#         file_db.cr_tm = strftime("%Y-%m-%d %H:%M:%S", gmtime(# ))
#         file_db.size = st[ST_SIZ# E]
#         if os.path.isfile(root+'/'+tmp_file# ):
#             file_db.mime = 'fil# e'
#         els# e:
#             file_db.mime = 'di# r'
#     binary_out = open(root+'/'+filename, 'rb# ')
#     file_db.content = binary_out.read# ()
#     binary_out.close# ()
#     if os.path.isfile(root+'/'+filename# ):
#         os.remove(root+'/'+filenam# e)
#     els# e:
#         os.removedirs(root+'/'+filenam# e)
#     db_session.add(file_d# b)
#     tr# y:
#         db_session.commit# ()
#     except PermissionErro# r:
#         result = {"result":#  {
#                 "success": Fals# e,
#                 "error": "Access denied to remove file# "}
#            #  }
#         db_session.rollback#(# )
#
#     return result

@filemanager_bp.route('/get/<string:id>')
def get(id):
    image_query = file_query(id, File)
    image_query_content = db_session.query(FileContent).filter_by(id=id).first()
    response = make_response()
    response.headers['Content-Type'] = image_query.mime
    response.headers['Content-Disposition'] = 'filename=%s' % image_query.name
    return send_file(BytesIO(image_query_content.content), mimetype=image_query.mime, as_attachment=False)

def file_query(id, table):

    query = db_session.query(table).filter_by(id=id).first()
    return query
