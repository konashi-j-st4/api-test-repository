import os
import sys

sys.path.append(os.environ["REPOSITORY_HOME"] + "/app/functions")
import hello_world


def test_ok ():


    res = hello_world.lambda_handler(1,2)

    status_code = res['statusCode']
    assert status_code == 200