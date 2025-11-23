from functools import wraps
from flask import abort
from flask_login import current_user
from app.modules.auth.models import RoleType 

def role_required(roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if current_user.role not in roles:
                abort(403) 
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper