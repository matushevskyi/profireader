import html
from profapp import utils
from flask import url_for
from profapp.models.permissions import RIGHT_AT_COMPANY

NOTIFICATION_TYPES = {
    'PROFIREADER': 'PROFIREADER',
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


class NotifyMembershipChange(Notify):
    __publication_kwargs = {
        'rights_at_company': [RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH,
                              RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH],
        'rights_at_portal': [RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH,
                             RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH],
        'notification_type_to_company_employees': NOTIFICATION_TYPES['ARTICLES_ACTIVITY'],
        'notification_type_to_portal_employees': NOTIFICATION_TYPES['ARTICLES_ACTIVITY']
    }

    def NOTIFY_PLAN_REQUESTED_BY_COMPANY(self, requested_plan_name):
        return self._send_notification_about_membership_change(
            'requested new plan `%(requested_plan_name)s` by company',
            {'requested_plan_name': requested_plan_name})

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

    def NOTIFY_PLAN_EXPIRED_BUT_NEW_NOT_CONFIRMED(self, old_plan_name, requested_plan_name, default_plan_name):
        return self._send_notification_about_membership_change(
            'old plan `%(old_plan_name)s` was expired but new requested `%(requested_plan_name)s` not confirmed so default plan `%(default_plan_name)s` was started',
            {'old_plan_name': old_plan_name, 'requested_plan_name': requested_plan_name,
             'default_plan_name': default_plan_name})

    def NOTIFY_PLAN_EXPIRED_BUT_NEW_NOT_REQUESTED(self, old_plan_name, default_plan_name):
        return self._send_notification_about_membership_change(
            'old plan `%(old_plan_name)s` was expired and no new plan was requested, so default plan `%(default_plan_name)s` was started',
            {'old_plan_name': old_plan_name, 'default_plan_name': default_plan_name})

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

    def NOTIFY_MATERIAL_ACTION_BY_COMPANY_OR_PORTAL(self, material_title, action, company_or_portal,
                                                    more_phrases_to_company=[], more_phrases_to_portal=[]):
        return self._send_notification_about_membership_change(
            '%(company_or_portal)s just %(action)s material `%%(material_title)s`' %
            {'action': action, 'company_or_portal': company_or_portal},
            dictionary={'material_title': material_title},
            more_phrases_to_portal=more_phrases_to_portal, more_phrases_to_company=more_phrases_to_company,
            **self.__publication_kwargs)

    def NOTIFY_MATERIAL_PUBLICATION_BULK_ACTION(self, action, reason, more_phrases_to_company=[],
                                                more_phrases_to_portal=[]):
        return self._send_notification_about_membership_change(
            'following publications was %(action)s because of %(reason)s' % {'action': action, 'reason': reason},
            more_phrases_to_portal=more_phrases_to_portal, more_phrases_to_company=more_phrases_to_company,
            **self.__publication_kwargs)

    def NOTIFY_ARTICLE_VISIBILITY_CHANGED_BY_PLAN_MEMBERSHIP_CHANGE(
            self, more_phrases_to_company, more_phrases_to_portal):
        return self._send_notification_about_membership_change(
            'New plan was applied for membership and changes of publication visibility was made',
            more_phrases_to_company=more_phrases_to_company,
            more_phrases_to_portal=more_phrases_to_portal,
            **self.__publication_kwargs)

    def NOTIFY_ARTICLE_STILL_HOLDED_DESPITE_BY_PLAN_MEMBERSHIP_CHANGE(
            self, more_phrases_to_company, more_phrases_to_portal):
        return self._send_notification_about_membership_change(
            'New plan was applied for membership HOLDED message still remains',
            more_phrases_to_company=more_phrases_to_company,
            more_phrases_to_portal=more_phrases_to_portal,
            **self.__publication_kwargs)


from profapp.models.permissions import RIGHT_AT_COMPANY


class NotifyEmploymentChange(Notify):
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


class NotifyUser(Notify):
    def NOTIFY_FRIEND_STATUS_CHANGED(self, old_status, new_status):
        return self._send_notification(
            'Friendship status changed from `%(old_status)s` to `%(new_status)s`' %
            {'old_status': old_status, 'new_status': new_status},
            notification_type=NOTIFICATION_TYPES['FRIENDSHIP_ACTIVITY'])

    def NOTIFY_WELCOME(self):
        from profapp import MAIN_DOMAIN
        return self._send_notification(
            'Welcome to %s. Get a look at %s' % (
                utils.jinja.link_external(href_placeholder='main_domain', text_placeholder='profireader',
                                          url_prefix='https://'),
                utils.jinja.link('url_tutorial', 'tutorial', True)),
            {'url_tutorial': url_for('tutorial.index'), 'profireader': 'profireader', 'main_domain': MAIN_DOMAIN}
        )

    def NOTIFY_MESSAGE_FROM_PORTAL_FRONT(self, message, company, portal):
        return self._send_notification(
            'You have message from portal %s as member of company %s<hr/>%%(message)s' %
            (utils.jinja.link_external(), utils.jinja.link_company_profile()),
            {'company': company, 'portal': portal, 'message': html.escape(message)},
            notification_type=NOTIFICATION_TYPES['PORTAL_ACTIVITY'])
