# src/ml_classifier/config/security.py
import os

# JWT Settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_key_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 8 * 60

# Password Settings
PASSWORD_MIN_LENGTH = 5
PASSWORD_REQUIRE_UPPERCASE = False
PASSWORD_REQUIRE_DIGIT = False
BCRYPT_SALT_ROUNDS = 12
