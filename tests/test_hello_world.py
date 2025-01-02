import os
import sys

sys.path.append(os.environ["REPOSITORY_HOME"] + "/route/dashb/user")
import dashboard_user_router


def test_ok ():


    res = dashboard_user_router.user_home()

    status_code = res['statusCode']
    assert status_code == 200