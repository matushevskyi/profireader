from flask import request, url_for, current_app
# from ..controllers.errors import WrongNumberOfParameters, WrongMandatoryParametersPassedToFunction
from functools import reduce
from operator import or_
import inspect
import copy


def redirect_url(*args):
    urls = [request.args.get('next'), url_for('index.index'), request.referrer]
    res_urls = []

    for elem in args:
        res_urls.append(elem)
        urls.remove(elem)

    res_urls += urls

    res_url = ''
    for elem in res_urls:
        res_url = res_url or elem
    return res_url

