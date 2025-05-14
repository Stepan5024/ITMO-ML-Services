# src/ml_classifier/services/user_use_cases.py
"""Бизнес-логика и варианты использования, связанные с пользователями."""

from typing import Optional, Tuple
from uuid import UUID

from fastapi import Depends
from passlib.context import CryptContext
from loguru import logger

from ml_classifier.domain.entities.user import User
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.security.password import (
    validate_password_strength,
    validate_email_format,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserUseCase:
    """
    Класс, реализующий бизнес-логику для операций с пользователями.
    """

    def __init__(self, user_repository: UserRepository):
        """
        Инициализация с репозиторием пользователей.

        :param user_repository: Репозиторий для взаимодействия с базой данных пользователей
        """
        self.user_repository = user_repository

    async def register_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Регистрация нового пользователя с валидацией данных.

        :param email: Электронная почта пользователя
        :param password: Пароль в открытом виде
        :param full_name: Полное имя пользователя (необязательно)
        :param is_admin: Флаг, указывающий на административные права
        :return: Кортеж (успех, сообщение, созданный пользователь)
        """
        logger.info(f"Регистрация пользователя: {email}")

        if not validate_email_format(email):
            logger.warning(f"Неверный формат email: {email}")
            return False, "Неверный формат email.", None

        valid_password, error_msg = validate_password_strength(password)
        if not valid_password:
            logger.warning(f"Слабый пароль для пользователя {email}: {error_msg}")
            return False, error_msg, None

        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            logger.warning(f"Попытка повторной регистрации: {email}")
            return False, f"Email {email} уже зарегистрирован.", None

        user = User.create(
            email=email,
            password=password,
            full_name=full_name,
            is_admin=is_admin,
        )

        created_user = await self.user_repository.create(user)
        logger.success(f"Пользователь успешно зарегистрирован: {email}")
        return True, "Пользователь успешно зарегистрирован.", created_user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Аутентификация пользователя по email и паролю.

        :param email: Электронная почта пользователя
        :param password: Пароль в открытом виде
        :return: Пользователь, если аутентификация успешна, иначе None
        """
        logger.info(f"Аутентификация пользователя: {email}")
        user = await self.user_repository.get_by_email(email)
        if not user:
            logger.warning(f"Пользователь не найден: {email}")
            return None

        if not user.verify_password(password):
            logger.warning(f"Неверный пароль для пользователя: {email}")
            return None

        logger.success(f"Аутентификация успешна: {email}")
        return user

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Получение пользователя по ID.

        :param user_id: Идентификатор пользователя
        :return: Пользователь или None, если не найден
        """
        logger.info(f"Получение пользователя по ID: {user_id}")
        return await self.user_repository.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Получение пользователя по email.

        :param email: Электронная почта пользователя
        :return: Пользователь или None, если не найден
        """
        logger.info(f"Получение пользователя по email: {email}")
        return await self.user_repository.get_by_email(email)

    async def update_user(
        self, user_id: UUID, full_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Обновление информации о пользователе.

        :param user_id: Идентификатор пользователя
        :param full_name: Новое полное имя (если есть)
        :return: Кортеж (успех, сообщение, обновлённый пользователь)
        """
        logger.info(f"Обновление пользователя ID: {user_id}")
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Пользователь не найден при обновлении: {user_id}")
            return False, f"Пользователь с ID {user_id} не найден.", None

        if full_name is not None:
            user = User(
                id=user.id,
                email=user.email,
                hashed_password=user.hashed_password,
                full_name=full_name,
                is_active=user.is_active,
                is_admin=user.is_admin,
                balance=user.balance,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

        try:
            updated_user = await self.user_repository.update(user)
            logger.success(f"Пользователь успешно обновлён: {user_id}")
            return True, "Пользователь успешно обновлён.", updated_user
        except Exception as e:
            logger.exception(f"Ошибка при обновлении пользователя {user_id}: {str(e)}")
            return False, f"Не удалось обновить пользователя: {str(e)}", None

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> Tuple[bool, str]:
        """
        Смена пароля пользователя с валидацией.

        :param user_id: Идентификатор пользователя
        :param current_password: Текущий пароль
        :param new_password: Новый пароль
        :return: Кортеж (успех, сообщение)
        """
        logger.info(f"Попытка смены пароля для пользователя: {user_id}")
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Пользователь не найден при смене пароля: {user_id}")
            return False, f"Пользователь с ID {user_id} не найден."

        if not user.verify_password(current_password):
            logger.warning(f"Неверный текущий пароль для пользователя: {user.email}")
            return False, "Неверный текущий пароль."

        valid_password, error_msg = validate_password_strength(new_password)
        if not valid_password:
            logger.warning(f"Слабый новый пароль для пользователя: {user.email}")
            return False, error_msg

        hashed_password = pwd_context.hash(new_password)

        updated_user = User(
            id=user.id,
            email=user.email,
            hashed_password=hashed_password,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            balance=user.balance,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        try:
            await self.user_repository.update(updated_user)
            logger.success(f"Пароль успешно изменён для пользователя: {user.email}")
            return True, "Пароль успешно обновлён."
        except Exception as e:
            logger.exception(
                f"Ошибка при смене пароля для пользователя {user.email}: {str(e)}"
            )
            return False, f"Не удалось обновить пароль: {str(e)}"


async def get_user_repository(session=Depends(get_db)) -> UserRepository:
    """
    Зависимость для получения экземпляра UserRepository.

    :param session: Сессия БД
    :return: Репозиторий пользователей
    """
    return SQLAlchemyUserRepository(session)


def get_user_use_case(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserUseCase:
    """
    Зависимость для получения экземпляра UserUseCase.

    :param user_repo: Репозиторий пользователей
    :return: Экземпляр бизнес-логики пользователя
    """
    return UserUseCase(user_repo)
