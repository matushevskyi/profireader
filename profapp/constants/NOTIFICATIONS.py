from profapp.models.permissions import RIGHT_AT_COMPANY

NOTIFICATION_TYPES = {
    'CUSTOM': 'CUSTOM',
    'FRIENDSHIP_ACTIVITY': 'FRIENDSHIP_ACTIVITY',
    'COMPANY_ACTIVITY': 'COMPANY_ACTIVITY',
    'ARTICLES_ACTIVITY': 'ARTICLES_ACTIVITY',
    'PORTAL_ACTIVITY': 'PORTAL_ACTIVITY',

    'EMPLOYMENT_USER_ACTIVITY': 'EMPLOYMENT_USER_ACTIVITY',
    'EMPLOYMENT_COMPANY_ACTIVITY': 'EMPLOYMENT_COMPANY_ACTIVITY',

    'MEMBERSHIP_COMPANY_ACTIVITY': 'MEMBERSHIP_COMPANY_ACTIVITY',
    'MEMBERSHIP_PORTAL_ACTIVITY': 'MEMBERSHIP_PORTAL_ACTIVITY',
}


class Notify:
    def _ftm(self, date_time):
        return '{:%a, %d %b %Y %H:%M:%S GMT}'.format(date_time)


class NotifyMembership(Notify):
    __publication_kwargs = {
        'rights_at_company': [RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH,
                              RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH],
        'rights_at_portal': [RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH,
                             RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH],
        'notification_type_to_company_employees': NOTIFICATION_TYPES['ARTICLES_ACTIVITY'],
        'notification_type_to_portal_employees': NOTIFICATION_TYPES['ARTICLES_ACTIVITY']
    }

    #    def _call_send_notification_about_membership_change(self, substitute_now={}, *args, **kwargs):
    #        text, dictionary = self._getfunc(substitute_now)
    #        return self._send_notification_about_membership_change(text, dictionary, *args, **kwargs)

    def NOTIFY_PLAN_REQUESTED_BY_COMPANY(self, new_plan_name):
        return self._send_notification_about_membership_change(
            'requested new plan `%(new_plan_name)s` by company',
            {'new_plan_name': new_plan_name})

    def NOTIFY_PLAN_SCHEDULED_BY_COMPANY(self, new_plan_name, date_to_start):
        return self._send_notification_about_membership_change(
            'scheduled new plan `%(new_plan_name)s` by company at `%(date_to_start)s`',
            {'new_plan_name': new_plan_name, 'date_to_start': self._ftm(date_to_start)})

    def NOTIFY_PLAN_STARTED_BY_COMPANY(self, new_plan_name, old_plan_name):
        return self._send_notification_about_membership_change(
            'started new plan `%(new_plan_name)s` instead of `%(old_plan_name)s` by company',
            {'new_plan_name': new_plan_name, 'old_plan_name': old_plan_name})

    def NOTIFY_PLAN_CONFIRMED_BY_PORTAL(self, new_plan_name, old_plan_name, date_to_start):
        return self._send_notification_about_membership_change(
            'requested by company plan `%(new_plan_name)s` was confirmed by portal and scheduled to start at `%(date_to_start)s` instead of `%(old_plan_name)s`',
            {'new_plan_name': new_plan_name, 'old_plan_name': old_plan_name, 'date_to_start': self._ftm(date_to_start)})

    def NOTIFY_PLAN_SCHEDULED_BY_PORTAL(self, new_plan_name, date_to_start):
        return self._send_notification_about_membership_change(
            'scheduled new plan `%(new_plan_name)s` by portal at `%(date_to_start)s`',
            {'new_plan_name': new_plan_name, 'date_to_start': self._ftm(date_to_start)})

    def NOTIFY_PLAN_STARTED_BY_PORTAL(self, new_plan_name, old_plan_name):
        return self._send_notification_about_membership_change(
            'started new plan `%(new_plan_name)s` instead of `%(old_plan_name)s` by portal',
            {'new_plan_name': new_plan_name, 'old_plan_name': old_plan_name})

    # def NOTIFY_PLAN_STARTED_BY_MEMBERSHIP_ACTIVATION_BY_PORTAL(self, new_plan_name):
    #     return self._send_notification_about_membership_change(
    #         'started new plan `%(new_plan_name)s` by membership activation by portal',
    #         {'new_plan_name': new_plan_name})

    # def NOTIFY_PLAN_STARTED_BY_MEMBERSHIP_ACTIVATION_BY_COMPANY(self, new_plan_name):
    #     return self._send_notification_about_membership_change(
    #         'started new plan `%(new_plan_name)s` by membership activation by company',
    #         {'new_plan_name': new_plan_name})

    def NOTIFY_PLAN_STARTED_BY_CRON(self, new_plan_name, old_plan_name):
        return self._send_notification_about_membership_change(
            'scheduled plan `%(new_plan_name)s` was started instead of `%(old_plan_name)s` by cron',
            {'new_plan_name': new_plan_name, 'old_plan_name': old_plan_name})

    def NOTIFY_PLAN_EXPIRED_BUT_NEW_NOT_CONFIRMED(self, new_plan_name, requested_plan_name, default_plan_name):
        return self._send_notification_about_membership_change(
            'old plan `%(old_plan_name)s` was expired but new requested `%(requested_plan_name)s` not confirmed so default plan `%(default_plan_name)s` was started',
            {'new_plan_name': new_plan_name, 'requested_plan_name': requested_plan_name,
             'default_plan_name': default_plan_name})

    def NOTIFY_PLAN_EXPIRED_BUT_NEW_NOT_REQUESTED(self, new_plan_name, requested_plan_name, default_plan_name):
        return self._send_notification_about_membership_change(
            'old plan `%(old_plan_name)s` was expired and no new plan was requested, so default plan `%(default_plan_name)s` was started',
            {'new_plan_name': new_plan_name, 'requested_plan_name': requested_plan_name,
             'default_plan_name': default_plan_name})

    def NOTIFY_STATUS_CHANGED_BY_COMPANY(self, old_status, new_status,
                                         more_phrases_to_portal=[], more_phrases_to_company=[]):
        return self._send_notification_about_membership_change(
            'status of membership changed from `%(old_status)s` to `%(new_status)s` by company' %
            {'old_status': old_status, 'new_status': new_status},
            more_phrases_to_portal=more_phrases_to_portal, more_phrases_to_company=more_phrases_to_company)

    def NOTIFY_MEMBERSHIP_REQUESTED_BY_COMPANY(self):
        return self._send_notification_about_membership_change('membership requested by company')

    def NOTIFY_STATUS_CHANGED_BY_PORTAL(self, old_status, new_status,
                                        more_phrases_to_portal=[], more_phrases_to_company=[]):
        return self._send_notification_about_membership_change(
            'status of membership changed from `%(old_status)s` to `%(new_status)s` by portal' %
            {'old_status': old_status, 'new_status': new_status},
            more_phrases_to_portal=more_phrases_to_portal, more_phrases_to_company=more_phrases_to_company)

    # def NOTIFY_PUBLICATION_PUBLISHED_BY_COMPANY(self, old_status, new_status):
    #     """publication %(name)s"""
    #     return self._send_notification_about_membership_change(**self.__publication_kwargs)
    #
    # def NOTIFY_PUBLICATION_PUBLISHED_BY_PORTAL(self, old_status, new_status):
    #     """publication %(name)s"""
    #     return self._send_notification_about_membership_change(**self.__publication_kwargs)
    #
    # def NOTIFY_PUBLICATION_UNPUBLISHED_BY_COMPANY(self, old_status, new_status):
    #     """publication %(name)s"""
    #     return self._send_notification_about_membership_change(**self.__publication_kwargs)
    #
    # def NOTIFY_PUBLICATION_UNPUBLISHED_BY_PORTAL(self, old_status, new_status):
    #     """publication %(name)s"""
    #     return self._send_notification_about_membership_change(**self.__publication_kwargs)

    def NOTIFY_PUBLICATION_VISIBILITY_CHANGED_BY_PLAN_MEMBERSHIP_CHANGE(
            self, more_phrases_to_company, more_phrases_to_portal):
        return self._call_send_notification_about_membership_change(
            'New plan was applied for membership and changes of publication visibility was made',
            more_phrases_to_company=more_phrases_to_company,
            more_phrases_to_portal=more_phrases_to_portal,
            **self.__publication_kwargs)

    def NOTIFY_PUBLICATION_STILL_HOLDED_DESPITE_BY_PLAN_MEMBERSHIP_CHANGE(
            self, more_phrases_to_company, more_phrases_to_portal):
        return self._call_send_notification_about_membership_change(
            'New plan was applied for membership HOLDED message still remains',
            more_phrases_to_company=more_phrases_to_company,
            more_phrases_to_portal=more_phrases_to_portal,
            **self.__publication_kwargs)


