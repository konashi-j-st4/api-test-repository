from flask import Blueprint


# 各ルートのインポート



from .dashb.user.dashboard_user_router import dashboard_user_router
# from .dashb.notification.dashboard_notification_router import dashboard_notification_router

# 統合されたBlueprintの作成
router = Blueprint('router', __name__)

# 各Blueprintを統合
# router.register_blueprint(app_user_router, url_prefix='/app')
# router.register_blueprint(app_bill_router, url_prefix='/app')
# router.register_blueprint(app_station_router, url_prefix='/app')
# router.register_blueprint(app_history_router, url_prefix='/app')
# router.register_blueprint(app_charge_history_router, url_prefix='/app')
# router.register_blueprint(app_charge_status_router, url_prefix='/app')
# router.register_blueprint(app_payment_router, url_prefix='/app')
# router.register_blueprint(app_charge_payment_router, url_prefix='/app')
# router.register_blueprint(app_receipt_router, url_prefix='/app')


router.register_blueprint(dashboard_user_router, url_prefix='/dashb')
# router.register_blueprint(dashboard_notification_router, url_prefix='/dashb')
