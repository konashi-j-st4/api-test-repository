import json
import logging
import os

# 初期環境
# ローカル環境かどうかを判断
# if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is None:
#     # Zappaの設定ファイルから環境変数を読み込む
#     with open('zappa_settings.json') as json_file:
#         env_vars = json.load(json_file)['dev']['environment_variables']
#         os.environ.update(env_vars)

        
# from db.db_connection import close_db_connection
from flask import Flask 
# ルーターのインポート
from route.router import router 




# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = Flask(__name__)
app.register_blueprint(router)

# DB接続を閉じる
# app.teardown_appcontext(close_db_connection)

if __name__ == '__main__':
    app.run(debug=True)