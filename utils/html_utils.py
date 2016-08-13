import re

# TODO: YG by OZ: remove this file

def clean_html_tags(html):
    """This function accept text with html tags and return text without html tags"""
    cleaner = re.compile('<.*?>')
    text = re.sub(cleaner, '', html)
    return text
