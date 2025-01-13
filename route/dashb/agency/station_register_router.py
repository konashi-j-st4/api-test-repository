from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def generate_app_location_number(cursor, agency_id):
    # 最新のapp_location_numberを取得
    query = """
    SELECT app_location_number 
    FROM m_location 
    WHERE agency_id = %s 
    ORDER BY app_location_number DESC 
    LIMIT 1
    """
    cursor.execute(query, (agency_id,))
    result = cursor.fetchone()

    if result:
        # 既存のapp_location_numberがある場合、1を加算
        last_number = int(result[0])
        app_location_number = last_number + 1
    else:
        # 新規の場合、1から開始
        new_number = 1

        # agency_idの桁数を取得
        agency_id_length = len(str(agency_id))

        # 4桁になるようにゼロパディング
        padding_length = 4 - agency_id_length
        padded_number = str(new_number).zfill(padding_length)

        # agency_id と padded_number を結合
        app_location_number = f"{agency_id}{padded_number}"

    return app_location_number

station_register_router = Blueprint('station_register', __name__)

@station_register_router.route('/station_register', methods=['POST'])
def station_register():
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
        required_fields = [
            'user_id', 'station_name', 'zip_code', 'prefecture',
            'city', 'address', 'open_time', 'end_time', 'open_day'
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify(create_error_response(
                f"必須パラメータが不足しています: {', '.join(missing_fields)}",
                None
            )), 400

        # パラメータの取得
        user_id = data['user_id']
        station_name = data['station_name']
        zip_code = data['zip_code']
        prefecture = data['prefecture']
        city = data['city']
        address = data['address']
        building = data.get('building')  # オプショナル
        open_time = data['open_time']
        end_time = data['end_time']
        open_day = data['open_day']
        logger.info('パラメータの取得が完了しました')

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

        try:
            with conn.cursor() as cursor:
                # ユーザーに対応する企業IDを取得
                user_query = 'SELECT agency_id FROM m_user_agency WHERE user_id = %s'
                cursor.execute(user_query, (user_id,))
                result = cursor.fetchone()
                
                if not result:
                    return jsonify(create_error_response(
                        f"ユーザーID {user_id} に対応する企業IDが見つかりません",
                        None
                    )), 404

                agency_id = result[0]
                logger.info('企業IDの取得に成功しました')

                # app_location_numberを生成
                app_location_number = generate_app_location_number(cursor, agency_id)

                # 現在時刻を取得
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # 実行クエリ
                insert_query = """
                INSERT INTO m_location (
                    agency_id, app_location_number, station_name,
                    zip_code, prefecture, city, address, building,
                    open_time, end_time, open_day,
                    create_date, create_user, update_date, update_user, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """
                cursor.execute(insert_query, (
                    agency_id, app_location_number, station_name,
                    zip_code, prefecture, city, address, building,
                    open_time, end_time, open_day,
                    now, 'Dashboard', now, 'Dashboard', 1
                ))
                conn.commit()
                logger.info("ステーション情報の登録に成功しました")

                return jsonify(create_success_response(
                    "ステーション情報の登録に成功しました",
                    {"app_location_number": app_location_number}
                )), 200

        except Exception as e:
            logger.error(f"クエリ実行中にエラーが発生しました: {str(e)}")
            if conn and conn.open:
                conn.rollback()
                logger.info("トランザクションをロールバックしました")
            return jsonify(create_error_response(
                "クエリ実行中にエラーが発生しました",
                str(e)
            )), 500

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "パラメータまたは環境変数の取得に失敗しました",
            str(e)
        )), 500

    finally:
        if conn and conn.open:
            conn.close()
            logger.info("データベース接続を終了しました") 