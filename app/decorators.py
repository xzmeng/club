from functools import wraps
from flask import abort
from flask_login import current_user
from .models import Permission, Club


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)


def club_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        club = Club.query.get_or_404(kwargs.get('club_id'))
        if current_user not in [club.chief, club.vice]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
