from flask import Blueprint

# [test]
from .dashb.hello_world import hello_world_router

# [admin]
from .dashb.admin.admin_create_agency_user_router import admin_create_agency_user_router
from .dashb.admin.admin_user_login_router import admin_user_login_router
from .dashb.admin.agency_get_companies_router import agency_get_companies_router
from .dashb.admin.agency_register_router import agency_register_router
from .dashb.admin.agency_update_company_router import agency_update_company_router
from .dashb.admin.corporate_get_companies_router import corporate_get_companies_router
from .dashb.admin.corporate_register_router import corporate_register_router
from .dashb.admin.corporate_update_company_router import corporate_update_company_router
from .dashb.admin.individual_get_users_router import individual_get_users_router
from .dashb.admin.individual_update_user_router import individual_update_user_router

# [agency]
from .dashb.agency.agency_user_login_router import agency_user_login_router
from .dashb.agency.agency_user_sms_router import agency_user_sms_router
from .dashb.agency.download_history_router import download_history_router
from .dashb.agency.get_charge_history_router import get_charge_history_router
from .dashb.agency.get_powersupplies_router import get_powersupplies_router
from .dashb.agency.get_stations_router import get_stations_router
from .dashb.agency.get_unpaid_history_router import get_unpaid_history_router
from .dashb.agency.powersupply_register_router import powersupply_register_router
from .dashb.agency.qr_powersupply_info_router import qr_powersupply_info_router
from .dashb.agency.station_register_router import station_register_router
from .dashb.agency.update_charge_fee_router import update_charge_fee_router
from .dashb.agency.update_powersupply_router import update_powersupply_router
from .dashb.agency.update_station_router import update_station_router

# [corporate]
from .dashb.corporate.corporate_user_login_router import corporate_user_login_router

# [common]
from .dashb.common.corporate_get_users_router import corporate_get_users_router
from .dashb.common.corporate_update_user_router import corporate_update_user_router
from .dashb.common.corporate_user_register_router import corporate_user_register_router
from .dashb.common.get_permission_router import get_permission_router
from .dashb.common.agency_user_register_router import agency_user_register_router
from .dashb.common.agency_get_users_router import agency_get_users_router
from .dashb.common.agency_update_user_router import agency_update_user_router

# 統合されたBlueprintの作成
router = Blueprint('router', __name__)

# [test]
router.register_blueprint(hello_world_router, url_prefix='/dashb')

# [admin]
router.register_blueprint(admin_create_agency_user_router, url_prefix='/dashb/admin')
router.register_blueprint(admin_user_login_router, url_prefix='/dashb/admin')
router.register_blueprint(agency_get_companies_router, url_prefix='/dashb/admin')
router.register_blueprint(agency_register_router, url_prefix='/dashb/admin')
router.register_blueprint(agency_update_company_router, url_prefix='/dashb/admin')
router.register_blueprint(corporate_get_companies_router, url_prefix='/dashb/admin')
router.register_blueprint(corporate_register_router, url_prefix='/dashb/admin')
router.register_blueprint(corporate_update_company_router, url_prefix='/dashb/admin')
router.register_blueprint(individual_get_users_router, url_prefix='/dashb/admin')
router.register_blueprint(individual_update_user_router, url_prefix='/dashb/admin')

# [agency]
router.register_blueprint(agency_user_login_router, url_prefix='/dashb/agency')
router.register_blueprint(agency_user_sms_router, url_prefix='/dashb/agency')
router.register_blueprint(download_history_router, url_prefix='/dashb/agency')
router.register_blueprint(get_charge_history_router, url_prefix='/dashb/agency')
router.register_blueprint(get_powersupplies_router, url_prefix='/dashb/agency')
router.register_blueprint(get_stations_router, url_prefix='/dashb/agency')
router.register_blueprint(get_unpaid_history_router, url_prefix='/dashb/agency')
router.register_blueprint(powersupply_register_router, url_prefix='/dashb/agency')
router.register_blueprint(qr_powersupply_info_router, url_prefix='/dashb/agency')
router.register_blueprint(station_register_router, url_prefix='/dashb/agency')
router.register_blueprint(update_charge_fee_router, url_prefix='/dashb/agency')
router.register_blueprint(update_powersupply_router, url_prefix='/dashb/agency')
router.register_blueprint(update_station_router, url_prefix='/dashb/agency')

# [corporate]
router.register_blueprint(corporate_user_login_router, url_prefix='/dashb/corporate')

# [common]
router.register_blueprint(corporate_get_users_router, url_prefix='/dashb/common')
router.register_blueprint(corporate_update_user_router, url_prefix='/dashb/common')
router.register_blueprint(corporate_user_register_router, url_prefix='/dashb/common')
router.register_blueprint(get_permission_router, url_prefix='/dashb/common')
router.register_blueprint(agency_user_register_router, url_prefix='/dashb/common')
router.register_blueprint(agency_get_users_router, url_prefix='/dashb/common')
router.register_blueprint(agency_update_user_router, url_prefix='/dashb/common')