from profapp.models.permissions import RIGHT_AT_COMPANY


class EmploymentChange(Notify):
    def NOTIFY_STATUS_CHANGED_BY_COMPANY(self, old_status, new_status):
        return self._send_notification_about_employment_change(
            'status of employment changed from `%(old_status)s` to `%(new_status)s` by company' %
            {'old_status': old_status, 'new_status': new_status},
            rights_at_company=RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE)

    def NOTIFY_STATUS_CHANGED_BY_COMPANY(self, old_status, new_status):
        return self._send_notification_about_employment_change(
            'status of employment changed from `%(old_status)s` to `%(new_status)s` by company' %
            {'old_status': old_status, 'new_status': new_status},
            rights_at_company=RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE)

    #    def NOTIFY_STATUS_CHANGED_BY_USER(self, old_status, new_status):
    #        """status of employment changed from `%(old_status)s` to `%(new_status)s` by user"""
    #        return self._call_send_notification_about_employment_change(
    #            substitute_now=True,
    #            rights_at_company=RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE)

    def NOTIFY_USER_APPLIED(self):
        return self._send_notification_about_employment_change(
            'user wants to join',
            rights_at_company=RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE)

    def NOTIFY_PORTAL_CREATED(self, portal_host, portal_name):
        from profapp.utils import jinja
        return self._send_notification_about_employment_change(
            'portal %s was created' % (jinja.link_external(),),
            {'portal': {'host': portal_host, 'name': portal_name}})
