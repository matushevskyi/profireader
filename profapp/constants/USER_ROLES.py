# User role
OWNER = 0
ADMIN = 1
EDITOR = 2
STAFF = 3
CONTRIBUTOR = 4
USER = 5
GUEST = 6
READER = 7

ROLE = {
    OWNER: 'owner',
    ADMIN: 'admin',
    EDITOR: 'editor',
    STAFF: 'staff',
    CONTRIBUTOR: 'contributor',
    USER: 'user',
    GUEST: 'guest',
    READER: 'reader'
}
COMPANY_OWNER = ['comment', 'publish', 'unpublish', 'write_articles', 'moderate_comments', 'manage_content',
                 'manage_members', 'manage_access', 'transfer_ownership']

class RIGHTS:

    def COMMENT(self):
        return 'comment'

    def PUBLISH(self):
        return 'publish'

    def UNPUBLISH(self):
        return 'unpublish'

    def WRITE_ARTICLES(self):
        return 'write_articles'

    def MODERATE_COMMENTS(self):
        return 'moderate_comments'

    def MANAGE_CONTENT(self):
        return 'manage_content'

    def MANAGE_MEMBERS(self):
        return 'manage_members'

    def MANAGE_ACCESS(self):
        return 'manage_access'

    def TRANSFER_OWNERSHIP(self):
        return 'transfer_ownership'
