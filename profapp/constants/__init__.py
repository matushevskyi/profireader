

class REGEXP:

    UUID = r'^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$'

    UUID_SHORT = r'^[A-Fa-f0-9]{12}$'

    URL = (r'^[hH][tT][tT][pP][sS]?://' \
          r'(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\.?|' \
        r'localhost|' \
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' \
        r'(?::\d+)?' \
        r'(?:/?|[/?]\S+)$')

    EMAIL = (r'[^@]+@[^@]+\.[^@]+')