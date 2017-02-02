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
    def __getfunc(self, substitute_now={}):
        import inspect, gc
        referrers = inspect.currentframe().f_back.f_back
        function = [f for f in gc.get_referrers(referrers.f_code) if type(f) is type(lambda: None)][0]
        arguments = {k: v for k, v in referrers.f_locals.items() if k != 'self'}

        if substitute_now is True:
            substitute_now = arguments

        return function.__doc__ % substitute_now, {k: v for k, v in arguments.items() if
                                                   k not in substitute_now}


class MembershipChange(Notify):
    __publication_kwargs = {
        'rights_at_company': [RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH,
                              RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH],
        'rights_at_portal': [RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH,
                             RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH],
        'notification_type_to_company_employees': NOTIFICATION_TYPES['ARTICLES_ACTIVITY'],
        'notification_type_to_portal_employees': NOTIFICATION_TYPES['ARTICLES_ACTIVITY']
    }

    def _call_send_notification_about_membership_change(self, substitute_now={}, *args, **kwargs):
        text, dictionary = self.__getfunc(substitute_now)
        return self._send_notification_about_membership_change(text, dictionary, *args, **kwargs)

    def NOTIFY_PLAN_REQUESTED_BY_COMPANY(self, new_plan_name):
        """requested new plan `%(new_plan_name)s` by company"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_SCHEDULED_BY_COMPANY(self, new_plan_name, date_to_start):
        """scheduled new plan `%(new_plan_name)s` by company at `%(date_to_start)s`"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_STARTED_BY_COMPANY(self, new_plan_name, old_plan_name):
        """started new plan `%(new_plan_name)s` instead of `%(old_plan_name)s` by company"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_CONFIRMED_BY_PORTAL(self, new_plan_name, old_plan_name, date_to_start):
        """ requested by company plan `%(new_plan_name)s` was confirmed by portal `%(old_plan_name)s` and scheduled to start at `%(date_to_start)s`"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_CONFIRMED_AND_STARTED_BY_PORTAL(self, new_plan_name, old_plan_name):
        """ requested by company plan `%(new_plan_name)s` was confirmed and started by portal and started instead of `%(old_plan_name)s`"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_SCHEDULED_BY_PORTAL(self, new_plan_name, date_to_start):
        """scheduled new plan `%(new_plan_name)s` by portal at `%(date_to_start)s`"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_STARTED_BY_PORTAL(self, new_plan_name, old_plan_name):
        """started new plan `%(new_plan_name)s` instead of `%(old_plan_name)s` by portal"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_STARTED_BY_MEMBERSHIP_ACTIVATION_BY_PORTAL(self, new_plan_name):
        """started new plan `%(new_plan_name)s` by membership activation by portal"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_STARTED_BY_MEMBERSHIP_ACTIVATION_BY_COMPANY(self, new_plan_name):
        """started new plan `%(new_plan_name)s` by membership activation by company"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_STARTED_BY_CRON(self, new_plan_name, old_plan_name):
        """scheduled plan `%(new_plan_name)s` was started instead of `%(old_plan_name)s` by cron"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_EXPIRED_BUT_NEW_NOT_CONFIRMED(self, new_plan_name, requested_plan_name, default_plan_name):
        """old plan `%(old_plan_name)s` was expired but new requested `%(requested_plan_name)s` not confirmed so default plan `%(default_plan_name)s` was started"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_PLAN_EXPIRED_BUT_NEW_NOT_REQUESTED(self, new_plan_name, requested_plan_name, default_plan_name):
        """old plan `%(old_plan_name)s` was expired and no new plan was requested, so default plan `%(default_plan_name)s` was started"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_STATUS_CHANGED_BY_COMPANY(self, old_status, new_status):
        """status of membership changed from `%(old_status)s` to `%(new_status)s` by company"""
        return self._call_send_notification_about_membership_change(substitute_now=True)

    def NOTIFY_MEMBERSHIP_REQUESTED_BY_COMPANY(self):
        """membership requested by company"""
        return self._call_send_notification_about_membership_change()

    def NOTIFY_STATUS_CHANGED_BY_PORTAL(self, old_status, new_status):
        """status of membership changed from `%(old_status)s` to `%(new_status)s` by portal"""
        return self._call_send_notification_about_membership_change(substitute_now=True)


    def NOTIFY_PUBLICATION_PUBLISHED_BY_COMPANY(self, old_status, new_status):
        """publication %(name)s"""
        return self._call_send_notification_about_membership_change(**self.__publication_kwargs)

    def NOTIFY_PUBLICATION_PUBLISHED_BY_PORTAL(self, old_status, new_status):
        """publication %(name)s"""
        return self._call_send_notification_about_membership_change(**self.__publication_kwargs)

    def NOTIFY_PUBLICATION_UNPUBLISHED_BY_COMPANY(self, old_status, new_status):
        """publication %(name)s"""
        return self._call_send_notification_about_membership_change(**self.__publication_kwargs)

    def NOTIFY_PUBLICATION_UNPUBLISHED_BY_PORTAL(self, old_status, new_status):
        """publication %(name)s"""
        return self._call_send_notification_about_membership_change(**self.__publication_kwargs)



    def NOTIFY_PUBLICATION_VISIBILITY_CHANGED_BY_PLAN_MEMBERSHIP_CHANGE(
            self, more_phrases_to_company, more_phrases_to_portal):
        """New plan was applied for membership and changes of publication visibility was made"""
        return self._call_send_notification_about_membership_change(
            more_phrases_to_company=more_phrases_to_company,
            more_phrases_to_portal=more_phrases_to_portal,
            **self.__publication_kwargs)

    def NOTIFY_PUBLICATION_STILL_HOLDED_DESPITE_BY_PLAN_MEMBERSHIP_CHANGE(
            self, more_phrases_to_company, more_phrases_to_portal):
        """New plan was applied for membership HOLDED message still remains"""
        return self._call_send_notification_about_membership_change(
            more_phrases_to_company=more_phrases_to_company,
            more_phrases_to_portal=more_phrases_to_portal,
            **self.__publication_kwargs)


from profapp.models.permissions import RIGHT_AT_COMPANY


class EmploymentChange(Notify):
    def _call_send_notification_about_employment_change(self, rights_at_company, substitute_now={}):
        return self._send_notification_about_employment_change(rights_at_company=rights_at_company,
                                                               *self.__getfunc(substitute_now))

    def NOTIFY_STATUS_CHANGED_BY_COMPANY(self, old_status, new_status):
        """status of employment changed from `%(old_status)s` to `%(new_status)s` by company"""
        return self._call_send_notification_about_employment_change(
            substitute_now=True,
            rights_at_company=RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE)

    def NOTIFY_STATUS_CHANGED_BY_USER(self, old_status, new_status):
        """status of employment changed from `%(old_status)s` to `%(new_status)s` by user"""
        return self._call_send_notification_about_employment_change(
            substitute_now=True,
            rights_at_company=RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE)

    def NOTIFY_USER_APPLIED(self):
        """user wants to join"""
        return self._call_send_notification_about_employment_change(
            rights_at_company=RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE)

