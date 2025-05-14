"""Сценарии использования биллинговой системы."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import time

from loguru import logger

from ml_classifier.domain.entities.enums import TransactionStatus, TransactionType
from ml_classifier.domain.entities.transaction import Transaction
from ml_classifier.domain.repositories.transaction_repository import (
    TransactionRepository,
)
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.services.pricing_service import PricingService


class InsufficientBalanceError(Exception):
    """Ошибка при недостаточном балансе пользователя."""

    pass


class TransactionError(Exception):
    """Ошибка при обработке транзакции."""

    pass


class BillingUseCase:
    """Бизнес-логика операций с биллингом."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        user_repository: UserRepository,
        pricing_service: PricingService,
    ):
        """Инициализация класса с необходимыми репозиториями и сервисами."""
        self.transaction_repository = transaction_repository
        self.user_repository = user_repository
        self.pricing_service = pricing_service

    async def get_balance(self, user_id: UUID) -> Decimal:
        """
        Получить текущий баланс пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Текущий баланс пользователя

        Raises:
            ValueError: Если пользователь не найден
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(f"[{operation_id}] Запрос баланса для пользователя: {user_id}")

        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                logger.error(f"[{operation_id}] Пользователь {user_id} не найден")
                raise ValueError(f"User with ID {user_id} not found")

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Баланс пользователя получен: user_id={user_id}, email={user.email},"
                f" balance={float(user.balance)} | Время выполнения: {execution_time:.3f}с"
            )
            return user.balance
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при получении баланса пользователя {user_id}: {str(e)}"
                f" | Время выполнения: {execution_time:.3f}с"
            )
            raise

    async def deposit(
        self, user_id: UUID, amount: Decimal, description: str = "Пополнение"
    ) -> Tuple[Transaction, Decimal]:
        """
        Пополнить баланс пользователя.

        Args:
            user_id: Идентификатор пользователя
            amount: Сумма пополнения (должна быть положительной)
            description: Описание транзакции

        Returns:
            Созданная транзакция и обновлённый баланс

        Raises:
            ValueError: Если сумма отрицательная или пользователь не найден
            TransactionError: Ошибка при обработке транзакции
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(
            f"[{operation_id}] Запрос на пополнение баланса: user_id={user_id}, сумма={float(amount)},"
            f" описание='{description}'"
        )

        if amount <= 0:
            logger.error(
                f"[{operation_id}] Ошибка валидации: сумма пополнения должна быть положительной: {float(amount)}"
            )
            raise ValueError("Deposit amount must be positive")

        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                logger.error(
                    f"[{operation_id}] Ошибка валидации: пользователь {user_id} не найден"
                )
                raise ValueError(f"User with ID {user_id} not found")

            logger.debug(
                f"[{operation_id}] Данные пользователя: ID={user_id}, email={user.email},"
                f" текущий баланс={float(user.balance)}"
            )

            # Создание транзакции пополнения
            logger.debug(
                f"[{operation_id}] Создание транзакции пополнения баланса: {float(amount)}"
            )
            transaction = await self.transaction_repository.create_deposit_transaction(
                user_id, amount, description
            )
            logger.debug(
                f"[{operation_id}] Транзакция создана: ID={transaction.id}, статус={transaction.status.value}"
            )

            # Обновление баланса пользователя
            logger.debug(
                f"[{operation_id}] Обновление баланса пользователя: {float(user.balance)} +"
                f" {float(amount)} = {float(user.balance + amount)}"
            )
            updated_user = await self.user_repository.update_balance(user_id, amount)

            # Завершение транзакции
            completed_transaction = transaction.complete()
            await self.transaction_repository.update(completed_transaction)

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Пополнение завершено: transaction_id={completed_transaction.id},"
                f" user_id={user_id}, amount={float(amount)}, новый баланс={float(updated_user.balance)}"
                f" | Время выполнения: {execution_time:.3f}с"
            )
            return completed_transaction, updated_user.balance

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(
                f"[{operation_id}] Ошибка при пополнении баланса пользователя {user_id} на сумму"
                f" {float(amount)}: {str(e)} | Время выполнения: {execution_time:.3f}с"
            )
            raise TransactionError(f"Error processing deposit: {str(e)}")

    async def withdraw(
        self, user_id: UUID, amount: Decimal, description: str = "Списание"
    ) -> Tuple[Transaction, Decimal]:
        """
        Списать средства с баланса пользователя.

        Args:
            user_id: Идентификатор пользователя
            amount: Сумма списания (должна быть положительной)
            description: Описание транзакции

        Returns:
            Созданная транзакция и обновлённый баланс

        Raises:
            ValueError: Если сумма отрицательная или пользователь не найден
            InsufficientBalanceError: Недостаточно средств
            TransactionError: Ошибка при обработке транзакции
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(
            f"[{operation_id}] Запрос на списание средств: user_id={user_id}, сумма={float(amount)},"
            f" описание='{description}'"
        )

        if amount <= 0:
            logger.error(
                f"[{operation_id}] Ошибка валидации: сумма списания должна быть положительной: {float(amount)}"
            )
            raise ValueError("Withdrawal amount must be positive")

        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                logger.error(
                    f"[{operation_id}] Ошибка валидации: пользователь {user_id} не найден"
                )
                raise ValueError(f"User with ID {user_id} not found")

            logger.debug(
                f"[{operation_id}] Данные пользователя: ID={user_id}, email={user.email},"
                f" текущий баланс={float(user.balance)}"
            )

            if user.balance < amount:
                logger.warning(
                    f"[{operation_id}] Недостаточно средств у пользователя {user_id}:"
                    f" баланс={float(user.balance)}, требуется={float(amount)}"
                )
                raise InsufficientBalanceError(
                    f"Insufficient balance: {float(user.balance)} < {float(amount)}"
                )

            # Создание транзакции списания
            transaction_id = uuid4()
            logger.debug(
                f"[{operation_id}] Создание транзакции списания: ID={transaction_id}, сумма={float(-amount)}"
            )
            transaction = Transaction(
                id=transaction_id,
                user_id=user_id,
                amount=-amount,
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.PENDING,
                description=description,
                created_at=datetime.utcnow(),
            )

            created_transaction = await self.transaction_repository.create(transaction)
            logger.debug(
                f"[{operation_id}] Транзакция создана: ID={created_transaction.id},"
                f" статус={created_transaction.status.value}"
            )

            # Обновление баланса пользователя
            logger.debug(
                f"[{operation_id}] Обновление баланса пользователя: {float(user.balance)} -"
                f" {float(amount)} = {float(user.balance - amount)}"
            )
            updated_user = await self.user_repository.update_balance(user_id, -amount)

            # Завершение транзакции
            completed_transaction = created_transaction.complete()
            await self.transaction_repository.update(completed_transaction)

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Списание завершено: transaction_id={completed_transaction.id},"
                f" user_id={user_id}, amount={float(amount)}, новый баланс={float(updated_user.balance)}"
                f" | Время выполнения: {execution_time:.3f}с"
            )
            return completed_transaction, updated_user.balance

        except InsufficientBalanceError:
            # Пробрасываем ошибку недостаточного баланса выше
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(
                f"[{operation_id}] Ошибка при списании средств у пользователя {user_id} на сумму {float(amount)}:"
                f" {str(e)} | Время выполнения: {execution_time:.3f}с"
            )
            raise TransactionError(f"Error processing withdrawal: {str(e)}")

    async def charge_for_prediction(
        self, user_id: UUID, amount: Decimal, task_id: UUID
    ) -> Tuple[Transaction, Decimal]:
        """
        Списать средства за выполнение ML-задачи (предсказания).

        Args:
            user_id: Идентификатор пользователя
            amount: Сумма списания
            task_id: Идентификатор задачи

        Returns:
            Транзакция и обновлённый баланс

        Raises:
            ValueError: Если сумма некорректна
            InsufficientBalanceError: Недостаточно средств
            TransactionError: Ошибка при списании
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(
            f"[{operation_id}] Запрос на списание за предсказание: user_id={user_id}, task_id={task_id}, "
            f"сумма={float(amount)}"
        )

        if amount <= 0:
            logger.error(
                f"[{operation_id}] Ошибка валидации: сумма списания должна быть положительной: {float(amount)}"
            )
            raise ValueError("Charge amount must be positive")

        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                logger.error(
                    f"[{operation_id}] Ошибка валидации: пользователь {user_id} не найден"
                )
                raise ValueError(f"User with ID {user_id} not found")

            logger.debug(
                f"[{operation_id}] Данные пользователя: ID={user_id}, email={user.email},"
                f" текущий баланс={float(user.balance)}"
            )

            if user.balance < amount:
                logger.warning(
                    f"[{operation_id}] Недостаточно средств у пользователя {user_id}:"
                    f" баланс={float(user.balance)}, требуется={float(amount)}"
                )
                raise InsufficientBalanceError(
                    f"Insufficient balance: {float(user.balance)} < {float(amount)}"
                )

            # Создание транзакции за предсказание
            logger.debug(
                f"[{operation_id}] Создание транзакции списания за предсказание:"
                f" user_id={user_id}, task_id={task_id}, сумма={float(amount)}"
            )
            transaction = await self.transaction_repository.create_charge_transaction(
                user_id=user_id, amount=amount, task_id=task_id
            )
            logger.debug(
                f"[{operation_id}] Транзакция создана: ID={transaction.id}, статус={transaction.status.value}"
            )

            # Обновление баланса пользователя
            logger.debug(
                f"[{operation_id}] Обновление баланса пользователя: {float(user.balance)} -"
                f" {float(amount)} = {float(user.balance - amount)}"
            )
            updated_user = await self.user_repository.update_balance(user_id, -amount)

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Списание за предсказание завершено: transaction_id={transaction.id},"
                f" user_id={user_id}, task_id={task_id}, amount={float(amount)},"
                f" новый баланс={float(updated_user.balance)} | Время выполнения: {execution_time:.3f}с"
            )
            return transaction, updated_user.balance

        except InsufficientBalanceError:
            # Пробрасываем ошибку недостаточного баланса выше
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(
                f"[{operation_id}] Ошибка при списании за предсказание: user_id={user_id},"
                f" task_id={task_id}, сумма={float(amount)}: {str(e)} | Время выполнения: {execution_time:.3f}с"
            )
            raise TransactionError(f"Error processing charge: {str(e)}")

    async def refund(
        self, transaction_id: UUID, reason: str = "Возврат"
    ) -> Tuple[Transaction, Decimal]:
        """
        Выполнить возврат по ранее проведённой транзакции.

        Args:
            transaction_id: ID оригинальной транзакции
            reason: Причина возврата

        Returns:
            Транзакция возврата и обновлённый баланс

        Raises:
            ValueError: Если транзакция не найдена или неподходящего типа
            TransactionError: Ошибка при возврате
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(
            f"[{operation_id}] Запрос на возврат средств по транзакции {transaction_id}, причина: '{reason}'"
        )

        try:
            # Получение оригинальной транзакции
            original_transaction = await self.transaction_repository.get_by_id(
                transaction_id
            )
            if not original_transaction:
                logger.error(
                    f"[{operation_id}] Ошибка валидации: транзакция с ID {transaction_id} не найдена"
                )
                raise ValueError(f"Transaction with ID {transaction_id} not found")

            logger.debug(
                f"[{operation_id}] Найдена транзакция: ID={transaction_id},"
                f" тип={original_transaction.type.value}, статус={original_transaction.status.value},"
                f" сумма={float(original_transaction.amount)}, user_id={original_transaction.user_id}"
            )

            # Проверка типа транзакции
            if original_transaction.type != TransactionType.CHARGE:
                logger.error(
                    f"[{operation_id}] Ошибка валидации: возврат возможен только для транзакций списания,"
                    f" текущий тип: {original_transaction.type.value}"
                )
                raise ValueError("Only charge transactions can be refunded")

            # Проверка статуса транзакции
            if not original_transaction.is_completed():
                logger.error(
                    f"[{operation_id}] Ошибка валидации: возврат возможен только для завершенных транзакций,"
                    f" текущий статус: {original_transaction.status.value}"
                )
                raise ValueError("Only completed transactions can be refunded")

            user_id = original_transaction.user_id
            refund_amount = abs(original_transaction.amount)
            logger.debug(
                f"[{operation_id}] Подготовка возврата пользователю {user_id}, сумма возврата: {float(refund_amount)}"
            )

            # Получение текущего баланса пользователя
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                logger.error(
                    f"[{operation_id}] Ошибка: пользователь {user_id} не найден"
                )
                raise ValueError(f"User with ID {user_id} not found")

            logger.debug(
                f"[{operation_id}] Данные пользователя: ID={user_id}, email={user.email},"
                f" текущий баланс={float(user.balance)}"
            )

            # Создание транзакции возврата
            refund_transaction_id = uuid4()
            refund_transaction = Transaction(
                id=refund_transaction_id,
                user_id=user_id,
                amount=refund_amount,
                type=TransactionType.REFUND,
                status=TransactionStatus.PENDING,
                reference_id=original_transaction.id,
                description=f"Возврат за транзакцию {transaction_id}: {reason}",
                created_at=datetime.utcnow(),
            )
            logger.debug(
                f"[{operation_id}] Создание транзакции возврата: ID={refund_transaction_id}"
            )

            created_transaction = await self.transaction_repository.create(
                refund_transaction
            )
            logger.debug(
                f"[{operation_id}] Транзакция возврата создана: ID={created_transaction.id},"
                f" статус={created_transaction.status.value}"
            )

            # Обновление баланса пользователя
            logger.debug(
                f"[{operation_id}] Обновление баланса пользователя: {float(user.balance)} +"
                f" {float(refund_amount)} = {float(user.balance + refund_amount)}"
            )
            updated_user = await self.user_repository.update_balance(
                user_id, refund_amount
            )

            # Завершение транзакции возврата
            completed_transaction = created_transaction.complete()
            await self.transaction_repository.update(completed_transaction)

            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Возврат средств завершен: refund_id={completed_transaction.id},"
                f" original_id={transaction_id}, user_id={user_id}, amount={float(refund_amount)}, "
                f"новый баланс={float(updated_user.balance)} | Время выполнения: {execution_time:.3f}с"
            )
            return completed_transaction, updated_user.balance

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(
                f"[{operation_id}] Ошибка при возврате средств по транзакции {transaction_id}: {str(e)}"
                f" | Время выполнения: {execution_time:.3f}с"
            )
            raise TransactionError(f"Error processing refund: {str(e)}")

    async def get_transactions(
        self,
        user_id: UUID,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        limit: int = 10,
    ) -> List[Transaction]:
        """
        Получить историю транзакций пользователя с фильтрацией.

        Args:
            user_id: Идентификатор пользователя
            transaction_type: Тип транзакции (необязательно)
            status: Статус транзакции (необязательно)
            limit: Количество транзакций (по умолчанию 10)

        Returns:
            Список транзакций
        """
        logger.info(f"Получение транзакций для пользователя {user_id}, limit={limit}")
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            raise ValueError(f"User with ID {user_id} not found")

        return await self.transaction_repository.get_user_balance_history(
            user_id, limit
        )

    async def calculate_cost(
        self, model_id: UUID, input_data: Dict, batch_size: int = 1
    ) -> Dict:
        """
        Рассчитать стоимость предсказания без его выполнения.

        Args:
            model_id: Идентификатор модели
            input_data: Данные для предсказания
            batch_size: Размер батча (по умолчанию 1)

        Returns:
            Словарь с деталями стоимости (базовая цена, скидки и т.д.)
        """
        logger.info(
            f"Расчёт стоимости предсказания: модель {model_id}, batch_size={batch_size}"
        )
        return await self.pricing_service.calculate_prediction_cost(
            model_id, input_data, batch_size
        )
