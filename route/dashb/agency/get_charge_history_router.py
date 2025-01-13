from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

get_charge_history_router = Blueprint('get_charge_history', __name__)

@get_charge_history_router.route('/get_charge_history', methods=['POST'])
def get_charge_history():
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
        if 'start_period' not in data or 'end_period' not in data:
            return jsonify(create_error_response(
                "start_periodとend_periodは必須です",
                None
            )), 400

        start_period = data['start_period']
        end_period = data['end_period']
        app_user_number = data.get('user_id')
        powersupply_ids = data.get('powersupply_ids')

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
                user_id = result[0]
                
                # user_idが存在し、powersupply_idsが未指定の場合にのみクエリを実行
                if user_id and not powersupply_ids:
                    # まずユーザーの権限レベルを取得
                    permission_query = """
                    SELECT permission 
                    FROM m_user_agency 
                    WHERE user_id = %s
                    """
                    cursor.execute(permission_query, (user_id,))
                    permission_result = cursor.fetchone()
                    
                    if not permission_result:
                        return jsonify(create_error_response(
                            f"ユーザーID {app_user_number} の権限が見つかりません",
                            None
                        )), 404
                    
                    user_permission = permission_result['permission']
                    permissions = list(range(1, user_permission + 1))
                    permission_placeholders = ', '.join(['%s'] * len(permissions))

                    # 権限に基づいてpowersupply_idを取得
                    queryUserId = f"""
                    SELECT c.powersupply_id
                    FROM m_user_agency a
                    JOIN m_location b ON a.agency_id = b.agency_id
                    JOIN m_powersupply c ON b.location_id = c.location_id
                    WHERE a.user_id = %s
                    AND c.permission IN ({permission_placeholders})
                    """
                    cursor.execute(queryUserId, (user_id,) + tuple(permissions))
                    resultUserId = cursor.fetchall()

                    # powersupply_idsを抽出
                    powersupply_ids = [item['powersupply_id'] for item in resultUserId]

                if not powersupply_ids:
                    return jsonify(create_success_response(
                        "利用履歴が存在しません。[E001]",
                        None
                    )), 200

                # powersupply_idsをクエリのパラメータとして使用
                placeholders = ', '.join(['%s'] * len(powersupply_ids))
                query = f"""
                SELECT
                    t_charge.transaction_id,
                    t_charge.powersupply_id,
                    t_charge.user_id,
                    t_charge_history.charging_start,
                    t_charge_history.charging_end,
                    t_charge_history.charged_amount,
                    t_charge_history.billing_amount,
                    m_user.app_user_number,
                    m_location.station_name,
                    m_powersupply.app_powersupply_number,
                    m_powersupply.powersupply_name
                FROM
                    t_charge
                JOIN t_charge_history ON t_charge.transaction_id = t_charge_history.transaction_id
                JOIN m_user ON t_charge.user_id = m_user.user_id
                JOIN m_powersupply ON t_charge.powersupply_id = m_powersupply.powersupply_id
                JOIN m_location ON m_powersupply.location_id = m_location.location_id
                WHERE 
                    t_charge.powersupply_id IN ({placeholders})
                AND 
                    t_charge_history.charging_start BETWEEN %s AND %s
                ORDER BY
                    t_charge_history.charging_start ASC;
                """                
                query_params = powersupply_ids + [start_period, end_period]
                cursor.execute(query, query_params)
                result = cursor.fetchall()
                logger.info("クエリの実行に成功しました")

                # datetimeオブジェクトを文字列に変換
                for record in result:
                    record['charging_start'] = record['charging_start'].isoformat() if record['charging_start'] else None
                    record['charging_end'] = record['charging_end'].isoformat() if record['charging_end'] else None

                return jsonify(create_success_response(
                    "利用履歴を取得しました。" if result else "利用履歴が存在しません。[E001]",
                    result if result else None
                )), 200

        except Exception as e:
            logger.error(f"クエリ実行中にエラーが発生しました: {str(e)}")
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