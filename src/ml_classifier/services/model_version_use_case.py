"""Use case for model version management."""
from typing import Dict, Optional, Tuple, Any
from uuid import UUID, uuid4
import time
from loguru import logger

from ml_classifier.domain.entities.ml_model_version import (
    MLModelVersion,
    ModelVersionStatus,
)
from ml_classifier.domain.repositories.ml_model_version_repository import (
    MLModelVersionRepository,
)
from ml_classifier.infrastructure.ml.model_storage import ModelStorage


class ModelVersionUseCase:
    """Use case for managing model versions."""

    def __init__(
        self, version_repository: MLModelVersionRepository, model_storage: ModelStorage
    ):
        """Initialize with repositories and storage."""
        self.version_repository = version_repository
        self.model_storage = model_storage

    async def create_version(
        self,
        model_id: UUID,
        version_data: Dict[str, Any],
        file_content: bytes,
        user_id: UUID,
    ) -> Tuple[bool, str, Optional[MLModelVersion]]:
        """
        Create a new model version with file.

        Args:
            model_id: Parent model ID
            version_data: Version metadata
            file_content: Model file binary content
            user_id: ID of the user creating the version

        Returns:
            Tuple[bool, str, Optional[MLModelVersion]]: (success, message, created_version)
        """
        operation_id = str(uuid4())
        start_time = time.time()

        logger.info(
            f"[{operation_id}] Запрос на создание новой версии модели: model_id={model_id}, "
            f"версия={version_data.get('version', 'не указана')}"
        )
        logger.debug(
            f"[{operation_id}] Размер файла модели: {len(file_content)} байт, пользователь: {user_id}"
        )

        existing = await self.version_repository.get_by_model_id_and_version(
            model_id, version_data["version"]
        )
        if existing:
            execution_time = time.time() - start_time
            logger.warning(
                f"[{operation_id}] Версия {version_data['version']} уже существует для модели"
                f" {model_id} | Время выполнения: {execution_time:.3f}с"
            )
            return (
                False,
                f"Version {version_data['version']} already exists for this model",
                None,
            )

        logger.debug(
            f"[{operation_id}] Сохранение файла модели на диск: model_id={model_id}, версия={version_data['version']}"
        )
        success, message, file_path = self.model_storage.save_model(
            file_content, model_id, version_data["version"]
        )
        if not success:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при сохранении файла модели: {message}"
                f" | Время выполнения: {execution_time:.3f}с"
            )
            return False, message, None

        file_size = self.model_storage.get_model_size(file_path)
        logger.debug(
            f"[{operation_id}] Файл модели сохранен: путь={file_path}, размер={file_size} байт"
        )

        logger.debug(
            f"[{operation_id}] Проверка, должна ли версия быть дефолтной для модели {model_id}"
        )
        versions = await self.version_repository.get_by_model_id(model_id)
        is_default = len(versions) == 0
        logger.debug(
            f"[{operation_id}] Найдено существующих версий: {len(versions)}, установка как дефолтной: {is_default}"
        )

        version_entity = MLModelVersion(
            model_id=model_id,
            version=version_data["version"],
            file_path=file_path,
            metrics=version_data.get("metrics", {}),
            parameters=version_data.get("parameters", {}),
            is_default=is_default,
            created_by=user_id,
            file_size=file_size,
            status=version_data.get("status", ModelVersionStatus.TRAINED),
        )
        logger.debug(
            f"[{operation_id}] Создан объект версии модели: model_id={model_id}, "
            f"версия={version_data['version']}, размер={file_size}, дефолтная={is_default}"
        )

        try:
            logger.debug(
                f"[{operation_id}] Сохранение информации о версии модели в базу данных"
            )
            created = await self.version_repository.create(version_entity)
            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Версия модели успешно создана: model_id={model_id}, "
                f"версия={version_data['version']}, ID версии={created.id} | Время выполнения: {execution_time:.3f}с"
            )
            return True, "Model version created successfully", created
        except Exception as e:
            logger.error(
                f"[{operation_id}] Ошибка при создании версии модели: {str(e)}"
            )
            logger.debug(
                f"[{operation_id}] Удаление сохраненного файла модели из-за ошибки: {file_path}"
            )
            self.model_storage.delete_model(file_path)
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при создании версии модели: {str(e)} "
                f"| Время выполнения: {execution_time:.3f}с"
            )
            return False, f"Error creating version: {str(e)}", None
