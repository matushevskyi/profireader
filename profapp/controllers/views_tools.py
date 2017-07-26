from flask import render_template, request
from .blueprints_declaration import tools_bp
from ..models.translate import TranslateTemplate
from ..models.files import File
from ..models.permissions import AvailableForAll


@tools_bp.route('/save_translate/', methods=['OK'], permissions=AvailableForAll())
def save_translate(json):
    return TranslateTemplate.getTranslate(json['template'], json['phrase'],
                                          json['url'], json['allow_html'],
                                          phrase_default=json['phrase_default'],
                                          phrase_comment=json['phrase_comment'])


@tools_bp.route('/update_translation_usage/', methods=['OK'], permissions=AvailableForAll())
def update_translation_usage(json):
    for p in json['to_update']:
        TranslateTemplate.update_translation(p['template'], p['phrase'],
                                             phrase_comment=p['phrase_comment'],
                                             phrase_default=p['phrase_default'])
    return True


@tools_bp.route('/SSO/<string:front_cookie>/', methods=['GET'], permissions=AvailableForAll())
def SSO(front_cookie):
    return render_template('tools/sso.html', local_cookie=front_cookie,
                           profi_cookie=request.cookies.get('beaker.session.id'))


@tools_bp.route('/change_allowed_html/', methods=['OK'], permissions=AvailableForAll())
def change_allowed_html(json):
    return TranslateTemplate.update_translation(json['template'], json['phrase'], allow_html=json['allow_html'])


@tools_bp.route('/empty/', methods=['GET'], permissions=AvailableForAll())
def empty():
    return render_template('tools/empty.html')


@tools_bp.route('/pass/<string:password>/', methods=['GET'], permissions=AvailableForAll())
def getpasshash(password):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, method='pbkdf2:sha256',
                                  salt_length=32)


@tools_bp.route('/filecheck/', methods=['GET'], permissions=AvailableForAll())
def filecheck():
    return render_template('tools/filecheck.html')


@tools_bp.route('/filecheck/', methods=['OK'], permissions=AvailableForAll())
def filecheck_load():
    files = File.all()
    return [f.check(['company_id']) for f in files]


@tools_bp.route('/filecheck/<string:fileid>/<string:repair>/', methods=['OK'], permissions=AvailableForAll())
def filecheck_repair(fileid, repair):
    return File.get(fileid).repair(repair, ['company_id'])
