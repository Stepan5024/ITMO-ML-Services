"""Сценарии использования биллинговой системы."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

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
        logger.info(f"Получение баланса для пользователя {user_id}")
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            raise ValueError(f"User with ID {user_id} not found")
        return user.balance

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
        logger.info(f"Пополнение баланса пользователя {user_id} на сумму {amount}")
        if amount <= 0:
            logger.error("Сумма пополнения должна быть положительной")
            raise ValueError("Deposit amount must be positive")

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            raise ValueError(f"User with ID {user_id} not found")

        try:
            transaction = await self.transaction_repository.create_deposit_transaction(
                user_id, amount, description
            )
            updated_user = await self.user_repository.update_balance(user_id, amount)
            completed_transaction = transaction.complete()
            await self.transaction_repository.update(completed_transaction)

            logger.success(f"Пополнение завершено: {completed_transaction}")
            return completed_transaction, updated_user.balance

        except Exception as e:
            logger.exception("Ошибка при пополнении баланса")
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
        logger.info(f"Списание средств у пользователя {user_id} на сумму {amount}")
        if amount <= 0:
            logger.error("Сумма списания должна быть положительной")
            raise ValueError("Withdrawal amount must be positive")

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            raise ValueError(f"User with ID {user_id} not found")

        if user.balance < amount:
            logger.warning(f"Недостаточно средств у пользователя {user_id}")
            raise InsufficientBalanceError(
                f"Insufficient balance: {float(user.balance)} < {float(amount)}"
            )

        try:
            transaction = Transaction(
                id=uuid4(),
                user_id=user_id,
                amount=-amount,
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.PENDING,
                description=description,
                created_at=datetime.utcnow(),
            )
            created_transaction = await self.transaction_repository.create(transaction)
            updated_user = await self.user_repository.update_balance(user_id, -amount)
            completed_transaction = created_transaction.complete()
            await self.transaction_repository.update(completed_transaction)

            logger.success(f"Списание завершено: {completed_transaction}")
            return completed_transaction, updated_user.balance

        except Exception as e:
            logger.exception("Ошибка при списании средств")
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
        logger.info(
            f"Списание за предсказание: пользователь {user_id}, задача {task_id}, сумма {amount}"
        )
        if amount <= 0:
            logger.error("Сумма списания должна быть положительной")
            raise ValueError("Charge amount must be positive")

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            raise ValueError(f"User with ID {user_id} not found")

        if user.balance < amount:
            logger.warning(f"Недостаточно средств у пользователя {user_id}")
            raise InsufficientBalanceError(
                f"Insufficient balance: {float(user.balance)} < {float(amount)}"
            )

        try:
            transaction = await self.transaction_repository.create_charge_transaction(
                user_id=user_id, amount=amount, task_id=task_id
            )
            updated_user = await self.user_repository.update_balance(user_id, -amount)

            logger.success(f"Списание за предсказание завершено: {transaction}")
            return transaction, updated_user.balance

        except Exception as e:
            logger.exception("Ошибка при списании за предсказание")
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
        logger.info(f"Инициирован возврат по транзакции {transaction_id}")
        original_transaction = await self.transaction_repository.get_by_id(
            transaction_id
        )
        if not original_transaction:
            logger.error("Оригинальная транзакция не найдена")
            raise ValueError(f"Transaction with ID {transaction_id} not found")

        if original_transaction.type != TransactionType.CHARGE:
            logger.error("Можно вернуть только списания")
            raise ValueError("Only charge transactions can be refunded")

        if not original_transaction.is_completed():
            logger.error("Можно вернуть только завершённые транзакции")
            raise ValueError("Only completed transactions can be refunded")

        user_id = original_transaction.user_id
        refund_amount = abs(original_transaction.amount)

        try:
            refund_transaction = Transaction(
                id=uuid4(),
                user_id=user_id,
                amount=refund_amount,
                type=TransactionType.REFUND,
                status=TransactionStatus.PENDING,
                reference_id=original_transaction.id,
                description=f"Возврат за транзакцию {transaction_id}: {reason}",
                created_at=datetime.utcnow(),
            )

            created_transaction = await self.transaction_repository.create(
                refund_transaction
            )
            updated_user = await self.user_repository.update_balance(
                user_id, refund_amount
            )
            completed_transaction = created_transaction.complete()
            await self.transaction_repository.update(completed_transaction)

            logger.success(f"Возврат завершён: {completed_transaction}")
            return completed_transaction, updated_user.balance

        except Exception as e:
            logger.exception("Ошибка при возврате средств")
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
