from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from .pr_base import PRBase, Base
from .files import FileImageCrop, ImagesDescriptor, File, FileContent
from .materials import Material
import re


class MaterialImageGallery(Base, PRBase):
    __tablename__ = 'material_image_gallery'

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    material_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Material.id))
    # width = Column(TABLE_TYPES['string_10'])
    # height = Column(TABLE_TYPES['string_10'])
    available_sizes = Column(TABLE_TYPES['json'], nullable=False,
                             default=(
                                 [[2048, 2048], [1024, 1024], [512, 512], [256, 256], [128, 128], [64, 64], [32, 32]]))

    material = relationship('Material', uselist=False)
    items = relationship('MaterialImageGalleryItem',
                         order_by='asc(MaterialImageGalleryItem.position)',
                         uselist=True)

    def get_client_side_dict(self, fields='id|material_id', more_fields=None):
        return self.to_dict(fields, more_fields)


class MaterialImageGalleryItem(Base, PRBase):
    __tablename__ = 'material_image_gallery_item'

    def __init__(self, binary_data, name, material_image_gallery: MaterialImageGallery):
        self.material_image_gallery = material_image_gallery
        self.title = name
        from io import BytesIO
        from PIL import Image
        import base64

        import sys

        pillow_image = Image.open(BytesIO(
            base64.b64decode(re.sub('("?\))?$', '', re.sub('^((url\("?)?data:image/.+;base64,)?', '', binary_data)))))
        format = pillow_image.format

        scale_to_image_size = min(self.material_image_gallery.available_sizes[0][0] / pillow_image.width,
                                  self.material_image_gallery.available_sizes[0][1] / pillow_image.height)
        if scale_to_image_size < 1:
            pillow_image = pillow_image.resize((round(pillow_image.width * scale_to_image_size),
                                                round(pillow_image.height * scale_to_image_size)), Image.ANTIALIAS)

        bytes_file = BytesIO()

        pillow_image.save(bytes_file, format)

        self.file = File(size=sys.getsizeof(bytes_file.getvalue()),
                         mime='image/' + format.lower(), name=name,
                         parent_id=material_image_gallery.material.company.system_folder_file_id,
                         root_folder_id=material_image_gallery.material.company.system_folder_file_id)

        FileContent(file=self.file, content=bytes_file.getvalue())

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    material_image_gallery_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(MaterialImageGallery.id))
    title = Column(TABLE_TYPES['string_1000'])
    position = Column(TABLE_TYPES['position'])

    file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(File.id))

    file = relationship(File)
    material_image_gallery = relationship(MaterialImageGallery)

    def get_client_side_dict(self, fields='id,position,title,file_id,file.*', more_fields=None):
        ret = self.to_dict(fields, more_fields)
        return {'id': ret['id'], 'position': ret['position'], 'file_id': ret['file_id'], 'title': ret['title'],
                'copyright': ret['file']['copyright_author_name']}
