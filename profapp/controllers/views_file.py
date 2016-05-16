from .blueprints_declaration import file_bp
from flask import request, g, abort
from ..models.files import File, FileContent
from io import BytesIO
from .request_wrapers import check_right
import re
from sqlalchemy import or_
from utils.db_utils import db
from flask import current_app
from werkzeug.datastructures import Headers
import mimetypes
import os
from time import time
from zlib import adler32
from flask._compat import string_types, text_type
import urllib.parse
from ..models.rights import UserIsActive, AllowAll

try:
    from werkzeug.wsgi import wrap_file
except ImportError:
    from werkzeug.utils import wrap_file


def file_query(table, file_id):
    query = g.db.query(table).filter_by(id=file_id).first()
    return query

#@file_bp.route('<string:file_id>')
#def download(file_id):
#    file = file_query(File, file_id)
#    file_c = file_query(FileContent, file_id)
#    if not file or not file_c:
#        abort(404)
#    else:
#        content = file_c.content
#        response = make_response(content)
#        response.headers['Content-Type'] = "application/octet-stream"
#        response.headers['Content-Disposition'] = 'attachment; filename=%s' % urllib.parse.quote(file.name)
#        return response


@file_bp.route('<string:file_id>/')
@file_bp.route('<string:file_id>')
@check_right(AllowAll)
def get(file_id):
    image_query = file_query(File, file_id)

    if not image_query:
        return abort(404)

    if 'HTTP_REFERER' in request.headers.environ:
        allowedreferrer = re.sub(r'^(https?://[^/]+).*$', r'\1', request.headers.environ['HTTP_REFERER'])
    else:
        allowedreferrer = ''

    if allowed_referrers(allowedreferrer):
        image_query_content = g.db.query(FileContent).filter_by(id=file_id).first()
        return send_file(BytesIO(image_query_content.content),
                         mimetype=image_query.mime, as_attachment=(request.args.get('d') is not None),
                         attachment_filename=urllib.parse.quote(
                             image_query.name,
                             safe='!"#$%&\'()*+,-.0123456789:;<=>?@[\]^_`{|}~ ¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸'
                                  '¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ')
                         )
    else:
        return abort(403)


