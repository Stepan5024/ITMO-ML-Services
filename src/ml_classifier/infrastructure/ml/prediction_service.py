"""Service for making predictions using ML models."""
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from pydantic import ValidationError
from sklearn.pipeline import Pipeline

from ml_classifier.domain.repositories.ml_model_repository import MLModelRepository
from ml_classifier.domain.repositories.task_repository import TaskRepository
from ml_classifier.domain.repositories.transaction_repository import (
    TransactionRepository,
)
from ml_classifier.domain.repositories.user_repository import UserRepository
from ml_classifier.infrastructure.ml.model_loader import ModelLoader, ModelNotFoundError


class PredictionError(Exception):
    """Raised when there's an error during prediction."""

    pass


class InsufficientBalanceError(Exception):
    """Raised when the user has insufficient balance."""

    pass


class PredictionService:
    """Service for making predictions using ML models."""

    def __init__(
        self,
        model_loader: ModelLoader,
        model_repository: MLModelRepository,
        user_repository: UserRepository,
        task_repository: TaskRepository,
        transaction_repository: TransactionRepository,
    ):
        """
        Initialize prediction service.

        Args:
            model_loader: Model loader service
            model_repository: Repository for ML models
            user_repository: Repository for users
            task_repository: Repository for tasks
            transaction_repository: Repository for transactions
        """
        self.model_loader = model_loader
        self.model_repository = model_repository
        self.user_repository = user_repository
        self.task_repository = task_repository
        self.transaction_repository = transaction_repository

    async def predict(
        self,
        user_id: UUID,
        model_id: UUID,
        data: Dict[str, Any],
        version_id: Optional[UUID] = None,
        sandbox: bool = False,
    ) -> Dict[str, Any]:
        start_time = time.time()
        reservation_id = None
        task = None
        logger.info(
            f"Predict called with model_id: {model_id}, version_id: {version_id}"
        )
        try:
            # 1. Загрузка метаданных
            model_entity = await self.model_repository.get_by_id(model_id)
            if not model_entity:
                logger.error(f"Model with ID {model_id} not found")
                raise ModelNotFoundError(f"Model {model_id} not found")

            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise PredictionError(f"User {user_id} not found")

            # 2. Валидация входных данных
            validated_data = await self.validate_input(model_id, data)

            # 3. Бронирование средств (если не sandbox)
            if not sandbox and model_entity.price_per_call > 0:
                if not user.check_sufficient_balance(model_entity.price_per_call):
                    raise InsufficientBalanceError(
                        f"Insufficient balance. Required: {float(model_entity.price_per_call)}, "
                        f"Available: {float(user.balance)}"
                    )
                task = await self.task_repository.create(
                    {
                        "user_id": user_id,
                        "model_id": model_id,
                        "input_data": validated_data,
                        "status": "processing",
                    }
                )
                tx = await self.transaction_repository.create_charge_transaction(
                    user_id=user_id, amount=model_entity.price_per_call, task_id=task.id
                )
                reservation_id = tx.id

            try:
                vectorizer = await self.model_loader.load_vectorizer(
                    model_id, version_id
                )
            except ModelNotFoundError as e:
                logger.warning(
                    f"Vectorizer not found, attempting to continue without it: {str(e)}"
                )
                vectorizer = None

            model = await self.model_loader.load_model(model_id, version_id)

            is_pipeline = isinstance(model, Pipeline)

            # 5. Подготовка входа для модели
            if "text" in validated_data:
                raw_text = validated_data["text"]
                if is_pipeline:
                    prediction_input = [raw_text]
                else:
                    vectorizer = await self.model_loader.load_vectorizer(
                        model_id, version_id
                    )
                    prediction_input = vectorizer.transform([raw_text])

                if vectorizer:
                    prediction_input = vectorizer.transform([raw_text])
                else:
                    prediction_input = [raw_text]
            else:
                prediction_input = validated_data

            # 6. Предсказание
            try:
                raw_pred = model.predict(prediction_input)
                if hasattr(raw_pred, "__len__") and len(raw_pred) == 1:
                    raw_pred = raw_pred[0]
            except Exception as e:
                raise PredictionError(f"Model prediction failed: {e}")

            # 7. Форматирование результата
            result = await self.format_output(model_id, raw_pred, validated_data)

            # 8. Добавляем время выполнения
            execution_time = time.time() - start_time
            result["execution_time_ms"] = int(execution_time * 1000)

            # 9. Завершаем задачу и транзакцию, обновляем баланс
            if task:
                await self.task_repository.mark_as_completed(task.id, result)
            if reservation_id:
                await self.transaction_repository.update_status(
                    reservation_id, "completed"
                )
                await self.user_repository.update_balance(
                    user_id, -model_entity.price_per_call
                )

            logger.info(
                f"Prediction completed in {execution_time:.3f}s "
                f"(model={model_id}, user={user_id}, sandbox={sandbox})"
            )
            return result

        except ModelNotFoundError:
            if reservation_id:
                await self.transaction_repository.update_status(
                    reservation_id, "failed"
                )
            raise

        except InsufficientBalanceError:
            raise

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            if reservation_id:
                await self.transaction_repository.update_status(
                    reservation_id, "failed"
                )
            raise PredictionError(f"Prediction failed: {e}")

    async def batch_predict(
        self,
        user_id: UUID,
        model_id: UUID,
        data_list: List[Dict[str, Any]],
        version_id: Optional[UUID] = None,
        sandbox: bool = False,
    ) -> Dict[str, Any]:
        """
        Make batch predictions using the specified model.

        Args:
            user_id: ID of the user making the request
            model_id: ID of the model to use
            data_list: List of input data for predictions
            version_id: Optional version ID of the model
            sandbox: Whether this is a sandbox (free) prediction

        Returns:
            Batch prediction results

        Raises:
            ModelNotFoundError: If model is not found
            InsufficientBalanceError: If user has insufficient balance
            PredictionError: If there's an error during prediction
        """
        start_time = time.time()
        reservation_id = None

        try:
            model_entity = await self.model_repository.get_by_id(model_id)
            if not model_entity:
                raise ModelNotFoundError(f"Model with ID {model_id} not found")

            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise PredictionError(f"User with ID {user_id} not found")

            batch_size = len(data_list)
            total_cost = model_entity.price_per_call * batch_size

            if not sandbox and total_cost > 0:
                if not user.check_sufficient_balance(total_cost):
                    raise InsufficientBalanceError(
                        f"Insufficient balance. Required: {float(total_cost)}, "
                        f"Available: {float(user.balance)}"
                    )

                task = await self.task_repository.create(
                    {
                        "user_id": user_id,
                        "model_id": model_id,
                        "input_data": {"batch": data_list},
                        "status": "processing",
                    }
                )

                transaction = (
                    await self.transaction_repository.create_charge_transaction(
                        user_id=user_id, amount=total_cost, task_id=task.id
                    )
                )
                reservation_id = transaction.id

            model = await self.model_loader.load_model(model_id, version_id)

            validated_data_list = [
                await self.validate_input(model_id, data) for data in data_list
            ]

            features = self._extract_batch_features(validated_data_list)

            raw_predictions = model.predict(features)

            results = []
            for i, raw_prediction in enumerate(raw_predictions):
                result = await self.format_output(
                    model_id, raw_prediction, validated_data_list[i]
                )
                results.append(result)
            execution_time = time.time() - start_time

            if not sandbox and total_cost > 0:
                await self.task_repository.mark_as_completed(
                    task.id, {"results": results}
                )
            if not sandbox and total_cost > 0 and reservation_id:
                await self.transaction_repository.update_status(
                    reservation_id, "completed"
                )
                await self.user_repository.update_balance(user_id, -total_cost)

            logger.info(
                f"Batch prediction completed for model {model_id} in {execution_time:.3f}s "
                f"(user: {user_id}, items: {batch_size}, {'sandbox' if sandbox else 'production'})"
            )

            return {"results": results, "execution_time_ms": int(execution_time * 1000)}

        except ModelNotFoundError as e:
            logger.error(f"Model not found: {str(e)}")
            if reservation_id:
                await self.transaction_repository.update_status(
                    reservation_id, "failed"
                )
            raise

        except InsufficientBalanceError as e:
            logger.error(f"Insufficient balance: {str(e)}")
            raise

        except Exception as e:
            logger.exception(f"Error during batch prediction: {str(e)}")
            if reservation_id:
                await self.transaction_repository.update_status(
                    reservation_id, "failed"
                )
            raise PredictionError(f"Batch prediction failed: {str(e)}")

    async def validate_input(
        self, model_id: UUID, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate input data against the model's input schema.

        Args:
            model_id: ID of the model
            data: Input data to validate

        Returns:
            Validated data

        Raises:
            ValidationError: If validation fails
        """
        model_entity = await self.model_repository.get_by_id(model_id)
        if not model_entity:
            raise ModelNotFoundError(f"Model with ID {model_id} not found")

        input_schema = model_entity.input_schema
        for field, field_schema in input_schema.items():
            if field_schema.get("required", False) and field not in data:
                raise ValidationError(f"Missing required field: {field}")
        for field, value in data.items():
            if field in input_schema:
                field_type = input_schema[field].get("type")
                if field_type == "string" and not isinstance(value, str):
                    raise ValidationError(f"Field {field} must be a string")
                elif field_type == "number" and not isinstance(value, (int, float)):
                    raise ValidationError(f"Field {field} must be a number")
                elif field_type == "integer" and not isinstance(value, int):
                    raise ValidationError(f"Field {field} must be an integer")
                elif field_type == "boolean" and not isinstance(value, bool):
                    raise ValidationError(f"Field {field} must be a boolean")

        return data

    async def format_output(
        self, model_id: UUID, raw_prediction: Any, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format raw prediction according to the model's output schema.

        Args:
            model_id: ID of the model
            raw_prediction: Raw prediction from model
            input_data: Original input data

        Returns:
            Formatted output
        """
        model_entity = await self.model_repository.get_by_id(model_id)
        if not model_entity:
            raise ModelNotFoundError(f"Model with ID {model_id} not found")

        output_schema = model_entity.output_schema
        if model_entity.model_type == "classification":
            result = {"prediction": "positive" if raw_prediction == 1 else "negative"}
            if "confidence" in output_schema:
                result["confidence"] = 0.85

            if "categories" in output_schema:
                if "text" in input_data:
                    result["categories"] = self._extract_categories(input_data["text"])
        elif model_entity.model_type == "regression":
            result = {"prediction": float(raw_prediction)}
            if "error_bounds" in output_schema:
                result["error_bounds"] = {
                    "lower": float(raw_prediction) - 0.1,
                    "upper": float(raw_prediction) + 0.1,
                }
        else:
            if isinstance(raw_prediction, (list, tuple, set)):
                result = {"prediction": list(raw_prediction)}
            else:
                result = {"prediction": raw_prediction}

        return result

    def _extract_batch_features(self, data_list: List[Dict[str, Any]]) -> List[Any]:
        """
        Extract features for batch processing.

        Args:
            data_list: List of input data

        Returns:
            Extracted features for batch processing
        """
        if all("text" in data for data in data_list):
            features = [data["text"] for data in data_list]
            logger.info(f"Extracted {len(features)} text features for batch prediction")
            return features

        logger.warning("Non-standard batch input format, attempting to process as is")
        return data_list

    def _extract_categories(self, text: str) -> List[str]:
        """
        Extract categories from text (placeholder implementation).

        Args:
            text: Input text

        Returns:
            List of extracted categories
        """
        categories = []
        keywords = {
            "quality": ["качество", "хороший", "плохой", "отличн"],
            "content": ["содержание", "материал", "программа"],
            "instructor": ["преподаватель", "учитель", "объясн"],
            "price": ["цена", "стоимость", "дорого", "дешево"],
            "support": ["поддержка", "помощь", "отвечают", "вопрос"],
        }

        text_lower = text.lower()
        for category, words in keywords.items():
            if any(keyword in text_lower for keyword in words):
                categories.append(category)

        if not categories:
            categories = ["general"]

        return categories
