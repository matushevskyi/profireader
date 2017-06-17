from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from .pr_base import PRBase, Base
from .files import FileImg
from .materials import Material


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

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    material_image_gallery_id = Column(TABLE_TYPES['id_profireader'])
    title = Column(TABLE_TYPES['string_1000'])
    copyright = Column(TABLE_TYPES['string_200'])

    small_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id))
    medium_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id))
    big_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id))

    small_file_img_id = relationship(FileImg, uselist=False)
    medium_file_img_id = relationship(FileImg, uselist=False)
    big_file_img_id = relationship(FileImg, uselist=False)

