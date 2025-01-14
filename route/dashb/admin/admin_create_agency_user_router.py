from flask import Blueprint, jsonify, request
import logging
import pymysql
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

admin_create_agency_user_router = Blueprint('admin_create_agency_user', __name__)

@admin_create_agency_user_router.route('/admin_create_agency_user', methods=['POST'])
def admin_create_agency_user():
    try:
        # リクエストボディから情報を取得
        body = request.get_json()
        if 'app_user_number' not in body or 'agency_id' not in body:
            raise ValueError("app_user_number and agency_id are required in the request body")
            
        app_user_number = body['app_user_number']
        agency_id = body['agency_id']
        
    except Exception as e:
        err_msg = 'Failed to retrieve request parameters'
        logger.error(f"{err_msg}:{str(e)}")
        return jsonify(create_error_response(err_msg, str(e))), 500

    try:
        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # app_user_numberからuser_idを取得
                user_id_query = "SELECT user_id FROM m_user WHERE app_user_number = %s"
                cursor.execute(user_id_query, (app_user_number,))
                result = cursor.fetchone()
                
                if not result:
                    return jsonify(create_error_response(
                        "指定されたapp_user_numberに対応するユーザーが見つかりません",
                        None
                    )), 404
                user_id = result['user_id']
                
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
                    logger.info(f"Updated record TO m_user_agency")
                else:
                    # レコードが存在しない場合はINSERT
                    insert_query = """
                    INSERT INTO m_user_agency (user_id, agency_id, permission, password)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (user_id, agency_id, 7, 'admin_user'))
                    logger.info(f"Inserted new record TO m_user_agency")

                return jsonify(create_success_response(
                    "User agency information updated successfully.",
                    {"app_user_number": app_user_number, "agency_id": agency_id}
                )), 200

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'Error occurred during database operation.'
        logger.error(f"{err_msg}:{str(e)}")            
        return jsonify(create_error_response(err_msg, str(e))), 500