# from .blueprints_declaration import image_editor_bp
# from flask import render_template, request, url_for, redirect, g
# from config import Config
# from PIL import Image
# from .errors import BadCoordinates, EmptyFieldName
# from profapp.models.files import File, FileContent
# from utils.db_utils import db
# from io import BytesIO
# from time import gmtime, strftime
# import sys
# from ..models.files import File
# from .views_file import file_query
#
#
# @image_editor_bp.route('/<string:img_id>', methods=['GET', 'POST'])
# def image_editor(img_id):
#
#     ratio = Config.IMAGE_EDITOR_RATIO
#     height = Config.HEIGHT_IMAGE
#     thumbnail = File()
#     thumbnail_content = FileContent()
#     size = (int(ratio*height), height)
#     image_id = img_id
#     data = request.form
#
#     if request.method != 'GET':
#         image_query = file_query(File, image_id)
#         image_content = file_query(FileContent, FileContent)
#         image = Image.open(BytesIO(image_content.content))
#         area = [int(a) for a in (data['1x'], data['2y'], data['3width'],
#                                  data['4height'])
#                 if int(a) in range(0, max(image.size))]
#         if not data['6name']:
#                 raise EmptyFieldName
#         elif area:
#
#             angle = int(data["5rotate"])*-1
#             area[2] = (area[0]+area[2])
#             area[3] = (area[1]+area[3])
#             rotated = image.rotate(angle)
#             cropped = rotated.crop(area).resize(size)
#             bytes_file = BytesIO()
#             cropped.save(bytes_file,
#                          image_query.mime.split('/')[-1].upper())
#             thumbnail.md_tm = strftime("%Y-%m-%d %H:%M:%S", gmtime())
#             thumbnail.size = sys.getsizeof(bytes_file.getvalue())
#             thumbnail.name = data['6name']+'.' + \
#                              image_query.name.split('.')[-1]
#             thumbnail.mime = image_query.mime
#             g.db.add(thumbnail)
#             g.db.commit()
#             thumbnail_content.content = bytes_file.getvalue()
#             thumbnail_content.id = thumbnail.id
#             g.db.add(thumbnail_content)
#             g.db.commit()
#             image_id = thumbnail.id
#             return redirect(url_for('image_editor.cropped',
#                                     id=image_id))
#
#         else:
#             g.db.rollback()
#             raise BadCoordinates
#     file = db(File, id=image_id).one()
#
#     return render_template('image_editor.html',
#                            ratio=ratio,
#                            img_id=img_id,
#                            image=file.url()
#                            )
#
#
# @image_editor_bp.route('/cropped/<string:id>')
# def cropped(id):
#     return render_template('cropped_image.html',
#                            image=file_query(File, id).url()
#                            )
#
#
# @image_editor_bp.route('/get_file')
# def get_file():
#     return '//file001.profireader.com/560baa85-31eb-4001-9685-d807fa6b6807/'
