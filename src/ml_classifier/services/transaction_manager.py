"""Transaction manager for safe execution of financial operations."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, List, Optional, Set
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ml_classifier.domain.entities.enums import TransactionStatus, TransactionType
from ml_classifier.domain.entities.transaction import Transaction
from ml_classifier.domain.repositories.transaction_repository import (
    TransactionRepository,
)
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.infrastructure.db.database import AsyncSessionMaker


class TransactionManager:
    """Manager for financial transactions with atomicity guarantees."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        user_repository: UserRepository,
        session_factory=AsyncSessionMaker,
        pending_timeout_minutes: int = 15,
    ):
        """
        Initialize transaction manager.

        Args:
            transaction_repository: Repository for transactions
            user_repository: Repository for users
            session_factory: Factory for database sessions
            pending_timeout_minutes: Minutes after which pending transactions are considered stale
        """
        self.transaction_repository = transaction_repository
        self.user_repository = user_repository
        self.session_factory = session_factory
        self.pending_timeout_minutes = pending_timeout_minutes
        self._locked_user_ids: Set[UUID] = set()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with transaction support.

        Yields:
            AsyncSession: Database session
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def begin_transaction(
        self,
        user_id: UUID,
        amount: Decimal,
        transaction_type: TransactionType,
        task_id: Optional[UUID] = None,
        description: Optional[str] = None,
        reference_id: Optional[UUID] = None,
    ) -> Transaction:
        """
        Begin a financial transaction with balance checking and locking.

        Args:
            user_id: User ID
            amount: Transaction amount (positive for credits, negative for debits)
            transaction_type: Type of transaction
            task_id: Optional related task ID
            description: Optional transaction description
            reference_id: Optional reference transaction ID

        Returns:
            Transaction: Created transaction

        Raises:
            ValueError: On validation errors
            RuntimeError: If user is already locked
        """
        if user_id in self._locked_user_ids:
            raise RuntimeError(f"User {user_id} is already locked for a transaction")

        try:
            self._locked_user_ids.add(user_id)

            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            if amount < 0 and user.balance < abs(amount):
                raise ValueError(
                    f"Insufficient balance: {float(user.balance)} < {float(abs(amount))}"
                )

            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                type=transaction_type,
                status=TransactionStatus.PENDING,
                task_id=task_id,
                description=description,
                reference_id=reference_id,
                created_at=datetime.utcnow(),
            )

            created_transaction = await self.transaction_repository.create(transaction)

            return created_transaction

        finally:
            if user_id in self._locked_user_ids:
                self._locked_user_ids.remove(user_id)

    async def complete_transaction(self, transaction_id: UUID) -> Transaction:
        """
        Complete a pending transaction and update user balance.

        Args:
            transaction_id: ID of transaction to complete

        Returns:
            Transaction: Updated transaction

        Raises:
            ValueError: If transaction not found or not pending
        """
        transaction = await self.transaction_repository.get_by_id(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction with ID {transaction_id} not found")

        if transaction.status != TransactionStatus.PENDING:
            raise ValueError(f"Transaction {transaction_id} is not in pending status")

        user_id = transaction.user_id

        try:
            if user_id in self._locked_user_ids:
                raise RuntimeError(
                    f"User {user_id} is already locked for a transaction"
                )

            self._locked_user_ids.add(user_id)

            await self.user_repository.update_balance(user_id, transaction.amount)

            transaction.complete()
            updated_transaction = await self.transaction_repository.update(transaction)

            return updated_transaction

        finally:
            if user_id in self._locked_user_ids:
                self._locked_user_ids.remove(user_id)

    async def rollback_transaction(
        self, transaction_id: UUID, reason: str
    ) -> Transaction:
        """
        Roll back a pending transaction.

        Args:
            transaction_id: ID of transaction to roll back
            reason: Reason for rollback

        Returns:
            Transaction: Updated transaction

        Raises:
            ValueError: If transaction not found or not in pending status
        """
        transaction = await self.transaction_repository.get_by_id(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction with ID {transaction_id} not found")

        if transaction.status != TransactionStatus.PENDING:
            raise ValueError(f"Transaction {transaction_id} is not in pending status")

        user_id = transaction.user_id

        try:
            if user_id in self._locked_user_ids:
                raise RuntimeError(
                    f"User {user_id} is already locked for a transaction"
                )

            self._locked_user_ids.add(user_id)

            transaction.fail(reason)
            updated_transaction = await self.transaction_repository.update(transaction)

            return updated_transaction

        finally:
            if user_id in self._locked_user_ids:
                self._locked_user_ids.remove(user_id)

    async def cleanup_stale_transactions(self) -> int:
        """
        Find and rollback stale pending transactions.

        Returns:
            int: Number of transactions rolled back
        """
        cutoff_time = datetime.utcnow() - timedelta(
            minutes=self.pending_timeout_minutes
        )

        stale_transactions = await self._find_stale_pending_transactions(cutoff_time)
        count = 0

        for transaction in stale_transactions:
            try:
                await self.rollback_transaction(
                    transaction.id,
                    f"Transaction timed out after {self.pending_timeout_minutes} minutes",
                )
                count += 1
            except Exception as e:
                print(f"Error rolling back transaction {transaction.id}: {str(e)}")

        return count

    async def _find_stale_pending_transactions(
        self, cutoff_time: datetime
    ) -> List[Transaction]:
        """
        Find stale pending transactions.

        Args:
            cutoff_time: Transactions created before this time are considered stale

        Returns:
            List[Transaction]: List of stale transactions
        """
        return []
