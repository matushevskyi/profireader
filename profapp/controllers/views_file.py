from .blueprints_declaration import file_bp
from flask import request, g, abort
from ..models.files import File, FileContent, ImageCroped
from io import BytesIO
from PIL import Image
from time import gmtime, strftime
import sys
import re
from sqlalchemy import or_
from config import Config
from utils.db_utils import db
from ..models.company import Company
from flask import current_app
from werkzeug.datastructures import Headers
import mimetypes
import os
from time import time
from zlib import adler32
from flask._compat import string_types, text_type
import urllib.parse

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
def get(file_id):
    image_query = file_query(File, file_id)
    image_query_content = g.db.query(FileContent).filter_by(id=file_id).first()

    if not image_query or not image_query_content:
        return abort(404)

    if 'HTTP_REFERER' in request.headers.environ:
        allowedreferrer = re.sub(r'^(https?://[^/]+).*$', r'\1', request.headers.environ['HTTP_REFERER'])
    else:
        allowedreferrer = ''

    if allowed_referrers(allowedreferrer):
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


def crop_image(image_id, coordinates):
    """
    :param image_id: image id from table File.
    :param coordinates: dict with following parameters: x from 0 - width image,
    - y - from 0 - height of image ,- width- from 0 - width image, height- from 0 - height image
    :return: croped image id from table File.
    """
    image_query = db(File, id=image_id).one() # get file object

    if db(ImageCroped, original_image_id=image_id).count(): # check if croped image already exists

        return update_croped_image(image_id, coordinates) # call function update_croped_image. see func documentation

    company_owner = db(Company).filter(or_(
        Company.system_folder_file_id == image_query.root_folder_id,
        Company.journalist_folder_file_id == image_query.root_folder_id)).one() # get company file owner

    bytes_file, area = crop_with_coordinates(image_query, coordinates) # call function crop_with_coordinates. see func documentation

    if bytes_file: # if func crop_with_coordinates doesn't return False.

        croped = File() # get empty file object

        croped.md_tm = strftime("%Y-%m-%d %H:%M:%S", gmtime()) # set md_tm

        croped.size = sys.getsizeof(bytes_file.getvalue()) # get size from bytes_file(object Image Pillow) and set it to
        # File object

        croped.name = image_query.name + '_cropped' # set name of cropped file. File will continious as _cropped

        croped.parent_id = company_owner.system_folder_file_id # set parent folder(directory) for cropped file
        #  from company owner system folder. System folder should present in company object.

        croped.root_folder_id = company_owner.system_folder_file_id # set root(/) folder(directory) for cropped
        # file from company owner system folder. System folder should present in company object.

        croped.mime = image_query.mime # set file mime for cropped image (mime it's:L
        #A media type (also MIME type and content type)[1] is a two-part identifier for file formats and format
        # contents transmitted on the Internet. The Internet Assigned Numbers Authority (IANA) is the official
        # authority for the standardization and publication of these classifications. Media types were first defined in
        # Request for Comments 2045 in November 1996,[2] at which point they were named MIME
        # (Multipurpose Internet Mail Extensions) types. From WIKI !!! )

        fc = FileContent(content=bytes_file.getvalue(), file=croped) # get FileContent object.
        # content should contain bytes of file produced in bytes_file
        copy_original_image_to_system_folder = \
            File(parent_id=company_owner.system_folder_file_id, name=image_query.name+'_original',
                 mime=image_query.mime, size=image_query.size, user_id=g.user.id,
                 root_folder_id=company_owner.system_folder_file_id, author_user_id=g.user.id)
        # copy original image file to system folder of company, because we save all original files of cropped image
        cfc = FileContent(content=image_query.file_content.content,
                          file=copy_original_image_to_system_folder)
        # copy original image file CONTENT !!! (bytes) to system folder of company,
        #  because we save all original files of cropped image
        g.db.add_all([croped, fc, copy_original_image_to_system_folder, cfc]) # Add all created objects to postgresql
        # transaction
        g.db.flush() # flush transaction, because then we will save id of cropped image from table file to
        # table image_cropped and need id from our created object
        ImageCroped(original_image_id=copy_original_image_to_system_folder.id,
                    croped_image_id=croped.id,
                    x=float(area[0]), y=float(area[1]),
                    width=float(area[2]),
                    height=float(area[3]), rotate=int(coordinates['rotate'])).save() # save
        return croped.id # return cropped file id from table file
    else:
        return image_id # if exception raised we return which pass to our native function
        #(def crop_image(image_id, coordinates):
        # )

        #THE END


