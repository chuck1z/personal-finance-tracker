
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash

def create_hashed_password(password):
    return generate_password_hash(password)

def verify_password(hashed_password, password):
    return check_password_hash(hashed_password, password)

def authenticate_user(user, password):
    if user and verify_password(user.password_hash, password):
        access_token = create_access_token(identity=user.id)
        return access_token
    return None
