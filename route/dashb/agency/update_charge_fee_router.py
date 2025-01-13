from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

update_charge_fee_router = Blueprint('update_charge_fee', __name__)

@update_charge_fee_router.route('/update_charge_fee', methods=['POST'])
def update_charge_fee():
    conn = None
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # パラメータの取得と検証
        powersupply_id = data.get('powersupply_id')
        location_id = data.get('location_id')
        price = data.get('price')

        # priceは必須
        if price is None:
            return jsonify(create_error_response(
                "priceは必須です",
                None
            )), 400

        # powersupply_idとlocation_idの両方が取得できた場合はエラー
        if powersupply_id and location_id:
            return jsonify(create_error_response(
                "powersupply_idとlocation_idは同時に指定できません",
                None
            )), 400

        # どちらも取得できなかった場合もエラー
        if not powersupply_id and not location_id:
            return jsonify(create_error_response(
                "powersupply_idまたはlocation_idのいずれかが必要です",
                None
            )), 400

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
                
                # 実行クエリの選択
                if powersupply_id:
                    update_query = """
                    UPDATE m_powersupply
                    SET price = %s,
                        update_date = %s,
                        update_user = 'API'
                    WHERE powersupply_id = %s;
                    """
                    cursor.execute(update_query, (price, now, powersupply_id))
                else:
                    update_query = """
                    UPDATE m_powersupply
                    SET price = %s,
                        update_date = %s,
                        update_user = 'API'
                    WHERE location_id = %s;
                    """
                    cursor.execute(update_query, (price, now, location_id))

                # 更新された行数を確認
                if cursor.rowcount == 0:
                    return jsonify(create_error_response(
                        "更新対象のデータが見つかりません",
                        None
                    )), 404

                conn.commit()
                logger.info("料金情報の更新に成功しました")

                return jsonify(create_success_response(
                    "料金情報の更新に成功しました",
                    {
                        "powersupply_id": powersupply_id,
                        "location_id": location_id,
                        "price": price
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