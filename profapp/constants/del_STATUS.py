# from profapp.models.rights import Right
#
#
# class STATUS_NAME(dict):
#     ACTIVE = 'ACTIVE'
#     NONACTIVE = 'NONACTIVE'
#     BLOCKED = 'BLOCKED'
#     DELETED = 'DELETED'
#     REJECTED = 'REJECTED'
#     SUSPENDED = 'SUSPENDED'
#
#     @classmethod
#     def __getitem__(cls, attr):
#         return getattr(cls, attr.upper())
#
# STATUS_NAME = STATUS_NAME()
#
#
# class STATUS:
#
#     @staticmethod
#     def NONACTIVE():
#         return 'NONACTIVE'
#
#     @staticmethod
#     def ACTIVE():
#         return 'ACTIVE'
#
#     @staticmethod
#     def BLOCKED():
#         return 'BLOCKED'
#
#     @staticmethod
#     def DELETED():
#         return 'DELETED'
#
#     @staticmethod
#     def REJECTED():
#         return 'REJECTED'
#
#     @staticmethod
#     def SUSPENDED():
#         return 'SUSPENDED'
#
#
# class UserStatusInCompanyRights:
#     _status = None
#     _rights = (0, 0)
#
#     def __init__(self, status, rights_defined=[], rights_undefined=[]):
#         self.status = STATUS_NAME[status]
#         self.rights = (rights_defined, rights_undefined)
#
#     @property
#     def status(self):
#         return self._status
#
#     @status.setter
#     def status(self, stat_name):
#         self._status = stat_name
#
#     @property
#     def rights(self):
#         return self._rights
#
#     @rights.setter
#     def rights(self, rights_def_undef=([], [])):
#         # Some explanation is needed.
#         # if rights_defined is 1 on some bit then this right (permission) is available.
#         # if 0 then we should check the value of rights_undefined column
#         # if it is really 0 then right (permission) is not available.
#         # if it is 1 then this right (permission) should be taken from user_company table.
#         # such construction of rights defines the CheckConstraint presented below.
#         rights_defined = rights_def_undef[0]
#         rights_undefined = rights_def_undef[1]
#         if set(rights_defined) & set(rights_undefined):
#             raise Exception
#         rights_defined_int = Right.transform_rights_into_integer(rights_defined)
#         rights_undefined_int = Right.transform_rights_into_integer(rights_undefined)
#         self._rights = (rights_defined_int, rights_undefined_int)
#
#     @property
#     def rights_defined(self):
#         return self.rights[0]
#
#     @property
#     def rights_undefined(self):
#         return self.rights[1]
#
# # STATUS_RIGHTS = dict()
# #
# # status = 'active'
# # rights_defined = [Right['upload_files'], Right['submit_publications']]
# # rights_undefined = [Right['edit'], Right['publish'], Right['unpublish'], Right['delete_files'],
# #                     Right['add_employee'], Right['suspend_employee'],
# #                     Right['manage_rights_company'], Right['manage_portal'],
# #                     Right['article_priority'],
# #                     Right['manage_companies_members'],
# #                     Right['subscribe_to_portals']]
# # stat_r = UserStatusInCompanyRights(status,
# #                                    rights_defined=rights_defined,
# #                                    rights_undefined=rights_undefined)
# # STATUS_RIGHTS[stat_r.status] = stat_r
# #
# # stat_r = UserStatusInCompanyRights('nonactive')
# # STATUS_RIGHTS[stat_r.status] = stat_r
# #
# # stat_r = UserStatusInCompanyRights('blocked')
# # STATUS_RIGHTS[stat_r.status] = stat_r
# #
# # stat_r = UserStatusInCompanyRights('deleted')
# # STATUS_RIGHTS[stat_r.status] = stat_r
# #
# # stat_r = UserStatusInCompanyRights('rejected')
# # STATUS_RIGHTS[stat_r.status] = stat_r
# #
# # stat_r = UserStatusInCompanyRights('suspended')
# # STATUS_RIGHTS[stat_r.status] = stat_r
# #
