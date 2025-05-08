"""Репозиторий для работы с финансовыми транзакциями."""
from abc import abstractmethod
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ml_classifier.domain.entities import TransactionStatus
from ml_classifier.domain.entities.transaction import Transaction
from ml_classifier.domain.repositories.base import Repository


class TransactionRepository(Repository[Transaction]):
    """Интерфейс репозитория для работы с транзакциями."""

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> List[Transaction]:
        """Получить все транзакции пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            List[Transaction]: Список транзакций пользователя
        """
        raise NotImplementedError

    @abstractmethod
    async def create_charge_transaction(
        self, user_id: UUID, amount: Decimal, task_id: UUID
    ) -> Transaction:
        """Создать транзакцию оплаты за использование модели.

        Args:
            user_id: Идентификатор пользователя
            amount: Сумма списания
            task_id: Идентификатор задачи

        Returns:
            Transaction: Созданная транзакция
        """
        raise NotImplementedError

    @abstractmethod
    async def create_deposit_transaction(
        self, user_id: UUID, amount: Decimal, description: Optional[str] = None
    ) -> Transaction:
        """Создать транзакцию пополнения баланса.

        Args:
            user_id: Идентификатор пользователя
            amount: Сумма пополнения
            description: Описание транзакции

        Returns:
            Transaction: Созданная транзакция
        """
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self, transaction_id: UUID, status: TransactionStatus
    ) -> Transaction:
        """Update transaction status.

        Args:
            transaction_id: Transaction ID
            status: New status

        Returns:
            Transaction: Updated transaction
        """
        raise NotImplementedError

    @abstractmethod
    async def get_user_balance_history(
        self, user_id: UUID, limit: int = 10
    ) -> List[Transaction]:
        """Get user's balance history.

        Args:
            user_id: User ID
            limit: Maximum number of transactions to return

        Returns:
            List[Transaction]: List of transactions
        """
        raise NotImplementedError
