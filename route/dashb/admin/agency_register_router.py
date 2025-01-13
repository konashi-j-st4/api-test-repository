from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
import random
from response.response_base import create_success_response, create_error_response

# RDS設定
db_user_name = os.environ['USER_NAME']
db_password = os.environ['PASSWORD']
end_point = os.environ['END_POINT']
db_name = os.environ['DB_NAME']
port = int(os.environ['PORT'])

# ロガー設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def generate_unique_number(cursor, table, column, length):
    for _ in range(5):  # 5回まで試行
        number = ''.join([str(random.randint(0, 9)) for _ in range(length)])
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = %s", (number,))
        if cursor.fetchone()[0] == 0:
            return number
    # 5回試行しても重複する場合はエラーを発生させる
    raise ValueError(f"Failed to generate a unique {column} after 5 attempts")

agency_register_router = Blueprint('agency_register', __name__)

@agency_register_router.route('/agency_register', methods=['POST'])
def agency_register():
    conn = None

    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        
        # 必須フィールドの取得と検証
        required_fields = ['agency', 'zip_code', 'prefecture', 'city', 'address', 'country', 'telephone']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        agency = data['agency']
        zip_code = data['zip_code']
        prefecture = data['prefecture']
        city = data['city']
        address = data['address']
        building = data.get('building')  # オプショナル
        country = data['country']
        telephone = data['telephone']

        # MySQLに接続
        conn = pymysql.connect(
            host=end_point,
            user=db_user_name,
            passwd=db_password,
            db=db_name,
            port=port,
            connect_timeout=60
        )
        logger.info("MySQL instance successfully connected to Database.")

        with conn.cursor() as cursor:
            # トランザクション開始
            conn.begin()

            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            app_agency_number = generate_unique_number(cursor, 'm_agency', 'app_agency_number', 3)
            
            # m_agencyテーブルにインサート
            insert_agency_query = """
            INSERT INTO m_agency (app_agency_number, company, zip_code, prefecture, city, address, building, country, telephone, create_date, create_user, update_date, update_user, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            cursor.execute(insert_agency_query, (app_agency_number, agency, zip_code, prefecture, city, address, building, country, telephone, now, 'admin', now, 'admin', 1))
            
            # 挿入したレコードのagency_idを取得
            select_agency_id_query = "SELECT agency_id FROM m_agency WHERE app_agency_number = %s;"
            cursor.execute(select_agency_id_query, (app_agency_number,))
            result = cursor.fetchone()
            if not result:
                raise ValueError("Failed to retrieve the inserted agency_id")
            agency_id = result[0]
            
            # すべての操作が成功したらコミット
            conn.commit()
            
            logger.info("Agency data was successfully registered in the database.")
            return jsonify(create_success_response(
                "Agency data was successfully registered in the database.",
                {
                    "agency_id": agency_id,
                    "app_agency_number": app_agency_number
                }
            )), 200

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'An error occurred while registering the agency.'
        
        # エラーが発生した場合、DBをロールバック
        if conn and conn.open:
            conn.rollback()
            logger.info("Database transaction rolled back.")
        
        return jsonify(create_error_response(err_msg, str(e))), 500

    finally:
        if conn and conn.open:
            conn.close()