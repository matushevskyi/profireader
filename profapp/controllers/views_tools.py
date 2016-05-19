from flask import render_template, request
from .blueprints_declaration import tools_bp
from .request_wrapers import ok
from ..models.translate import TranslateTemplate
from .request_wrapers import check_right
from ..models.rights import UserIsActive, AllowAll
from ..models.files import File




# @tools_bp.route('/translate/', methods=['POST'])
# @ok
# def translate(json):
#     translation = TranslateTemplate.getTranslate(request.json['template'], request.json['phrase'])
#     return {'phrase': translation}




@tools_bp.route('/save_translate/', methods=['OK'])
@check_right(AllowAll)
def save_translate(json):
    return TranslateTemplate.getTranslate(request.json['template'], request.json['phrase'], request.json['url'], request.json['allow_html'])


@tools_bp.route('/update_last_accessed/', methods=['OK'])
@check_right(AllowAll)
def update_last_accessed(json):
    return TranslateTemplate.update_last_accessed(json['template'], json['phrase'])

@tools_bp.route('/SSO/<string:local_cookie>/', methods=['GET'])
@check_right(AllowAll)
def SSO(local_cookie):
    return render_template('tools/sso.html', local_cookie=local_cookie, profi_cookie=request.cookies.get('beaker.session.id'))


@tools_bp.route('/change_allowed_html/', methods=['OK'])
@check_right(AllowAll)
def change_allowed_html(json):
    return TranslateTemplate.change_allowed_html(json['template'], json['phrase'], json['allow_html'])


@tools_bp.route('/empty/', methods=['GET'])
def empty():
    return render_template('tools/empty.html')


@tools_bp.route('/filecheck/', methods=['GET'])
def filecheck():
    return render_template('tools/filecheck.html')

@tools_bp.route('/filecheck/', methods=['OK'])
def filecheck_load():
    files  =  File.all()
    return [f.check(['company_id']) for f in files]

@tools_bp.route('/filecheck/<string:fileid>/<string:repair>/', methods=['OK'])
def filecheck_repair(fileid, repair):
    return File.get(fileid).repair(repair, ['company_id'])
