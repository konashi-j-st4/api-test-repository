from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

admin_create_agency_user_router = Blueprint('admin_create_agency_user', __name__)

@admin_create_agency_user_router.route('/admin_create_agency_user', methods=['POST'])
def admin_create_agency_user():
    try:
        # リクエストボディから情報を取得
        body = request.get_json()
        if 'user_id' not in body or 'agency_id' not in body:
            raise ValueError("user_id and agency_id are required in the request body")
            
        user_id = body['user_id']
        agency_id = body['agency_id']
        
        # MySQLへの接続情報
        db_user_name = os.environ['USER_NAME']
        db_password = os.environ['PASSWORD']
        end_point = os.environ['END_POINT']
        db_name = os.environ['DB_NAME']
        port = int(os.environ['PORT'])
    except Exception as e:
        err_msg = 'Failed to retrieve request parameters or environment variables'
        logger.error(f"{err_msg}:{str(e)}")
        return jsonify(create_error_response(err_msg, str(e))), 500

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
        logger.error(f"{err_msg}:{str(e)}")
        return jsonify(create_error_response(err_msg, str(e))), 500

    try:
        with conn.cursor() as cursor:
            # レコードの存在確認
            check_query = "SELECT * FROM m_user_agency WHERE user_id = %s"
            cursor.execute(check_query, (user_id,))
            existing_record = cursor.fetchone()

            if existing_record:
                # レコードが存在する場合はUPDATE
                update_query = """
                UPDATE m_user_agency
                SET agency_id = %s
                WHERE user_id = %s
                """
                cursor.execute(update_query, (agency_id, user_id))
                logger.info(f"Updated record for user_id: {user_id}")
            else:
                # レコードが存在しない場合はINSERT
                insert_query = """
                INSERT INTO m_user_agency (user_id, agency_id, permission, password)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (user_id, agency_id, 7, 'admin_user'))
                logger.info(f"Inserted new record for user_id: {user_id}")

            conn.commit()
            return jsonify(create_success_response(
                "User agency information updated successfully.",
                {"user_id": user_id, "agency_id": agency_id}
            )), 200

    except Exception as e:
        conn.rollback()
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'Error occurred during database operation.'
        logger.error(f"{err_msg}:{str(e)}")            
        return jsonify(create_error_response(err_msg, str(e))), 500
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()