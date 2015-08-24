from flask import render_template, redirect, url_for, request, g
from profapp.forms.article import ArticleForm
from profapp.models.articles import Article, ArticleVersion
from profapp.models.users import User
from profapp.models.company import Company
from db_init import db_session
from .blueprints import article_bp
#import os


@article_bp.route('/my/', methods=['GET'])
def show_mine():
    return render_template('article/mine_list.html', articles = Article.list(g.user_dict['id']))

@article_bp.route('/create/', methods=['GET'])
def show_form_create():
    return render_template('article/edit_form.html', article_version = {'name': '', 'short':  '', 'long': ''})

@article_bp.route('/create/', methods=['POST'])
def create():
    return redirect(url_for('article.my_versions', article_id = ArticleVersion(None, **request.form.to_dict(True)).save().article_id))

@article_bp.route('/update/<string:article_version_id>/', methods=['GET'])
def show_form_update(article_version_id):
    return render_template('article/edit_form.html', article_version = Article.get_one_version(article_version_id=article_version_id))

@article_bp.route('/update/<string:article_version_id>/', methods=['POST'])
def update(article_version_id):
    return redirect(url_for('article.my_versions', article_id = ArticleVersion(article_version_id, **request.form.to_dict(True)).save().article_id))

@article_bp.route('/my/versions/<string:article_id>/', methods=['GET'])
def my_versions(article_id):
    return render_template('article/versions.html', article_versions=Article.get_versions(article_id, author_user_id=g.user.id))

