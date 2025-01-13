def create_success_response(message, data):
    return {
        "resultCode": "success",
        "message": message,
        "data": data
    }

def create_error_response(message, error_detail):
    return {
        "resultCode": "error",
        "message": message,
        "data": {
            "error": error_detail
        }
    }
