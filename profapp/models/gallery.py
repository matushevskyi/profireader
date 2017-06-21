from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from .pr_base import PRBase, Base
from .files import FileImg, ImagesDescriptor, File, FileContent
from .materials import Material
import re


class MaterialImageGallery(Base, PRBase):
    __tablename__ = 'material_image_gallery'

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    material_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Material.id))
    width = Column(TABLE_TYPES['string_10'])
    height = Column(TABLE_TYPES['string_10'])

    material = relationship('Material', uselist=False)
    items = relationship('MaterialImageGalleryItem', uselist=True)

    def get_client_side_dict(self, fields='id|material_id|width|height', more_fields=None):
        return self.to_dict(fields, more_fields)


class MaterialImageGalleryItem(Base, PRBase):
    __tablename__ = 'material_image_gallery_item'

    def __init__(self, binary_data, name):
        from io import BytesIO
        from PIL import Image
        import base64

        import sys

        pillow_image = Image.open(BytesIO(
            base64.b64decode(re.sub('("?\))?$', '', re.sub('^((url\("?)?data:image/.+;base64,)?', '', binary_data)))))

        bytes_file = BytesIO()

        pillow_image.save(bytes_file, pillow_image.format)

        self.original_file = File(size=sys.getsizeof(bytes_file.getvalue()),
                             mime='image/' + pillow_image.format.lower(),
                             name=name)

        FileContent(file=self.original_file, content=bytes_file.getvalue())

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    material_image_gallery_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(MaterialImageGallery.id))
    title = Column(TABLE_TYPES['string_1000'])
    copyright = Column(TABLE_TYPES['string_200'])
    position = Column(TABLE_TYPES['position'])

    tiny_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id))
    small_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id))
    medium_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id))
    big_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id))
    huge_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id))
    original_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(File.id))

    original_file = relationship(File, foreign_keys=[original_file_id])

    # images = ImagesDescriptor(image_sizes={'tiny': [100, 100], 'small': [200, 200], 'medium': [400, 400],
    #                                        'big': [800, 800], 'huge': [1600, 1600]})
