import sys

sys.path.append('..')

from profapp.models.profiler import PRBase
from profapp.models.company import Company, NewsFeedCompany
from profapp.models.materials import Material
from profapp.models.users import User
from flask import g, url_for

from sqlalchemy.sql import text, and_, or_

from profapp import create_app, prepare_connections, utils
import argparse
import datetime
import feedparser
import re
from bs4 import BeautifulSoup
from profapp.constants.RECORD_IDS import SYSTEM_USERS
from profapp.models.translate import Phrase


app = create_app(apptype='read_company_data_feeds', config='config.CommandLineConfig', debug = True)

def grab_datetime_from_item(item):
    return PRBase.parse_timestamp(item.get('published', None)) \
           or None


def try_to_grab_illustration(material, *urls):
    for url in [u for u in urls if u]:
        try:
            material.illustration = {'selected_by_user':
                             {'type': "url",
                              'url': url
                              }
                         }
            return True
        except Exception as e:
            app.log.warning("error getting thumbnails for material from url `%s`: `%s`" % (url, e))

    return False



def try_to_guess_more_properties(item):

    import urllib.request as req

    r = req.Request(url=item['link'])
    response = req.urlopen(r)

    body = BeautifulSoup(response.read(), "html.parser")

    keywords = body.find("meta", {'name': "keywords"})
    if keywords:
        keywords = keywords.get('content', None)
    if not keywords:
        keywords = item.get('category', '')

    author = item.get('author', '')

    item['__downloaded_page'] = body

    return {
        'author': author,
        'keywords': keywords,
    }

def convert_item_to_material(item, feed:NewsFeedCompany):

    # item_date_datetime = grab_datetime_from_item(item)

    existing_material = g.db.query(Material).filter(and_(
        Material.company_id == news_feed.company_id,
        Material.external_url == item['link'],
        Material.source_type == 'rss',
        Material.source_id == feed.id
    )).first()

    if existing_material:
        app.log.info(
            'for company_news_feed={} material already exists (material={})'.
                format(news_feed.id, existing_material.id))
        return None

    more_properties = try_to_guess_more_properties(item)

    material = Material(company_id=news_feed.company_id,
                        company=news_feed.company,
                        title=item['title'],
                        short=BeautifulSoup(item['description'], "html.parser").text,
                        external_url=item['link'],
                        source_type='rss',
                        source_id=feed.id,
                        editor=User.get(SYSTEM_USERS.profireader()),
                        **more_properties
                        )

    try:
        downloaded_page = item.get('__downloaded_page', None)
        downloaded_page = downloaded_page.find("meta", {'property': "og:image"}) if downloaded_page else None
        image_in_description = re.match(r'<img[^>]+src="([^"]+)"[^>]*>', item['description'])
        try_to_grab_illustration(material, *[
            downloaded_page.get('content', None) if downloaded_page else None,
            item.get('image', None),
            image_in_description.group(1) if image_in_description else None,
            ])
    except Exception as e:
        app.log.warning("error while converting rss item to material: `%s`" % (e, ))


    return material




try:
    if __name__ == '__main__':

        parser = argparse.ArgumentParser(description='read data feeds for company (convert items from feeds to materials)')
        args = parser.parse_args()

        with app.app_context():

            prepare_connections(app, echo=False)()

            news_feeds = g.db.query(NewsFeedCompany) \
                .filter(text("seconds_ago(last_pull_tm) > update_interval_seconds")).all()

            app.log.info("expired data feeds found: `%s`" % (len(news_feeds),))

            phrases_by_company_id = {}

            for news_feed in news_feeds:
                try:

                    app.log.info(
                        'getting news from news_feed (id=`{}`, name=`{}`, source=`{}`, company=`{}`)'.format(
                        news_feed.id, news_feed.name, news_feed.source, news_feed.company_id))

                    materials_added = 0


                    items = feedparser.parse(news_feed.source)['items']

                    for item in items:
                        app.log.info("converting item `%s` to material" % (item['link']))
                        try:
                            material = convert_item_to_material(item, news_feed)
                            if material:
                                material.save()
                                materials_added += 1
                                utils.dict_deep_replace([], phrases_by_company_id,
                                    news_feed.company_id, add_only_if_not_exists=True).append(
                                        Phrase("created material named `%(a_tag_for_material)s`" %
                                               {'a_tag_for_material': utils.jinja.link('url_material_details', 'material_title')},
                                               dict={'url_material_details': url_for('article.material_details', material_id=material.id),
                                                     'material_title': material.title}))

                        except Exception as e:
                            app.log.warning("error `%s` converting rss item `%s` to material" % (e, item['link']))

                    news_feed.last_pull_tm = datetime.datetime.utcnow()

                    for company_id, phrases in phrases_by_company_id.items():
                        Company.get(company_id).\
                            NOTIFY_MATERIALS_CREATED_FROM_EXTERNAL_SOURCES(
                            news_feed.id, news_feed.name,
                            more_phrases_to_employees=phrases)

                    g.db.commit()

                    app.log.info(
                        'total material added in feed id=`{}`: `{}`'.format(news_feed.id, materials_added))

                except Exception as e:
                    app.log.warning("error `%s` in rss feed `%s` processing" % (e, news_feed.id))



except Exception as e:
    app.log.critical(e)
    raise e
