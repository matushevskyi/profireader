import sys

sys.path.append('..')

from profapp.models.profiler import PRBase
from profapp.models.company import Company, NewsFeedCompany
from profapp.models.materials import Material
from profapp.models.users import User
from flask import g, url_for

from sqlalchemy.sql import text, and_, or_
from sqlalchemy import func

from profapp import create_app, prepare_connections, utils
import argparse
import datetime
import feedparser
import re
from bs4 import BeautifulSoup
from profapp.constants.RECORD_IDS import SYSTEM_USERS


app = create_app(apptype='read_company_data_feeds', config='config.CommandLineConfig')
import pprint
ppr = pprint.PrettyPrinter(indent=2, compact=True, width=120)

def grab_illustration_from_item(item, material):

    ppr.pprint(item)

    # images = re.match(r'<img[^>]+src="([^"]+)"[^>]*>', item['description'])

    # if images:
    #     illustration_data = {cropper: material.illustration.cropper_data(),
    #                          selected_by_user: {
    #                              {'type': "upload",
    #                               'file': {
    #                                   'mime': "image/jpeg",
    #                                   'name': "nice-pictures-005.jpg",
    #                                     'content': ''}, }
    #                          }}
    # cropper
    # :
    # {aspect_ratio: [1.25, 1.25], upload: true, browse: false,…}
    # selected_by_user
    # :
    # {type: "upload", file: {mime: "image/jpeg", name: "nice-pictures-005.jpg",…}, …}
    # crop
    # :
    # {origin_zoom: 0.203125, origin_left: 0, origin_top: 0, crop_left: 210, crop_top: 0,
    #  crop_width: 1500,…}
    # crop_height
    # :
    # 1200
    # crop_left
    # :
    # 210
    # crop_top
    # :
    # 0
    # crop_width
    # :
    # 1500
    # origin_left
    # :
    # 0
    # origin_top
    # :
    # 0
    # origin_zoom
    # :
    # 0.203125
    # file
    # :
    # {mime: "image/jpeg", name: "nice-pictures-005.jpg",…}
    # content
    # :
    # "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD//gA7Q1JFQVRPUjogZ2QtanBlZyB2MS4wICh1c2luZyBJSkcgSlBFRyB2NjIpLCBxdWFsaXR5ID0gOTUK/9sAQwACAQEBAQECAQEBAgICAgIEAwICAgIFBAQDBAYFBgYGBQYGBgcJCAYHCQcGBggLCAkKCgoKCgYICwwLCgwJCgoK/9sAQwECAgICAgIFAwMFCgcGBwoKCgoNb3dn5xEdxFKhR0cA/MME/TNV28AWt1ptpa3nijVprnTr77XpepzzRPcWknktB8pMexh5TyKd6sT5jEkt8wxhj8XGm4KpJRbu1d2b72vv5nVLAYOVRVJUouSVk7K6XZPe3kcRFc/BfRbmDU7b4UaxchXsknjeZHW2uLm8kslt3SW4wzrcRsj/eQdQxHNeueCvGFh430L+3LO0uLcLf3dnNDc7d6TW1xJbyj5SQRvibBB5GDxnFYCfCrwV/ZsemrDciJHsHO+5Znd7O7N3G7O2Wd2mZmdmJLljk5JNb3hXw9pHhPT5NL0cSLFNqF3ev5j7j5tzcSXEnPpvlbA7DA7VpiMfi8W069SU2tuZt2+8eEwOCwUWsPTjC+/Kkr/AHH/2Q=="
    # mime
    # :
    # "image/jpeg"
    # name
    # :
    # "nice-pictures-005.jpg"
    # type
    # :
    # "upload"
    #
    # material.illustration = json_data['material']['illustration']
    pass

try:
    if __name__ == '__main__':

        parser = argparse.ArgumentParser(description='read data feeds for company (convert items from feeds to materials)')
        args = parser.parse_args()

        with app.app_context():

            prepare_connections(app, echo=True)()

            news_feeds = g.db.query(NewsFeedCompany) \
                .filter(text("seconds_ago(last_pull_tm) > update_interval_seconds")).all()


            if len(news_feeds):
                app.log.info("%s expired data feeds found" % (len(news_feeds),))
                for news_feed in news_feeds:

                    app.log.info(
                        'getting news from news_feed (id={}, source={}, company={})'.format(
                            news_feed.id, news_feed.source, news_feed.company_id))

                    items = feedparser.parse(news_feed.source)['items']


                    for item in items:
                        try:
                            # ppr.pprint(item)
                            item_date_datetime = PRBase.parse_timestamp(item['published'])
                            ppr.pprint(item['published'])


                            if item_date_datetime and \
                                    (news_feed.last_news_tm is None or item_date_datetime > news_feed.last_news_tm):

                                existing_material = g.db.query(Material).filter(and_(
                                    Material.company_id == item['link'],
                                    Material.external_url == news_feed.company_id,
                                    Material.source == 'RSS')).one()

                                if existing_material:
                                    raise Exception('for company_news_feed={} material already exists (material={})'.format(news_feed.id, existing_material.id))

                                material = Material(company_id = news_feed.company_id,
                                                    title=item['title'],
                                                    short = BeautifulSoup(item['description'], "html.parser").text,
                                                    external_url=item['link'],
                                                    author = item.get('author',''),
                                                    keywords=item.get('category',''),
                                                    source = 'RSS',
                                                    editor = User.get(SYSTEM_USERS.profireader()))

                                grab_illustration_from_item(item, material)

                            # material.save()
                            news_feed.last_news_tm = max([item_date_datetime, news_feed.last_news_tm])

                        except Exception as e:
                            ppr.pprint(e)
                            # app.log.warning("error %s converting rss item %s to material" % (e, item))

                news_feed.last_pull_tm = datetime.datetime.utcnow()

                g.db.commit()

            else:
                app.log.info("no news_feeds with expired news found")

except Exception as e:
    app.log.critical(e)
    raise e
