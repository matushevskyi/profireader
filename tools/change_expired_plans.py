import sys

sys.path.append('..')

from profapp.models.portal import MemberCompanyPortal, MembershipPlanIssued
from flask import g, url_for

from sqlalchemy.sql import text, and_

from profapp import create_app, load_database
import argparse
import datetime

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='activate requested (and confirmed) plans')
    args = parser.parse_args()

    app = create_app(apptype='profi', config='config.CommandLineConfig')

    with app.app_context():

        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()

        memberships = g.db.query(MemberCompanyPortal) \
            .join(MembershipPlanIssued,
                  MemberCompanyPortal.current_membership_plan_issued_id == MembershipPlanIssued.id). \
            filter(and_(MembershipPlanIssued.calculated_stopping_tm != None,
                        MembershipPlanIssued.calculated_stopping_tm <= datetime.datetime.utcnow())).all()

        if len(memberships):
            print("%s memberships with expired plans found" % (len(memberships),))
            for membership in memberships:
                print('getting new plan for (id, company, portal)',
                      membership.id, membership.company_id, membership.portal_id)

                try:
                    membership.current_membership_plan_issued.stop()

                    if membership.requested_membership_plan_issued and membership.requested_membership_plan_issued.confirmed:
                        print('starting requested plan', membership.requested_membership_plan_issued.id)
                        membership.current_membership_plan_issued = membership.requested_membership_plan_issued
                        membership.current_membership_plan_issued.start()
                        membership.requested_membership_plan_issued = None
                        membership.request_membership_plan_issued_immediately = False
                    else:
                        if membership.requested_membership_plan_issued:
                            print('requested plan is still not confirmed. starting instead default plan')
                            membership.request_membership_plan_issued_immediately = True
                            membership.current_membership_plan_issued = membership.create_issued_plan()
                            membership.current_membership_plan_issued.start()
                        else:
                            print('no new plan requested. starting default plan')
                            membership.current_membership_plan_issued = membership.create_issued_plan()
                            membership.current_membership_plan_issued.start()
                            membership.requested_membership_plan_issued = None
                            membership.request_membership_plan_issued_immediately = False

                    membership.save()
                    g.db.commit()
                except Exception as e:
                    print(e)
        else:
            print("no memberships with expired plans found")
