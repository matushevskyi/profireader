import sys

sys.path.append('..')

from profapp.models.portal import MemberCompanyPortal, MembershipPlanIssued
from flask import g, url_for

from sqlalchemy.sql import text, and_

from profapp import create_app, prepare_connections
import argparse
import datetime

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='activate requested (and confirmed) plans')
    args = parser.parse_args()

    app = create_app(apptype='profi', config='config.CommandLineConfig')

    with app.app_context():

        prepare_connections(app)()

        memberships = g.db.query(MemberCompanyPortal) \
            .join(MembershipPlanIssued,
                  MemberCompanyPortal.current_membership_plan_issued_id == MembershipPlanIssued.id). \
            filter(and_(MembershipPlanIssued.calculated_stopping_tm != None,
                        MembershipPlanIssued.calculated_stopping_tm <= datetime.datetime.utcnow())).all()

        if len(memberships):
            g.log('change_expired_plan', "%s memberships with expired plans found" % (len(memberships),))
            for membership in memberships:
                g.log('change_expired_plan', 'getting new plan for (id, company, portal)',
                      membership.id, membership.company_id, membership.portal_id)

                try:
                    membership.current_membership_plan_issued.stop()

                    if membership.requested_membership_plan_issued and membership.requested_membership_plan_issued.confirmed:
                        g.log('change_expired_plan',
                              ['starting requested plan', membership.requested_membership_plan_issued.id])
                        membership.current_membership_plan_issued = membership.requested_membership_plan_issued
                        membership.current_membership_plan_issued.start(inform_portal='launched',
                                                                        inform_company='launched')
                        membership.requested_membership_plan_issued = None
                        membership.request_membership_plan_issued_immediately = False
                    else:
                        if membership.requested_membership_plan_issued:
                            g.log('change_expired_plan',
                                  'requested plan is still not confirmed. starting instead default plan')
                            membership.request_membership_plan_issued_immediately = True
                            membership.current_membership_plan_issued = membership.create_issued_plan()
                            membership.current_membership_plan_issued.start(inform_portal='launched',
                                                                            inform_company='launched')
                        else:
                            g.log('change_expired_plan', 'no new plan requested. starting default plan')
                            membership.current_membership_plan_issued = membership.create_issued_plan()
                            membership.current_membership_plan_issued.start(inform_portal='launched',
                                                                            inform_company='launched')
                            membership.requested_membership_plan_issued = None
                            membership.request_membership_plan_issued_immediately = False

                    membership.save()
                    g.db.commit()

                except Exception as e:
                    print(e)
        else:
            g.log('change_expired_plan', "no memberships with expired plans found")
