from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def format_time(time_value):
    if isinstance(time_value, str):
        try:
            parsed_time = datetime.datetime.strptime(time_value, "%H:%M:%S").time()
            return parsed_time.strftime("%H:%M")
        except ValueError:
            try:
                datetime.datetime.strptime(time_value, "%H:%M")
                return time_value
            except ValueError:
                logger.error(f"Invalid time format: {time_value}")
                return "00:00"
    elif isinstance(time_value, datetime.time):
        return time_value.strftime("%H:%M")
    elif isinstance(time_value, datetime.timedelta):
        total_minutes = int(time_value.total_seconds() / 60)
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"
    else:
        logger.error(f"Unknown time format: {time_value}")
        return "00:00"

get_stations_router = Blueprint('get_stations', __name__)

@get_stations_router.route('/get_stations', methods=['POST'])
def get_stations():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの確認
        if 'app_user_number' not in data or 'status' not in data:
            return jsonify(create_error_response(
                "app_user_numberとstatusは必須です",
                None
            )), 400

        app_user_number = data['app_user_number']
        status = data['status']
        logger.info(f"Received app_user_number: {app_user_number}, status: {status}")

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
                
                # 実行クエリ
                user_query = """
                SELECT 
                    a.app_user_number,
                    b.location_id,
                    b.station_name,
                    b.agency_id,
                    b.zip_code,
                    b.prefecture,
                    b.city,
                    b.address,
                    b.building,
                    b.open_time,
                    b.end_time,
                    b.open_day,
                    b.status
                FROM m_user_agency a
                INNER JOIN m_location b ON a.agency_id = b.agency_id
                WHERE
                    a.user_id = %s
                    AND b.status = %s;
                """
                cursor.execute(user_query, (user_id, status))
                results = cursor.fetchall()
                logger.info("クエリの実行に成功しました")

                # Format open_time and end_time
                for result in results:
                    result['open_time'] = format_time(result['open_time'])
                    result['end_time'] = format_time(result['end_time'])
                    logger.info(f"時間のフォーマット完了: open_time={result['open_time']}, end_time={result['end_time']}")

                return jsonify(create_success_response(
                    "ステーション情報を取得しました。" if results else "ステーション情報が存在しません。[E001]",
                    results if results else None
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ取得中にエラーが発生しました",
            str(e)
        )), 500 