def send_file(filename_or_fp, mimetype=None, as_attachment=False,
              attachment_filename=None, add_etags=True,
              cache_timeout=None, conditional=False, headers={}):



    """Sends the contents of a file to the client.  This will use the
    most efficient method available and configured.  By default it will
    try to use the WSGI server's file_wrapper support.  Alternatively
    you can set the application's :attr:`~Flask.use_x_sendfile` attribute
    to ``True`` to directly emit an `X-Sendfile` header.  This however
    requires support of the underlying webserver for `X-Sendfile`.

    By default it will try to guess the mimetype for you, but you can
    also explicitly provide one.  For extra security you probably want
    to send certain files as attachment (HTML for instance).  The mimetype
    guessing requires a `filename` or an `attachment_filename` to be
    provided.

    Please never pass filenames to this function from user sources without
    checking them first.  Something like this is usually sufficient to
    avoid security problems::

        if '..' in filename or filename.startswith('/'):
            abort(404)

    .. versionadded:: 0.2

    .. versionadded:: 0.5
       The `add_etags`, `cache_timeout` and `conditional` parameters were
       added.  The default behavior is now to attach etags.

    .. versionchanged:: 0.7
       mimetype guessing and etag support for file objects was
       deprecated because it was unreliable.  Pass a filename if you are
       able to, otherwise attach an etag yourself.  This functionality
       will be removed in Flask 1.0

    .. versionchanged:: 0.9
       cache_timeout pulls its default from application config, when None.

    :param filename_or_fp: the filename of the file to send.  This is
                           relative to the :attr:`~Flask.root_path` if a
                           relative path is specified.
                           Alternatively a file object might be provided
                           in which case `X-Sendfile` might not work and
                           fall back to the traditional method.  Make sure
                           that the file pointer is positioned at the start
                           of data to send before calling :func:`send_file`.
    :param mimetype: the mimetype of the file if provided, otherwise
                     auto detection happens.
    :param as_attachment: set to `True` if you want to send this file with
                          a ``Content-Disposition: attachment`` header.
    :param attachment_filename: the filename for the attachment if it
                                differs from the file's filename.
    :param add_etags: set to `False` to disable attaching of etags.
    :param conditional: set to `True` to enable conditional responses.

    :param cache_timeout: the timeout in seconds for the headers. When `None`
                          (default), this value is set by
                          :meth:`~Flask.get_send_file_max_age` of
                          :data:`~flask.current_app`.
    """

    # sleep(5)
    
    mtime = None

    if isinstance(filename_or_fp, string_types):
        filename = filename_or_fp
        file = None
    else:
        from warnings import warn
        file = filename_or_fp
        filename = getattr(file, 'name', None)

        # XXX: this behavior is now deprecated because it was unreliable.
        # removed in Flask 1.0
        if not attachment_filename and not mimetype \
           and isinstance(filename, string_types):
            warn(DeprecationWarning('The filename support for file objects '
                'passed to send_file is now deprecated.  Pass an '
                'attach_filename if you want mimetypes to be guessed.'),
                stacklevel=2)
        if add_etags:
            warn(DeprecationWarning('In future flask releases etags will no '
                'longer be generated for file objects passed to the send_file '
                'function because this behavior was unreliable.  Pass '
                'filenames instead if possible, otherwise attach an etag '
                'yourself based on another value'), stacklevel=2)

    if filename is not None:
        if not os.path.isabs(filename):
            filename = os.path.join(current_app.root_path, filename)
    if mimetype is None and (filename or attachment_filename):
        mimetype = mimetypes.guess_type(filename or attachment_filename)[0]
    if mimetype is None:
        mimetype = 'application/octet-stream'

    default_headers = Headers()
    if as_attachment:
        if attachment_filename is None:
            if filename is None:
                raise TypeError('filename unavailable, required for '
                                'sending as attachment')
            attachment_filename = os.path.basename(filename)
        default_headers.add('Content-Disposition', 'attachment',
                    filename=attachment_filename)

    if current_app.use_x_sendfile and filename:
        if file is not None:
            file.close()
        default_headers['X-Sendfile'] = filename
        default_headers['Content-Length'] = os.path.getsize(filename)
        data = None
    else:
        if file is None:
            file = open(filename, 'rb')
            mtime = os.path.getmtime(filename)
            default_headers['Content-Length'] = os.path.getsize(filename)
        data = wrap_file(request.environ, file)

    for headername in headers:
        default_headers[headername] = headers[headername]

    rv = current_app.response_class(data, mimetype=mimetype, headers=default_headers,
                                    direct_passthrough=True)

    # if we know the file modification date, we can store it as the
    # the time of the last modification.
    if mtime is not None:
        rv.last_modified = int(mtime)

    rv.cache_control.public = True
    if cache_timeout is None:
        cache_timeout = current_app.get_send_file_max_age(filename)
    if cache_timeout is not None:
        rv.cache_control.max_age = cache_timeout
        rv.expires = int(time() + cache_timeout)

    if add_etags and filename is not None:
        rv.set_etag('flask-%s-%s-%s' % (
            os.path.getmtime(filename),
            os.path.getsize(filename),
            adler32(
                filename.encode('utf-8') if isinstance(filename, text_type)
                else filename
            ) & 0xffffffff
        ))
        if conditional:
            rv = rv.make_conditional(request)
            # make sure we don't send x-sendfile for servers that
            # ignore the 304 status code for x-sendfile.
            if rv.status_code == 304:
                rv.headers.pop('x-sendfile', None)
    return rv


def allowed_referrers(domain):
    return True if domain == 'https://profireader.com' or domain == 'https://profireader.com' or \
                   'http://rodynnifirmy.profireader.com' else False


def crop_image(image_id, coordinates, zoom, params):
    from ..models.company import Company
    image_query = db(File, id=image_id).one()  # get file object
    company_owner = db(Company).filter(or_(
                Company.system_folder_file_id == image_query.root_folder_id,
                Company.journalist_folder_file_id == image_query.root_folder_id)).one()  # get company file owner
    return File.crop(image_query, coordinates, zoom, company_owner, params)


