"""Доменная сущность User."""
from decimal import Decimal
from typing import Optional

from passlib.context import CryptContext
from pydantic import EmailStr, Field

from ml_classifier.domain.entities.base import Entity

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Entity):
    """Пользователь системы."""

    email: EmailStr
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    balance: Decimal = Field(default=Decimal("0.0"), ge=0)

    @classmethod
    def create(
        cls,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> "User":
        """Создать нового пользователя с хэшированным паролем.

        Args:
            email: Email пользователя
            password: Пароль (будет хэширован)
            full_name: Полное имя пользователя
            is_admin: Флаг, является ли пользователь администратором

        Returns:
            User: Новый объект пользователя
        """
        hashed_password = pwd_context.hash(password)
        return cls(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_admin=is_admin,
        )

    def verify_password(self, plain_password: str) -> bool:
        """Проверить соответствие пароля хэшу.

        Args:
            plain_password: Пароль в открытом виде

        Returns:
            bool: True, если пароль соответствует хэшу
        """
        return pwd_context.verify(plain_password, self.hashed_password)

    def check_sufficient_balance(self, amount: Decimal) -> bool:
        """Проверить достаточность средств на балансе.

        Args:
            amount: Требуемая сумма

        Returns:
            bool: True, если на балансе достаточно средств
        """
        return self.balance >= amount
