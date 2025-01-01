import os
import sys
from pathlib import Path

# project_root = Path(__file__).parent.parent.absolute()
# sys.path.append(str(project_root / "app" / "functions"))
from app.functions.hello_world import hello_world

def test_ok ():


    res = hello_world.lambda_handler(1,2)

    status_code = res['statusCode']
    assert status_code == 200