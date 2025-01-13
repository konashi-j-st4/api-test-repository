from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
from response.response_base import create_success_response, create_error_response

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
    conn = None
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの確認
        if 'userId' not in data or 'status' not in data:
            return jsonify(create_error_response(
                "userIdとstatusは必須です",
                None
            )), 400

        user_id = data['userId']
        status = data['status']
        logger.info(f"Received userId: {user_id}, status: {status}")

        # MySQLに接続
        conn = pymysql.connect(
            host=os.environ['END_POINT'],
            user=os.environ['USER_NAME'],
            passwd=os.environ['PASSWORD'],
            db=os.environ['DB_NAME'],
            port=int(os.environ['PORT']),
            connect_timeout=60
        )
        logger.info("データベースへの接続に成功しました")

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 実行クエリ
            user_query = """
            SELECT 
                a.user_id,
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

    finally:
        if conn and conn.open:
            conn.close()
            logger.info("データベース接続を終了しました") 