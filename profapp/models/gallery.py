from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from .pr_base import PRBase, Base
from .files import File, FileContent
from .materials import Material
from .company import Company
import re


class MaterialImageGallery(Base, PRBase):
    __tablename__ = 'material_image_gallery'

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    material_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Material.id))
    # portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(PortalDivision.id))
    available_sizes = Column(TABLE_TYPES['json'], nullable=False,
                             default=(
                                 [[2048, 2048], [1024, 1024], [512, 512], [256, 256], [128, 128], [64, 64], [32, 32]]))

    material = relationship('Material', uselist=False)
    # portal_division = relationship('PortalDivision', uselist=False)

    items = relationship('MaterialImageGalleryItem',
                         order_by='asc(MaterialImageGalleryItem.position)',
                         cascade="all, delete-orphan",
                         uselist=True)

    def get_client_side_dict(self, fields='id|material_id', more_fields=None):
        return self.to_dict(fields, more_fields)


    @staticmethod
    def check_html(html:str, galleries_cli: list, galleries:list, company_owner: Company):

        def placeholder(id=None):
            return r'(<img[^>]*data-mce-image-gallery-placeholder=")({})("[^>]*>)'.format(id if id else '[^"]*')

        # galleries that was removed from html will be removed from db
        galleries_cli = list(filter(
            lambda x: re.search(placeholder(x['id']), html),
            galleries_cli))


        # remove from db galleries and items removed at client side
        for gallery in galleries:
            g_cli = next(filter(lambda x: x['id'] == gallery.id, galleries_cli), None)
            if not g_cli:
                gallery.delete()
            else:
                for item in gallery.items:
                    if not next(filter(lambda x: x['id'] == item.id, g_cli['items']), None):
                        item.delete()

        for g_cli in galleries_cli:
            gallery = next(filter(lambda x: x.id == g_cli['id'], galleries), None)

            # create gallery that is new
            if not gallery:
                gallery = MaterialImageGallery()
                galleries.append(gallery)
                gallery.save()
                html = re.sub(placeholder(g_cli['id']), r'\g<1>{}\g<3>'.format(gallery.id), html)

            position = 0
            for item_cli in g_cli['items']:
                position += 1
                item = next(filter(lambda x: x.id == item_cli['id'], gallery.items), None)

                # create item that is new
                if not item:
                    item = MaterialImageGalleryItem(
                        binary_data=re.sub(r'[\'"]?\)$', '', re.sub(r'^url\([\'"]?', '', item_cli['background_image'])),
                        material_image_gallery=gallery, name=item_cli['title'],
                        company_owner = company_owner
                    )
                    gallery.items.append(item)

                item.position = position
                item.title = item_cli['title']
                item.file.copyright_author_name = item_cli['copyright']

        return (html, galleries)



class MaterialImageGalleryItem(Base, PRBase):
    __tablename__ = 'material_image_gallery_item'

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    material_image_gallery_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(MaterialImageGallery.id))
    title = Column(TABLE_TYPES['string_1000'])
    position = Column(TABLE_TYPES['position'])

    file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(File.id))

    file = relationship(File)
    material_image_gallery = relationship(MaterialImageGallery)

    def __init__(self, binary_data, name, material_image_gallery: MaterialImageGallery, company_owner = None):
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

        company_owner = company_owner if company_owner else material_image_gallery.material.company

        self.file = File(size=sys.getsizeof(bytes_file.getvalue()),
                         mime='image/' + format.lower(), name=name,
                         parent_id=company_owner.system_folder_file_id,
                         root_folder_id=company_owner.system_folder_file_id)

        FileContent(file=self.file, content=bytes_file.getvalue())

    def get_client_side_dict(self, fields='id,position,title,file_id,file.*', more_fields=None):
        ret = self.to_dict(fields, more_fields)
        return {'id': ret['id'], 'position': ret['position'], 'file_id': ret['file_id'], 'title': ret['title'],
                'copyright': ret['file']['copyright_author_name']}