def update_croped_image(original_image_id, coordinates):
    """
    call this function when cropped file already exists
    :param original_image_id:  original image id of cropped file from table File.
    :param coordinates: list with following parameters: [0] -x from 0 - width image,
    [1] - y - from 0 - height of image , [2] - width- from 0 - width image,[3] - height- from 0 - height image
    :return: cropped file id from table File
    """
    image_croped_assoc = db(ImageCroped, original_image_id=original_image_id).one() # get image_croped object from table
    # image_croped and filter by original_image_id
    croped = db(File, id=image_croped_assoc.croped_image_id).one()# get cropped file object from table
    # file
    image_query = file_query(File, image_croped_assoc.original_image_id)
    bytes_file, area = crop_with_coordinates(image_query, coordinates, )# call function crop_with_coordinates to get ImagePil
    # object with cropped image and get properly coordinates
    if bytes_file: # if not exception occured in function crop_with_coordinates do
        croped.size = sys.getsizeof(bytes_file.getvalue())# get size from bytes_file(object Image Pillow) and set it to
        # File object


        croped.file_content.content = bytes_file.getvalue() # Get file content (bytes) from saved Pillow object
        image_croped_assoc.x = float(area[0]) # set coordinates to ImageCroped object - x
        image_croped_assoc.y = float(area[1])# set coordinates to ImageCroped object - x
        image_croped_assoc.width = float(area[2])# set coordinates to ImageCroped object - x
        image_croped_assoc.height = float(area[3])# set coordinates to ImageCroped object - x
        image_croped_assoc.rotate = int(coordinates['rotate'])
    return croped.id # cropped file id from table File


def crop_with_coordinates(image, coordinates,  ratio=Config.IMAGE_EDITOR_RATIO,
                          height=Config.HEIGHT_IMAGE):
    """

    :param image: File objects
    :param coordinates: dict with following parameters: x from 0 - width image,
    - y - from 0 - height of image ,- width- from 0 - width image, height- from 0 - height image
    :param ratio: aspect ratio. Default aspect ratio from config
    :param height: height for creating size (int(ratio*height), height)
    :return: cropped bytes of file and area(coordinates)
    """
    size = (int(ratio*height), height) #size for future cropped image
    image_pil = Image.open(BytesIO(image.file_content.content)) # create Pillow object from content of original picture
    try:
        area = [int(a) for a in (coordinates['x'], coordinates['y'], coordinates['width'],
                                 coordinates['height'])] # convert dict of coordinates to list
        if not (area[0] in range(0, image_pil.width)) or not (area[1] in range(0, image_pil.height)): #
            # if coordinates are not correctly, we make coordinates the same as image coordinates
            area[0], area[1], area[2], area[3] = 0, 0, image_pil.width, image_pil.height
        angle = int(coordinates["rotate"])*-1
        area[2] = (area[0]+area[2])# The crop rectangle, as a (left, upper, right, lower)-tuple.    RIGHT
        area[3] = (area[1]+area[3])# The crop rectangle, as a (left, upper, right, lower)-tuple.    LOWER
        rotated = image_pil.rotate(angle)
        cropped = rotated.crop(area).resize(size) # crop and resize image with area and size
        bytes_file = BytesIO() # create BytesIO object to save cropped image to Pillow object
        cropped.save(bytes_file, image.mime.split('/')[-1].upper()) # save cropped image to Pillow object
        # (not to database)
        return bytes_file, area #  cropped bytes of file and area(coordinates)
    except ValueError: # if error occured return False
        return False
