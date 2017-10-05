import sys

sys.path.append('..')

from profapp.models.portal import MemberCompanyPortal, MembershipPlanIssued
from flask import g, url_for

from sqlalchemy.sql import text, and_
from sqlalchemy import func

from profapp import create_app, prepare_connections, utils
import argparse
import datetime

app = create_app(apptype='change_expired_plan', config='config.CommandLineConfig')

try:
    if __name__ == '__main__':

        parser = argparse.ArgumentParser(description='activate requested (and confirmed) plans')
        args = parser.parse_args()

        with app.app_context():

            prepare_connections(app, echo=True)()

            memberships = g.db.query(MemberCompanyPortal) \
                .join(MembershipPlanIssued,
                      MemberCompanyPortal.current_membership_plan_issued_id == MembershipPlanIssued.id). \
                filter(and_(MembershipPlanIssued.calculated_stopping_tm != None,
                            MembershipPlanIssued.calculated_stopping_tm <= func.clock_timestamp())).all()

            if len(memberships):
                app.log.info("%s memberships with expired plans found" % (len(memberships),))
                for membership in memberships:
                    app.log.info(
                        'getting new plan for (id={}, company={}, portal={})'.format(membership.id,
                                                                                     membership.company_id,
                                                                                     membership.portal_id))
                    try:
                        membership.current_membership_plan_issued.stop()
                        old_plan_name = membership.current_membership_plan_issued.name
                        app.log.info(
                            'membership (id={}, company_id={}, portal_id={})'.
                                format(membership.id, membership.company_id, membership.portal_id))

                        if membership.requested_membership_plan_issued and membership.requested_membership_plan_issued.confirmed:
                            app.log.info('starting requested issued plan (id={})'.format(
                                membership.requested_membership_plan_issued.id))
                            membership.current_membership_plan_issued = membership.requested_membership_plan_issued
                            membership.current_membership_plan_issued.start()
                            membership.NOTIFY_PLAN_STARTED_BY_CRON(
                                old_plan_name=old_plan_name,
                                new_plan_name=membership.current_membership_plan_issued.name)
                            membership.requested_membership_plan_issued = None
                            membership.request_membership_plan_issued_immediately = False
                        else:
                            if membership.requested_membership_plan_issued:
                                app.log.info('requested plan is still not confirmed. starting instead default plan')
                                membership.request_membership_plan_issued_immediately = True
                                membership.current_membership_plan_issued = membership.create_issued_plan()
                                membership.current_membership_plan_issued.start()
                                membership.NOTIFY_PLAN_EXPIRED_BUT_NEW_NOT_CONFIRMED(
                                    old_plan_name=old_plan_name,
                                    requested_plan_name=membership.requested_membership_plan_issued.name,
                                    default_plan_name=membership.current_membership_plan_issued.name)
                            else:
                                app.log.info('no new plan requested. starting default plan')
                                membership.current_membership_plan_issued = membership.create_issued_plan()
                                membership.current_membership_plan_issued.start()
                                membership.NOTIFY_PLAN_EXPIRED_BUT_NEW_NOT_REQUESTED(
                                    old_plan_name=old_plan_name,
                                    default_plan_name=membership.current_membership_plan_issued.name)
                                membership.requested_membership_plan_issued = None
                                membership.request_membership_plan_issued_immediately = False

                        membership.save()
                        g.db.commit()

                    except Exception as e:
                        app.log.error(e)
                        raise e
            else:
                app.log.info("no memberships with expired plans found")

except Exception as e:
    app.log.critical(e)
    raise e
