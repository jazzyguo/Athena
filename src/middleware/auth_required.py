from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

def auth_required(fn):
    @wraps(fn)
    def decorated(*args, **kwargs):
        verify_jwt_in_request()
        current_user = get_jwt_identity()
        # Perform any additional user authorization checks here if needed
        return fn(current_user, *args, **kwargs)
    return decorated
