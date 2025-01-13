from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

update_powersupply_router = Blueprint('update_powersupply', __name__)

@update_powersupply_router.route('/update_powersupply', methods=['POST'])
def update_powersupply():
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
        if 'powersupply_id' not in data:
            return jsonify(create_error_response(
                "powersupply_idは必須です",
                None
            )), 400

        # パラメータの取得
        powersupply_id = data['powersupply_id']
        location_id = data.get('location_id')
        powersupply_name = data.get('powersupply_name')
        plan = data.get('plan')
        type = data.get('type')
        wat = data.get('wat')
        price = data.get('price')
        quick_power = data.get('quick_power')
        nomal_power = data.get('nomal_power')
        maintenance = data.get('maintenance')
        online = data.get('online')
        charge_segment = data.get('charge_segment')
        permission = data.get('permission')
        status = data.get('status')

        logger.info(f"更新パラメータ: powersupply_name={powersupply_name}")

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
                UPDATE m_powersupply
                SET location_id = %s,
                    powersupply_name = %s,
                    plan = %s,
                    type = %s,
                    wat = %s,
                    price = %s,
                    quick_power = %s,
                    nomal_power = %s,
                    maintenance = %s,
                    online = %s,
                    charge_segment = %s,
                    permission = %s,
                    status = %s,
                    update_date = %s,
                    update_user = 'Dashboard'
                WHERE powersupply_id = %s;
                """
                cursor.execute(update_query, (
                    location_id, powersupply_name, plan, type, wat,
                    price, quick_power, nomal_power, maintenance,
                    online, charge_segment, permission, status,
                    now, powersupply_id
                ))

                # 更新された行数を確認
                if cursor.rowcount == 0:
                    return jsonify(create_error_response(
                        "更新対象のデータが見つかりません",
                        None
                    )), 404

                conn.commit()
                logger.info("充電器情報の更新に成功しました")

                return jsonify(create_success_response(
                    "充電器情報の更新に成功しました",
                    {
                        "powersupply_id": powersupply_id,
                        "powersupply_name": powersupply_name
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