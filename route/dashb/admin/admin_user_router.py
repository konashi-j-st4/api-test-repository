from flask import Blueprint, jsonify, request
import json
import logging
import pymysql
import os

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

admin_user_router = Blueprint('admin_user', __name__)

@admin_user_router.route('/login', methods=['POST'])
def admin_login():
    # エラーレスポンスは予め作成
    err_res = {
        "resultCode": "error",
        "data": {}
    }

    try:
        # リクエストボディから情報を取得
        body = request.get_json()
        logger.info('body表示')
        logger.info(body)
        
        if 'userId' in body and 'password' in body:
            userId = body['userId']
            password = body['password']
        else:
            raise ValueError("userId or password is missing in the request body")
            
        # MySQLへの接続情報
        db_user_name = os.environ['USER_NAME']
        db_password = os.environ['PASSWORD']
        end_point = os.environ['END_POINT']
        db_name = os.environ['DB_NAME']
        port = int(os.environ['PORT'])
        
    except Exception as e:
        err_msg = 'Failed to retrieve query parameters or environment variables'
        err_res['message'] = err_msg
        err_res['data']['error'] = str(e)
        logger.error(f"{err_msg}:{str(e)}")
        return jsonify(err_res), 500

    # MySQLに接続
    try:
        conn = pymysql.connect(
            host=end_point,
            user=db_user_name,
            passwd=db_password,
            db=db_name,
            port=port,
            connect_timeout=60
        )
        logger.info("MySQL instance successfully connected to Database.")
        
    except Exception as e:
        err_msg = "MySQL instance failed to connect to Database."
        err_res['message'] = err_msg
        err_res['data']['error'] = str(e)
        logger.error(f"{err_msg}:{str(e)}")
        return jsonify(err_res), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            user_query = """
            SELECT a.user_id 
            FROM m_user a
            INNER JOIN m_user_admin b ON a.user_id = b.user_id
            WHERE a.user_id = %s
            AND b.password = %s
            AND a.user_category = 3;
            """
            cursor.execute(user_query, (userId, password))
            result = cursor.fetchall()
            logger.info(user_query)
            logger.info(result)
            
            if result:
                res = {
                    "resultCode": "success",
                    "message": "You can reset your password.",
                    "data": result
                }
                return jsonify(res), 200
            else:
                res = {
                    "resultCode": "success",
                    "message": "User does not exist.[E001]",
                    "data": ""
                }
                return jsonify(res), 200

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'err.'
        detail_err_msg = 'An error occurred while executing the query.'
        err_res['message'] = err_msg
        err_res['data']['error'] = detail_err_msg
        logger.error(f"{err_msg}:{detail_err_msg}")
        return jsonify(err_res), 500
        
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
