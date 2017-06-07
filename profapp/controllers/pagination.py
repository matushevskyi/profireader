from config import Config
import math
from flask import request
from .request_wrapers import ok
from sqlalchemy.orm import load_only


# TODO: OZ by OZ: use pagination function instad
def pagination(query, for_id=None, page=1, items_per_page=Config.ITEMS_PER_PAGE, getPageOfId = None):
    """ Pagination for pages. For use this function you have to pass subquery with all filters,
     number of current page. Also you can change page_size(items per page) from config.
     Return query with pagination parameters, all pages, current page"""



    # query_for_all = query
# TODO OZ by OZ: select only ID, and maybe use some sql function to search page via id (window function)
#     query_for_all.options(load_only("id"))

    count = query.count()

    pages = math.ceil(count/items_per_page)
    #
    # if for_id and tuple(query_for_all).index(for_id) > -1:
    #     page = math.ceil(tuple(query_for_all).index(for_id)+1/items_per_page)-1
    #     print(page)
    if items_per_page:
        query = query.limit(items_per_page)

    if page > 0:
        query = query.offset((page-1)*items_per_page) if int(page) in range(1, int(pages)+1) else \
            query.offset(pages*items_per_page)

    return query, pages, page, count


def load_for_infinite_scroll(query, items=Config.ITEMS_PER_PAGE):

    result = query.limit(items + 1).all()
    return result[0:items], len(result) > items

#
# def get_request_page_filter_order_seek(json):
#
#     search = json.get('search')
#     page = json.get('page')
#     filter_by = json.get('filter')
#     order = json.get('order')
#     seek = json.get('seek')
#     return {'filter_by': filter_by, 'search': search, 'page': page, 'order': order, 'seek': seek}
