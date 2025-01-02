import os
import sys
from flask import Flask

sys.path.append(os.environ["REPOSITORY_HOME"] + "/route/dashb/user")
from dashboard_user_router import dashboard_user_router

# テスト用のFlaskアプリケーション作成
app = Flask(__name__)
app.register_blueprint(dashboard_user_router, url_prefix='/dashb')

def test_ok():
    with app.test_client() as client:
        response = client.get('/dashb/user')
        response_data = response.get_json()
        
        status_code = response_data['statusCode']
        assert status_code == 200