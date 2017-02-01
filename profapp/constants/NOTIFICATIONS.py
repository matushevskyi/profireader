
#
#
#
# class MembershipChanged:
#     from profapp.models.portal import MemberCompanyPortal
#
#
#     def PLAN_REQUESTED_BY_COMPANY(selfm):
#         """ requested new plan that can`t start automatically and must be confirmed
#                     """
#         return MemberCompanyPortal.send()NOTIFICATIONS.EmploymentChanged('requested new plan `%(new_plan_name)s` by company'). \
#             _send({'new_plan_name': new_plan_name}, more_phrases_to_company, more_phrases_to_portal, except_to_user)


class MembershipChange:

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

    def NOTIFY_PLAN_STARTED_BY_CRON(self, new_plan_name):
        """scheduled plan `%(new_plan_name)s` was started instead of `%(old_plan_name)s` by cron"""
        return self._call_send_notification_about_membership_change()

    def _call_send_notification_about_membership_change(self):
        def getfunc():
            import inspect, gc
            referrers = inspect.currentframe().f_back.f_back
            function = [f for f in gc.get_referrers(referrers.f_code) if type(f) is type(lambda: None)][0]
            arguments = {k: v for k, v in referrers.f_locals.items() if k != 'self'}

            return function, arguments

        f, kwargs = getfunc()
        return self._send_notification_about_membership_change(text=f.__doc__, dictionary=kwargs)

