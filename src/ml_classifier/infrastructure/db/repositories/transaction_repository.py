# src/ml_classifier/infrastructure/db/repositories/transaction_repository.py
"""SQLAlchemy implementation of transaction repository."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ml_classifier.domain.entities.enums import TransactionStatus, TransactionType
from ml_classifier.domain.entities.transaction import Transaction
from ml_classifier.domain.repositories.transaction_repository import (
    TransactionRepository,
)
from ml_classifier.infrastructure.db.models import Transaction as TransactionModel
from ml_classifier.infrastructure.db.repositories.base import SQLAlchemyRepository


class SQLAlchemyTransactionRepository(
    SQLAlchemyRepository[Transaction, TransactionModel], TransactionRepository
):
    """SQLAlchemy implementation of transaction repository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Database session
        """
        super().__init__(session, TransactionModel)

    def _db_to_entity(self, db_tx: TransactionModel) -> Transaction:
        """Convert database model to domain entity."""
        return Transaction(
            id=db_tx.id,
            user_id=db_tx.user_id,
            amount=Decimal(str(db_tx.amount)),
            type=db_tx.type,
            reference_id=db_tx.reference_id,
            task_id=db_tx.reference_id,  # For compatibility
            status=db_tx.status,
            description=db_tx.description,
            created_at=db_tx.created_at,
            updated_at=db_tx.updated_at,
        )

    def _entity_to_db_values(self, entity: Transaction) -> Dict:
        """Convert domain entity to database values dictionary."""
        # For compatibility - use reference_id if task_id is provided
        reference_id = entity.reference_id or entity.task_id

        return {
            "id": entity.id,
            "user_id": entity.user_id,
            "amount": float(entity.amount),
            "type": entity.type,
            "reference_id": reference_id,
            "status": entity.status,
            "description": entity.description,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    async def get_by_id(self, entity_id: UUID) -> Optional[Transaction]:
        """Get transaction by ID."""
        result = await self.session.execute(
            select(TransactionModel).where(TransactionModel.id == entity_id)
        )
        db_tx = result.scalars().first()
        if not db_tx:
            return None
        return self._db_to_entity(db_tx)

    async def create(self, entity: Transaction) -> Transaction:
        """Create new transaction."""
        db_tx = TransactionModel(**self._entity_to_db_values(entity))
        self.session.add(db_tx)
        await self.session.commit()
        await self.session.refresh(db_tx)
        return self._db_to_entity(db_tx)

    async def update(self, entity: Transaction) -> Transaction:
        """Update transaction."""
        values = self._entity_to_db_values(entity)
        # We don't want to update id or created_at
        values.pop("id", None)
        values.pop("created_at", None)
        values["updated_at"] = datetime.utcnow()

        stmt = (
            update(TransactionModel.__table__)
            .where(TransactionModel.id == entity.id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.commit()

        updated = await self.get_by_id(entity.id)
        if not updated:
            raise ValueError(f"Transaction with ID {entity.id} not found after update")
        return updated

    async def delete(self, entity_id: UUID) -> bool:
        """Delete transaction."""
        stmt = delete(TransactionModel.__table__).where(
            TransactionModel.id == entity_id
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount > 0)

    async def get_by_user_id(self, user_id: UUID) -> List[Transaction]:
        """Get transactions by user ID."""
        result = await self.session.execute(
            select(TransactionModel).where(TransactionModel.user_id == user_id)
        )
        db_txs = result.scalars().all()
        return [self._db_to_entity(db_tx) for db_tx in db_txs]

    async def update_status(
        self, transaction_id: UUID, status: TransactionStatus
    ) -> Transaction:
        """Update transaction status."""
        stmt = (
            update(TransactionModel.__table__)
            .where(TransactionModel.id == transaction_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await self.session.execute(stmt)
        await self.session.commit()

        transaction = await self.get_by_id(transaction_id)
        if not transaction:
            raise ValueError(
                f"Transaction with ID {transaction_id} not found after status update"
            )
        return transaction

    async def create_deposit_transaction(
        self, user_id: UUID, amount: Decimal, description: Optional[str] = None
    ) -> Transaction:
        """Create deposit transaction."""
        now = datetime.utcnow()
        transaction = Transaction(
            id=uuid4(),
            user_id=user_id,
            amount=amount,
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            description=description,
            created_at=now,
            updated_at=now,
        )
        return await self.create(transaction)

    async def create_charge_transaction(
        self, user_id: UUID, amount: Decimal, task_id: UUID
    ) -> Transaction:
        """Create charge transaction for model usage."""
        now = datetime.utcnow()
        transaction = Transaction(
            id=uuid4(),
            user_id=user_id,
            amount=-abs(amount),  # Ensure amount is negative for charges
            type=TransactionType.CHARGE,
            reference_id=task_id,  # Store as reference_id
            task_id=task_id,  # For compatibility
            status=TransactionStatus.COMPLETED,
            description=f"Payment for task {task_id}",
            created_at=now,
            updated_at=now,
        )
        return await self.create(transaction)

    async def get_user_balance_history(
        self, user_id: UUID, limit: int = 10
    ) -> List[Transaction]:
        """Get user's balance history."""
        result = await self.session.execute(
            select(TransactionModel)
            .where(TransactionModel.user_id == user_id)
            .order_by(TransactionModel.created_at.desc())
            .limit(limit)
        )
        db_txs = result.scalars().all()
        return [self._db_to_entity(db_tx) for db_tx in db_txs]
