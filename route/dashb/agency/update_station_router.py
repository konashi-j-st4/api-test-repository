from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

update_station_router = Blueprint('update_station', __name__)

@update_station_router.route('/update_station', methods=['POST'])
def update_station():
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
        if 'location_id' not in data:
            return jsonify(create_error_response(
                "location_idは必須です",
                None
            )), 400

        # パラメータの取得
        location_id = data['location_id']
        station_name = data.get('station_name')
        zip_code = data.get('zip_code')
        prefecture = data.get('prefecture')
        city = data.get('city')
        address = data.get('address')
        building = data.get('building')
        open_time = data.get('open_time')
        end_time = data.get('end_time')
        open_day = data.get('open_day')
        status = data.get('status', 1)  # デフォルト値1

        logger.info(f"更新パラメータ: station_name={station_name}")

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
                # 現在時刻を取得
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 実行クエリ
                update_query = """
                UPDATE m_location
                SET station_name = %s,
                    zip_code = %s,
                    prefecture = %s,
                    city = %s,
                    address = %s,
                    building = %s,
                    open_time = %s,
                    end_time = %s,
                    open_day = %s,
                    status = %s,
                    update_date = %s,
                    update_user = %s
                WHERE location_id = %s;
                """
                cursor.execute(update_query, (
                    station_name, zip_code, prefecture, city,
                    address, building, open_time, end_time,
                    open_day, status, now, 'Dashboard', location_id
                ))

                # 更新された行数を確認
                if cursor.rowcount == 0:
                    return jsonify(create_error_response(
                        "更新対象のデータが見つかりません",
                        None
                    )), 404

                conn.commit()
                logger.info("ステーション情報の更新に成功しました")

                return jsonify(create_success_response(
                    "ステーション情報の更新に成功しました",
                    {
                        "location_id": location_id,
                        "station_name": station_name
                    }
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
