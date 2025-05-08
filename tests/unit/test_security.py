"""Unit tests for security modules (JWT and password)."""
import datetime
import time
import uuid
from typing import Dict
from typing import Tuple

import pytest
from jose import jwt

from ml_classifier.config.security import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    PASSWORD_MIN_LENGTH,
    PASSWORD_REQUIRE_UPPERCASE,
    PASSWORD_REQUIRE_DIGIT,
)
from ml_classifier.infrastructure.security.jwt import create_access_token, decode_token
from ml_classifier.infrastructure.security.password import (
    get_password_hash,
    validate_email_format,
    validate_password_strength,
    verify_password,
)


class TestPasswordSecurity:
    """Tests for password security functions."""

    def test_password_hash_and_verify(self):
        """Test password hashing and verification."""
        password = "StrongPassword123"
        hashed = get_password_hash(password)

        # Should not be plain text
        assert hashed != password

        # Should be verifiable
        assert verify_password(password, hashed) is True

        # Wrong password should not verify
        assert verify_password("WrongPassword", hashed) is False

    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password meets strength requirements.

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if len(password) < PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters."

        if PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must include at least one uppercase letter."

        if PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            return False, "Password must include at least one digit."

        return True, ""

    def test_validate_password_strength_short(self):
        """Test validation of too short passwords."""
        # Too short
        is_valid, message = validate_password_strength("Short1")
        assert is_valid is False
        assert str(PASSWORD_MIN_LENGTH) in message

    def test_validate_password_strength_no_uppercase(self):
        """Test validation of passwords without uppercase letters."""
        # No uppercase
        is_valid, message = validate_password_strength("nouppercase123")
        assert is_valid is False
        assert "uppercase" in message.lower()

    def test_validate_password_strength_no_digit(self):
        """Test validation of passwords without digits."""
        # No digit
        is_valid, message = validate_password_strength("NoDigitsHere")
        assert is_valid is False
        assert "digit" in message.lower()

    def test_validate_email_format_valid(self):
        """Test validation of valid email formats."""
        assert validate_email_format("user@example.com") is True
        assert validate_email_format("user.name@example.co.uk") is True
        assert validate_email_format("user+tag@example.com") is True

    def test_validate_email_format_invalid(self):
        """Test validation of invalid email formats."""
        assert validate_email_format("not-an-email") is False
        assert validate_email_format("@example.com") is False
        assert validate_email_format("user@") is False
        assert validate_email_format("user@.com") is False


class TestJwtSecurity:
    """Tests for JWT security functions."""

    def test_create_access_token(self):
        """Test creating JWT token."""
        user_id = uuid.uuid4()
        email = "test@example.com"

        token = create_access_token(subject=user_id, email=email)

        # Token should be a string
        assert isinstance(token, str)

        # Token should be properly formatted JWT (header.payload.signature)
        parts = token.split(".")
        assert len(parts) == 3

    def test_decode_token_valid(self):
        """Test decoding a valid JWT token."""
        user_id = uuid.uuid4()
        email = "test@example.com"

        token = create_access_token(subject=user_id, email=email)
        payload = decode_token(token)

        # Check claims
        assert payload["sub"] == str(user_id)
        assert payload["email"] == email
        assert "exp" in payload
        assert "iat" in payload
        assert payload["is_admin"] is False

    def test_decode_token_admin(self):
        """Test decoding a JWT token for admin user."""
        user_id = uuid.uuid4()
        email = "admin@example.com"

        token = create_access_token(subject=user_id, email=email, is_admin=True)
        payload = decode_token(token)

        assert payload["is_admin"] is True

    def test_token_expiration(self):
        """Test token expiration."""
        # Create a token that expires in 1 second
        user_id = uuid.uuid4()

        # Manually create a token with 1 second expiration
        expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)

        to_encode: Dict[str, str] = {
            "sub": str(user_id),
            "email": "test@example.com",
            "exp": expire,
        }

        token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # Token should be valid now
        payload = decode_token(token)
        assert payload["sub"] == str(user_id)

        # Wait for token to expire
        time.sleep(2)

        # Token should be expired now
        with pytest.raises(Exception):
            decode_token(token)
