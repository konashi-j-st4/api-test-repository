import os
import sys
from flask import Flask

sys.path.append(os.environ["REPOSITORY_HOME"] + "/route/dashb/user")
from dashboard_user_router import dashboard_user_router  # Blueprintオブジェクトを直接インポート

# テスト用のFlaskアプリケーション作成
app = Flask(__name__)
app.register_blueprint(dashboard_user_router)

def test_ok():
    with app.app_context():  # アプリケーションコンテキストを作成
        res = dashboard_user_router.user_home()
        response_data = res.get_json()  # JSONレスポンスを取得
        
        status_code = response_data['statusCode']
        assert status_code == 200