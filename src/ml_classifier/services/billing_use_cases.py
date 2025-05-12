"""Billing system use cases."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from ml_classifier.domain.entities.enums import TransactionStatus, TransactionType
from ml_classifier.domain.entities.transaction import Transaction
from ml_classifier.domain.repositories.transaction_repository import (
    TransactionRepository,
)
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.services.pricing_service import PricingService


class InsufficientBalanceError(Exception):
    """Raised when user has insufficient balance for an operation."""

    pass


class TransactionError(Exception):
    """Raised when there's an error processing a transaction."""

    pass


class BillingUseCase:
    """Business logic for billing operations."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        user_repository: UserRepository,
        pricing_service: PricingService,
    ):
        """Initialize with required repositories and services."""
        self.transaction_repository = transaction_repository
        self.user_repository = user_repository
        self.pricing_service = pricing_service

    async def get_balance(self, user_id: UUID) -> Decimal:
        """
        Get current balance for a user.

        Args:
            user_id: User ID

        Returns:
            Decimal: Current balance

        Raises:
            ValueError: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        return user.balance

    async def deposit(
        self, user_id: UUID, amount: Decimal, description: str = "Deposit"
    ) -> Tuple[Transaction, Decimal]:
        """
        Add funds to user's balance.

        Args:
            user_id: User ID
            amount: Amount to deposit (must be positive)
            description: Transaction description

        Returns:
            Tuple[Transaction, Decimal]: Created transaction and updated balance

        Raises:
            ValueError: If amount is not positive or user not found
            TransactionError: On transaction processing error
        """
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        try:
            # Create deposit transaction
            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.PENDING,
                description=description,
                created_at=datetime.utcnow(),
            )

            # Create and save transaction
            transaction = await self.transaction_repository.create_deposit_transaction(
                user_id, amount, description
            )

            # Update user balance
            updated_user = await self.user_repository.update_balance(user_id, amount)

            # Mark transaction as completed
            completed_transaction = transaction.complete()
            await self.transaction_repository.update(completed_transaction)

            return completed_transaction, updated_user.balance

        except Exception as e:
            raise TransactionError(f"Error processing deposit: {str(e)}")

    async def withdraw(
        self, user_id: UUID, amount: Decimal, description: str = "Withdrawal"
    ) -> Tuple[Transaction, Decimal]:
        """
        Withdraw funds from user's balance.

        Args:
            user_id: User ID
            amount: Amount to withdraw (must be positive)
            description: Transaction description

        Returns:
            Tuple[Transaction, Decimal]: Created transaction and updated balance

        Raises:
            ValueError: If amount is not positive or user not found
            InsufficientBalanceError: If user has insufficient balance
            TransactionError: On transaction processing error
        """
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        if user.balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance: {float(user.balance)} < {float(amount)}"
            )

        try:
            # Create withdrawal transaction with negative amount
            transaction = Transaction(
                id=uuid4(),
                user_id=user_id,
                amount=-amount,  # Negative for withdrawal
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.PENDING,
                description=description,
                created_at=datetime.utcnow(),
            )

            # Create and save transaction
            created_transaction = await self.transaction_repository.create(transaction)

            # Update user balance
            updated_user = await self.user_repository.update_balance(user_id, -amount)

            # Mark transaction as completed
            completed_transaction = created_transaction.complete()
            await self.transaction_repository.update(completed_transaction)

            return completed_transaction, updated_user.balance

        except Exception as e:
            raise TransactionError(f"Error processing withdrawal: {str(e)}")

    async def charge_for_prediction(
        self, user_id: UUID, amount: Decimal, task_id: UUID
    ) -> Tuple[Transaction, Decimal]:
        """
        Charge user for prediction service.

        Args:
            user_id: User ID
            amount: Amount to charge (must be positive)
            task_id: Related prediction task ID

        Returns:
            Tuple[Transaction, Decimal]: Created transaction and updated balance

        Raises:
            ValueError: If amount is not positive or user not found
            InsufficientBalanceError: If user has insufficient balance
            TransactionError: On transaction processing error
        """
        if amount <= 0:
            raise ValueError("Charge amount must be positive")

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        if user.balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance: {float(user.balance)} < {float(amount)}"
            )

        try:
            # Create charge transaction
            transaction = await self.transaction_repository.create_charge_transaction(
                user_id=user_id, amount=amount, task_id=task_id
            )

            # Update user balance
            updated_user = await self.user_repository.update_balance(user_id, -amount)

            return transaction, updated_user.balance

        except Exception as e:
            raise TransactionError(f"Error processing charge: {str(e)}")

    async def refund(
        self, transaction_id: UUID, reason: str = "Refund"
    ) -> Tuple[Transaction, Decimal]:
        """
        Refund a previous charge transaction.

        Args:
            transaction_id: Original transaction ID to refund
            reason: Refund reason

        Returns:
            Tuple[Transaction, Decimal]: Created refund transaction and updated balance

        Raises:
            ValueError: If original transaction not found or not eligible for refund
            TransactionError: On refund processing error
        """
        # Get original transaction
        original_transaction = await self.transaction_repository.get_by_id(
            transaction_id
        )
        if not original_transaction:
            raise ValueError(f"Transaction with ID {transaction_id} not found")

        if original_transaction.type != TransactionType.CHARGE:
            raise ValueError("Only charge transactions can be refunded")

        if not original_transaction.is_completed():
            raise ValueError("Only completed transactions can be refunded")

        user_id = original_transaction.user_id
        refund_amount = abs(original_transaction.amount)  # Make positive for refund

        try:
            # Create refund transaction
            refund_transaction = Transaction(
                id=uuid4(),
                user_id=user_id,
                amount=refund_amount,  # Positive amount for refund
                type=TransactionType.REFUND,
                status=TransactionStatus.PENDING,
                reference_id=original_transaction.id,
                description=f"Refund for transaction {transaction_id}: {reason}",
                created_at=datetime.utcnow(),
            )

            # Create and save transaction
            created_transaction = await self.transaction_repository.create(
                refund_transaction
            )

            # Update user balance
            updated_user = await self.user_repository.update_balance(
                user_id, refund_amount
            )

            # Mark refund transaction as completed
            completed_transaction = created_transaction.complete()
            await self.transaction_repository.update(completed_transaction)

            return completed_transaction, updated_user.balance

        except Exception as e:
            raise TransactionError(f"Error processing refund: {str(e)}")

    async def get_transactions(
        self,
        user_id: UUID,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        limit: int = 10,
    ) -> List[Transaction]:
        """
        Get user's transaction history with filtering.

        Args:
            user_id: User ID
            transaction_type: Filter by transaction type
            status: Filter by transaction status
            limit: Maximum number of transactions to return

        Returns:
            List[Transaction]: List of matching transactions
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        return await self.transaction_repository.get_user_balance_history(
            user_id, limit
        )

    async def calculate_cost(
        self, model_id: UUID, input_data: Dict, batch_size: int = 1
    ) -> Dict:
        """
        Calculate cost for a prediction without executing it.

        Args:
            model_id: Model ID
            input_data: Input data for prediction
            batch_size: Number of items in batch (for batch prediction)

        Returns:
            Dict: Cost details including base cost, discounts, etc.
        """
        return await self.pricing_service.calculate_prediction_cost(
            model_id, input_data, batch_size
        )
