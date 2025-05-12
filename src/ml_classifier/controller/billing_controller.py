"""Billing API controller."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, validator

from ml_classifier.domain.entities.enums import TransactionStatus, TransactionType
from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.ml_model_repository import (
    SQLAlchemyMLModelRepository,
)
from ml_classifier.infrastructure.db.repositories.transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from ml_classifier.infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user
from ml_classifier.services.billing_use_cases import (
    BillingUseCase,
    TransactionError,
)
from ml_classifier.services.pricing_service import PricingService
from ml_classifier.services.transaction_manager import TransactionManager


class BalanceResponse(BaseModel):
    """Response model for balance endpoint."""

    balance: float
    currency: str = "USD"
    last_updated: datetime


class TransactionResponse(BaseModel):
    """Response model for transaction data."""

    id: UUID
    type: str
    amount: float
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    description: Optional[str] = None
    task_id: Optional[UUID] = None


class TransactionListResponse(BaseModel):
    """Response model for transaction list endpoint."""

    items: List[TransactionResponse]
    total: int
    page: int
    size: int
    pages: int


class DepositRequest(BaseModel):
    """Request model for deposit endpoint."""

    amount: float = Field(..., gt=0)
    payment_method: str = "card"

    @validator("amount")
    def amount_must_be_positive(cls, v):
        """Validate amount is positive."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class CostCalculationRequest(BaseModel):
    """Request model for cost calculation endpoint."""

    model_id: UUID
    input_data: dict
    priority: str = "normal"
    batch_size: int = Field(1, ge=1)

    @validator("priority")
    def priority_must_be_valid(cls, v):
        """Validate priority value."""
        if v not in ["normal", "high"]:
            raise ValueError("Priority must be either 'normal' or 'high'")
        return v


# ----- Router and Dependencies ----- #

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


async def get_billing_use_case(
    session=Depends(get_db),
) -> BillingUseCase:
    """Get billing use case with dependencies."""
    transaction_repo = SQLAlchemyTransactionRepository(session)
    user_repo = SQLAlchemyUserRepository(session)
    model_repo = SQLAlchemyMLModelRepository(session)
    pricing_service = PricingService(model_repo, user_repo)

    return BillingUseCase(
        transaction_repository=transaction_repo,
        user_repository=user_repo,
        pricing_service=pricing_service,
    )


async def get_transaction_manager(
    session=Depends(get_db),
) -> TransactionManager:
    """Get transaction manager with dependencies."""
    transaction_repo = SQLAlchemyTransactionRepository(session)
    user_repo = SQLAlchemyUserRepository(session)

    return TransactionManager(
        transaction_repository=transaction_repo,
        user_repository=user_repo,
    )


# ----- Endpoints ----- #


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: User = Depends(get_current_active_user),
    billing_use_case: BillingUseCase = Depends(get_billing_use_case),
):
    """
    Get current user's balance.

    Returns:
        BalanceResponse: Current balance information
    """
    try:
        balance = await billing_use_case.get_balance(current_user.id)
        return BalanceResponse(
            balance=float(balance),
            last_updated=current_user.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    transaction_type: Optional[str] = Query(
        None, description="Filter by transaction type"
    ),
    status: Optional[str] = Query(None, description="Filter by status"),
    from_date: Optional[date] = Query(None, alias="from", description="From date"),
    to_date: Optional[date] = Query(None, alias="to", description="To date"),
    current_user: User = Depends(get_current_active_user),
    billing_use_case: BillingUseCase = Depends(get_billing_use_case),
):
    """
    Get transaction history with filtering and pagination.

    Returns:
        TransactionListResponse: List of transactions
    """
    try:
        # Convert string parameters to enums if provided
        tx_type = None
        if transaction_type:
            try:
                tx_type = TransactionType(transaction_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid transaction type: {transaction_type}",
                )

        tx_status = None
        if status:
            try:
                tx_status = TransactionStatus(status.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid transaction status: {status}",
                )

        # Get transactions
        transactions = await billing_use_case.get_transactions(
            user_id=current_user.id,
            transaction_type=tx_type,
            status=tx_status,
            limit=size,
        )

        # Convert to response model
        items = [
            TransactionResponse(
                id=tx.id,
                type=tx.type.value,
                amount=float(tx.amount),
                status=tx.status.value,
                created_at=tx.created_at,
                completed_at=tx.completed_at,
                description=tx.description,
                task_id=tx.task_id,
            )
            for tx in transactions
        ]

        # Simple pagination - in a real app, you'd need to count total matching transactions
        total = len(items)
        pages = (total + size - 1) // size if size > 0 else 0

        return TransactionListResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/deposit",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def deposit_funds(
    deposit_data: DepositRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    billing_use_case: BillingUseCase = Depends(get_billing_use_case),
    transaction_manager: TransactionManager = Depends(get_transaction_manager),
):
    """
    Emulate deposit operation (for development/testing).

    In production, this would integrate with a payment gateway.

    Returns:
        TransactionResponse: Created transaction
    """
    try:
        amount = Decimal(str(deposit_data.amount))
        description = f"Deposit via {deposit_data.payment_method}"

        # Process deposit
        transaction, new_balance = await billing_use_case.deposit(
            user_id=current_user.id,
            amount=amount,
            description=description,
        )

        # Schedule cleanup of stale transactions
        background_tasks.add_task(transaction_manager.cleanup_stale_transactions)

        return TransactionResponse(
            id=transaction.id,
            type=transaction.type.value,
            amount=float(transaction.amount),
            status=transaction.status.value,
            created_at=transaction.created_at,
            completed_at=transaction.completed_at,
            description=transaction.description,
            task_id=transaction.task_id,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TransactionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/transaction/{transaction_id}", response_model=TransactionResponse)
async def get_transaction_details(
    transaction_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session=Depends(get_db),
):
    """
    Get details of a specific transaction.

    Returns:
        TransactionResponse: Transaction details
    """
    transaction_repo = SQLAlchemyTransactionRepository(session)
    transaction = await transaction_repo.get_by_id(transaction_id)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    # Check if transaction belongs to current user
    if transaction.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this transaction",
        )

    return TransactionResponse(
        id=transaction.id,
        type=transaction.type.value,
        amount=float(transaction.amount),
        status=transaction.status.value,
        created_at=transaction.created_at,
        completed_at=transaction.completed_at,
        description=transaction.description,
        task_id=transaction.task_id,
    )


@router.post("/calculate-cost", response_model=dict)
async def calculate_cost(
    cost_data: CostCalculationRequest,
    current_user: User = Depends(get_current_active_user),
    billing_use_case: BillingUseCase = Depends(get_billing_use_case),
):
    """
    Calculate cost for a prediction without executing it.

    Returns:
        dict: Cost details
    """
    try:
        cost_details = await billing_use_case.calculate_cost(
            model_id=cost_data.model_id,
            input_data=cost_data.input_data,
            batch_size=cost_data.batch_size,
        )

        # Add user's current balance
        cost_details["user_balance"] = float(current_user.balance)
        cost_details["can_afford"] = current_user.balance >= Decimal(
            str(cost_details["discounted_cost"])
        )

        return cost_details

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
