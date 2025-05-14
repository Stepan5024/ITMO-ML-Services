# src/ml_classifier/services/user_use_cases.py
"""Бизнес-логика и варианты использования, связанные с пользователями."""

from typing import Optional, Tuple
from uuid import UUID

from fastapi import Depends
from passlib.context import CryptContext
from loguru import logger
import time
from uuid import uuid4

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
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(
            f"[{operation_id}] Начало регистрации пользователя: {email} | Имя:"
            f" {full_name or 'Не указано'} | Админ: {is_admin}"
        )

        if not validate_email_format(email):
            logger.warning(
                f"[{operation_id}] Валидация не пройдена: неверный формат email: {email}"
            )
            return False, "Неверный формат email.", None

        valid_password, error_msg = validate_password_strength(password)
        if not valid_password:
            logger.warning(
                f"[{operation_id}] Валидация не пройдена: слабый пароль для пользователя {email}: {error_msg}"
            )
            return False, error_msg, None

        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            logger.warning(
                f"[{operation_id}] Валидация не пройдена: пользователь с email"
                f" {email} уже существует (ID: {existing_user.id})"
            )
            return False, f"Email {email} уже зарегистрирован.", None

        user = User.create(
            email=email,
            password=password,
            full_name=full_name,
            is_admin=is_admin,
        )

        logger.debug(
            f"[{operation_id}] Создание объекта пользователя: {email} | ID: {user.id}"
        )
        try:
            created_user = await self.user_repository.create(user)
            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Пользователь успешно зарегистрирован: {email} | ID: {created_user.id} "
                f"| Время выполнения: {execution_time:.3f}с"
            )
            return True, "Пользователь успешно зарегистрирован.", created_user
        except Exception as e:
            logger.error(
                f"[{operation_id}] Ошибка при создании пользователя {email}: {str(e)}"
            )
            return False, f"Ошибка при регистрации пользователя: {str(e)}", None

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Аутентификация пользователя по email и паролю.

        :param email: Электронная почта пользователя
        :param password: Пароль в открытом виде
        :return: Пользователь, если аутентификация успешна, иначе None
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(f"[{operation_id}] Попытка аутентификации пользователя: {email}")

        try:
            user = await self.user_repository.get_by_email(email)

            if not user:
                logger.warning(
                    f"[{operation_id}] Аутентификация не удалась: пользователь не найден: {email}"
                )
                return None

            logger.debug(
                f"[{operation_id}] Пользователь найден: {email} | ID: {user.id} | Активен: {user.is_active} "
                f"| Админ: {user.is_admin}"
            )

            if not user.verify_password(password):
                logger.warning(
                    f"[{operation_id}] Аутентификация не удалась: неверный пароль для пользователя: "
                    f"{email} | ID: {user.id}"
                )
                return None

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Аутентификация успешна: {email} | ID: {user.id} | Время выполнения: "
                f"{execution_time:.3f}с"
            )
            return user

        except Exception as e:
            logger.error(
                f"[{operation_id}] Ошибка при аутентификации пользователя {email}: {str(e)}"
            )
            return None

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Получение пользователя по ID.

        :param user_id: Идентификатор пользователя
        :return: Пользователь или None, если не найден
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(f"[{operation_id}] Запрос пользователя по ID: {user_id}")

        try:
            user = await self.user_repository.get_by_id(user_id)
            execution_time = time.time() - start_time

            if user:
                logger.debug(
                    f"[{operation_id}] Пользователь найден: ID {user_id} | Email: {user.email} | Активен: "
                    f"{user.is_active} | Время выполнения: {execution_time:.3f}с"
                )
            else:
                logger.warning(
                    f"[{operation_id}] Пользователь не найден: ID {user_id} | Время выполнения: {execution_time:.3f}с"
                )

            return user
        except Exception as e:
            logger.error(
                f"[{operation_id}] Ошибка при получении пользователя по ID {user_id}: {str(e)}"
            )
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Получение пользователя по email.

        :param email: Электронная почта пользователя
        :return: Пользователь или None, если не найден
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(f"[{operation_id}] Запрос пользователя по email: {email}")

        try:
            user = await self.user_repository.get_by_email(email)
            execution_time = time.time() - start_time

            if user:
                logger.debug(
                    f"[{operation_id}] Пользователь найден: Email {email} | ID: {user.id} | Активен:"
                    f" {user.is_active} | Время выполнения: {execution_time:.3f}с"
                )
            else:
                logger.warning(
                    f"[{operation_id}] Пользователь не найден: Email {email} | Время выполнения: {execution_time:.3f}с"
                )

            return user
        except Exception as e:
            logger.error(
                f"[{operation_id}] Ошибка при получении пользователя по email {email}: {str(e)}"
            )
            return None

    async def update_user(
        self, user_id: UUID, full_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Обновление информации о пользователе.

        :param user_id: Идентификатор пользователя
        :param full_name: Новое полное имя (если есть)
        :return: Кортеж (успех, сообщение, обновлённый пользователь)
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(
            f"[{operation_id}] Запрос на обновление пользователя ID: {user_id} | Новое имя: {full_name}"
        )

        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(
                f"[{operation_id}] Обновление не выполнено: пользователь не найден: {user_id}"
            )
            return False, f"Пользователь с ID {user_id} не найден.", None

        logger.debug(
            f"[{operation_id}] Текущие данные пользователя: ID: {user.id} | Email: {user.email} | Имя: "
            f"{user.full_name} | Активен: {user.is_active} | Админ: {user.is_admin}"
        )

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
            logger.debug(
                f"[{operation_id}] Подготовлено обновление имени пользователя: {user.full_name} -> {full_name}"
            )

        try:
            updated_user = await self.user_repository.update(user)
            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Пользователь успешно обновлён: ID: {user_id} | Email: {user.email} | Новое имя: "
                f"{updated_user.full_name} | Время выполнения: {execution_time:.3f}с"
            )
            return True, "Пользователь успешно обновлён.", updated_user
        except Exception as e:
            logger.exception(
                f"[{operation_id}] Ошибка при обновлении пользователя {user_id}: {str(e)}"
            )
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
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(
            f"[{operation_id}] Запрос на смену пароля для пользователя: {user_id}"
        )

        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(
                f"[{operation_id}] Смена пароля не выполнена: пользователь не найден: {user_id}"
            )
            return False, f"Пользователь с ID {user_id} не найден."

        logger.debug(
            f"[{operation_id}] Пользователь найден: ID: {user.id} | Email: {user.email}"
        )

        if not user.verify_password(current_password):
            logger.warning(
                f"[{operation_id}] Смена пароля не выполнена: неверный текущий пароль для пользователя: "
                f"{user.email} | ID: {user.id}"
            )
            return False, "Неверный текущий пароль."

        valid_password, error_msg = validate_password_strength(new_password)
        if not valid_password:
            logger.warning(
                f"[{operation_id}] Смена пароля не выполнена: слабый новый пароль для пользователя: "
                f"{user.email} | ID: {user.id} | Причина: {error_msg}"
            )
            return False, error_msg

        logger.debug(
            f"[{operation_id}] Валидация нового пароля пройдена, хеширование пароля для пользователя: {user.email}"
        )
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
            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Пароль успешно изменён для пользователя: "
                f"{user.email} | ID: {user.id} | Время выполнения: {execution_time:.3f}с"
            )
            return True, "Пароль успешно обновлён."
        except Exception as e:
            logger.exception(
                f"[{operation_id}] Ошибка при смене пароля для пользователя {user.email} | ID: {user.id}: {str(e)}"
            )
            return False, f"Не удалось обновить пароль: {str(e)}"


async def get_user_repository(session=Depends(get_db)) -> UserRepository:
    """
    Зависимость для получения экземпляра UserRepository.

    :param session: Сессия БД
    :return: Репозиторий пользователей
    """
    logger.debug("Создание экземпляра SQLAlchemyUserRepository")
    return SQLAlchemyUserRepository(session)


def get_user_use_case(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserUseCase:
    """
    Зависимость для получения экземпляра UserUseCase.

    :param user_repo: Репозиторий пользователей
    :return: Экземпляр бизнес-логики пользователя
    """
    logger.debug("Создание экземпляра UserUseCase с репозиторием пользователей")
    return UserUseCase(user_repo)
