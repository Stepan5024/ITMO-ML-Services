""" Use cases for ML model and version management."""
import os
import re
import uuid
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID, uuid4

from fastapi import UploadFile
import joblib
from loguru import logger

from ml_classifier.domain.entities.ml_model import MLModel, ModelType, ModelAlgorithm
from ml_classifier.domain.entities.ml_model_version import (
    MLModelVersion,
    ModelVersionStatus,
)
from ml_classifier.domain.repositories.ml_model_repository import MLModelRepository
from ml_classifier.domain.repositories.ml_model_version_repository import (
    MLModelVersionRepository,
)


class ModelUseCase:
    """Кейс использования для управления моделями машинного обучения."""

    def __init__(
        self,
        model_repository: MLModelRepository,
        version_repository: MLModelVersionRepository,
        model_storage_path: str = "models",
    ):
        """
        Инициализация кейса с репозиториями.

        Аргументы:
            model_repository: Репозиторий для моделей машинного обучения
            version_repository: Репозиторий для версий моделей
            model_storage_path: Путь для хранения файлов моделей
        """
        self.model_repository = model_repository
        self.version_repository = version_repository
        self.model_storage_path = model_storage_path

        os.makedirs(self.model_storage_path, exist_ok=True)
        logger.info(f"Модели будут сохраняться в {self.model_storage_path}")

    async def create_model(
        self, model_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[MLModel]]:
        """
        Создать новую модель машинного обучения.

        Аргументы:
            model_data: Метаданные модели

        Возвращает:
            Tuple[bool, str, Optional[MLModel]]: (успех, сообщение, созданная модель)
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(
            f"[{operation_id}] Начало создания новой модели: '{model_data.get('name', 'Unnamed')}'"
        )
        logger.debug(f"[{operation_id}] Данные модели: {model_data}")

        existing_model = await self.model_repository.get_by_name(model_data["name"])
        if existing_model:
            logger.warning(
                f"[{operation_id}] Модель с именем '{model_data['name']}' уже существует. ID: {existing_model.id}"
            )
            return False, f"Модель с именем '{model_data['name']}' уже существует", None

        required_fields = [
            "name",
            "model_type",
            "algorithm",
            "input_schema",
            "output_schema",
        ]
        for field in required_fields:
            if field not in model_data:
                logger.warning(
                    f"[{operation_id}] Валидация не пройдена: отсутствует обязательное поле: {field}"
                )
                return False, f"Отсутствует обязательное поле: {field}", None

        try:
            model_type = ModelType(model_data["model_type"])
            algorithm = ModelAlgorithm(model_data["algorithm"])
            logger.debug(
                f"[{operation_id}] Тип модели: {model_type}, Алгоритм: {algorithm}"
            )
        except ValueError as e:
            logger.error(f"[{operation_id}] Неверное значение перечисления: {str(e)}")
            return False, f"Неверное значение перечисления: {str(e)}", None

        model_id = uuid.uuid4()
        model = MLModel(
            id=model_id,
            name=model_data["name"],
            description=model_data.get("description"),
            model_type=model_type,
            algorithm=algorithm,
            input_schema=model_data["input_schema"],
            output_schema=model_data["output_schema"],
            is_active=model_data.get("is_active", True),
            price_per_call=Decimal(str(model_data.get("price_per_call", 0.0))),
        )
        logger.debug(
            f"[{operation_id}] Создание объекта модели: ID: {model_id}, Имя: {model.name}, Активность: "
            f"{model.is_active}, Цена: {model.price_per_call}"
        )

        try:
            created_model = await self.model_repository.create(model)
            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Модель '{model.name}' успешно создана. ID: {created_model.id} | Время выполнения:"
                f" {execution_time:.3f}с"
            )
            return True, "Модель успешно создана", created_model
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при создании модели '{model.name}': {str(e)} | Время выполнения: "
                f"{execution_time:.3f}с"
            )
            return False, f"Ошибка при создании модели: {str(e)}", None

    async def update_model(
        self, model_id: UUID, model_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[MLModel]]:
        """
        Обновить метаданные модели машинного обучения.

        Аргументы:
            model_id: ID модели
            model_data: Обновленные данные модели

        Возвращает:
            Tuple[bool, str, Optional[MLModel]]: (успех, сообщение, обновленная модель)
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(f"[{operation_id}] Запрос на обновление модели с ID {model_id}")
        logger.debug(f"[{operation_id}] Данные для обновления: {model_data}")

        model = await self.model_repository.get_by_id(model_id)
        if not model:
            logger.warning(f"[{operation_id}] Модель с ID {model_id} не найдена.")
            return False, f"Модель с ID {model_id} не найдена", None

        logger.debug(
            f"[{operation_id}] Найдена модель: ID: {model.id}, Имя: {model.name}, Тип: {model.model_type}, "
            f"Алгоритм: {model.algorithm}"
        )

        if "name" in model_data and model_data["name"] != model.name:
            logger.debug(
                f"[{operation_id}] Обнаружено изменение имени модели: '{model.name}' -> '{model_data['name']}'"
            )
            existing = await self.model_repository.get_by_name(model_data["name"])
            if existing and existing.id != model_id:
                logger.warning(
                    f"[{operation_id}] Модель с именем '{model_data['name']}' уже существует (ID: {existing.id})."
                )
                return (
                    False,
                    f"Модель с именем '{model_data['name']}' уже существует",
                    None,
                )

        model_type = model.model_type
        algorithm = model.algorithm

        if "model_type" in model_data:
            try:
                model_type = ModelType(model_data["model_type"])
                logger.debug(
                    f"[{operation_id}] Изменение типа модели: {model.model_type} -> {model_type}"
                )
            except ValueError as e:
                logger.error(f"[{operation_id}] Неверный тип модели: {str(e)}")
                return False, f"Неверный тип модели: {str(e)}", None

        if "algorithm" in model_data:
            try:
                algorithm = ModelAlgorithm(model_data["algorithm"])
                logger.debug(
                    f"[{operation_id}] Изменение алгоритма модели: {model.algorithm} -> {algorithm}"
                )
            except ValueError as e:
                logger.error(f"[{operation_id}] Неверный алгоритм: {str(e)}")
                return False, f"Неверный алгоритм: {str(e)}", None

        updated_model = MLModel(
            id=model.id,
            name=model_data.get("name", model.name),
            description=model_data.get("description", model.description),
            model_type=model_type,
            algorithm=algorithm,
            input_schema=model_data.get("input_schema", model.input_schema),
            output_schema=model_data.get("output_schema", model.output_schema),
            is_active=model_data.get("is_active", model.is_active),
            price_per_call=Decimal(
                str(model_data.get("price_per_call", model.price_per_call))
            ),
            created_at=model.created_at,
            updated_at=datetime.utcnow(),
        )

        logger.debug(
            f"[{operation_id}] Подготовлена обновленная модель. Имя: {updated_model.name}, Активность: "
            f"{updated_model.is_active}, Цена: {updated_model.price_per_call}"
        )

        try:
            updated = await self.model_repository.update(updated_model)
            execution_time = time.time() - start_time
            logger.success(
                f"[{operation_id}] Модель '{updated_model.name}' успешно обновлена. ID: {updated.id} |"
                f" Время выполнения: {execution_time:.3f}с"
            )
            return True, "Модель успешно обновлена", updated
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при обновлении модели '{updated_model.name}': {str(e)} | "
                f"Время выполнения: {execution_time:.3f}с"
            )
            return False, f"Ошибка при обновлении модели: {str(e)}", None

    async def delete_model(self, model_id: UUID) -> Tuple[bool, str]:
        """
        Удалить модель машинного обучения и все её версии.

        Аргументы:
            model_id: ID модели

        Возвращает:
            Tuple[bool, str]: (успех, сообщение)
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(f"[{operation_id}] Запрос на удаление модели с ID {model_id}")

        model = await self.model_repository.get_by_id(model_id)
        if not model:
            logger.warning(f"[{operation_id}] Модель с ID {model_id} не найдена.")
            return False, f"Модель с ID {model_id} не найдена"

        logger.debug(
            f"[{operation_id}] Найдена модель: ID: {model.id}, Имя: {model.name}, Тип: {model.model_type}"
        )

        versions = await self.version_repository.get_by_model_id(model_id)
        logger.info(
            f"[{operation_id}] Обнаружено {len(versions)} версий модели '{model.name}', которые будут удалены"
        )

        for version in versions:
            try:
                logger.debug(
                    f"[{operation_id}] Удаление версии {version.id}, файл: {version.file_path}"
                )
                if os.path.exists(version.file_path):
                    os.remove(version.file_path)
                    logger.debug(
                        f"[{operation_id}] Файл модели удален: {version.file_path}"
                    )
                await self.version_repository.delete(version.id)
                logger.info(
                    f"[{operation_id}] Версия {version.id} модели {model.name} удалена из БД."
                )
            except Exception as e:
                logger.error(
                    f"[{operation_id}] Ошибка при удалении версии {version.id}: {str(e)}"
                )
                return False, f"Ошибка при удалении версии {version.id}: {str(e)}"

        try:
            logger.debug(f"[{operation_id}] Удаление данных модели из БД: {model_id}")
            success = await self.model_repository.delete(model_id)
            execution_time = time.time() - start_time

            if success:
                logger.success(
                    f"[{operation_id}] Модель {model.name} (ID: {model_id}) и все её версии ({len(versions)}) удалены."
                    f" | Время выполнения: {execution_time:.3f}с"
                )
                return True, "Модель и все её версии успешно удалены"
            else:
                logger.warning(
                    f"[{operation_id}] Не удалось удалить модель {model.name} (ID: {model_id}) | Время выполнения: "
                    f"{execution_time:.3f}с"
                )
                return False, "Не удалось удалить модель"

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при удалении модели {model.name} (ID: {model_id}): {str(e)} "
                f"| Время выполнения: {execution_time:.3f}с"
            )
            return False, f"Ошибка при удалении модели: {str(e)}"

    async def get_model_by_id(self, model_id: UUID) -> Optional[MLModel]:
        """
        Получить модель по ID.

        Аргументы:
            model_id: ID модели

        Возвращает:
            Optional[MLModel]: Найденная модель или None
        """
        operation_id = str(uuid4())
        start_time = time.time()
        logger.info(f"[{operation_id}] Запрос модели по ID: {model_id}")

        try:
            model = await self.model_repository.get_by_id(model_id)
            execution_time = time.time() - start_time

            if model:
                logger.debug(
                    f"[{operation_id}] Модель найдена: ID: {model.id}, Имя: {model.name}, Тип: {model.model_type},"
                    f" Активна: {model.is_active} | Время выполнения: {execution_time:.3f}с"
                )
            else:
                logger.warning(
                    f"[{operation_id}] Модель с ID {model_id} не найдена | Время выполнения: {execution_time:.3f}с"
                )

            return model
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при получении модели по ID {model_id}: {str(e)} | Время выполнения: "
                f"{execution_time:.3f}с"
            )
            return None

    async def list_models(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[MLModel], int]:
        """
        Получить список моделей с фильтрами.

        Аргументы:
            skip: Количество пропускаемых записей
            limit: Максимальное количество возвращаемых записей
            search: Поисковый запрос по имени или описанию
            model_type: Фильтрация по типу модели
            is_active: Фильтрация по статусу активности

        Возвращает:
            Tuple[List[MLModel], int]: Список моделей и общее количество
        """
        operation_id = str(uuid4())
        start_time = time.time()

        filters_info = {
            "skip": skip,
            "limit": limit,
            "search": search,
            "model_type": model_type.value if model_type else None,
            "is_active": is_active,
        }
        logger.info(
            f"[{operation_id}] Запрос списка моделей с фильтрами: {filters_info}"
        )

        try:
            if search:
                logger.debug(f"[{operation_id}] Поиск моделей по запросу: '{search}'")
                models = await self.model_repository.search_models(
                    query=search, model_type=model_type, skip=skip, limit=limit
                )
                total = len(models) + skip
                logger.debug(
                    f"[{operation_id}] Найдено моделей по поиску: {len(models)}"
                )
            else:
                logger.debug(
                    f"[{operation_id}] Получение списка всех моделей с пагинацией: skip={skip}, limit={limit}"
                )
                models = await self.model_repository.list(skip=skip, limit=limit)
                total = await self.model_repository.count()
                logger.debug(
                    f"[{operation_id}] Получено моделей: {len(models)}, всего в БД: {total}"
                )

            # Применение фильтра по активности, если указан
            if is_active is not None:
                initial_count = len(models)
                models = [model for model in models if model.is_active == is_active]
                logger.debug(
                    f"[{operation_id}] Фильтрация по активности (is_active={is_active}):"
                    f" отфильтровано {initial_count - len(models)} моделей"
                )

            execution_time = time.time() - start_time
            model_ids = [str(model.id) for model in models]
            logger.success(
                f"[{operation_id}] Успешно получен список моделей. Найдено: {len(models)} из {total} "
                f"| Время выполнения: {execution_time:.3f}с"
            )
            logger.debug(f"[{operation_id}] IDs полученных моделей: {model_ids}")

            return models, total

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[{operation_id}] Ошибка при получении списка моделей: {str(e)} | Время выполнения: "
                f"{execution_time:.3f}с"
            )
            return [], 0

    async def activate_model(
        self, model_id: UUID
    ) -> Tuple[bool, str, Optional[MLModel]]:
        """
        Активировать ML модель.

        Args:
            model_id: ID модели

        Returns:
            Tuple[bool, str, Optional[MLModel]]: (успех, сообщение, обновленная модель)
        """
        operation_id = str(uuid4())
        logger.info(f"[{operation_id}] Запрос на активацию модели с ID {model_id}")

        try:
            model = await self.model_repository.get_by_id(model_id)
            if not model:
                logger.error(f"[{operation_id}] Модель с ID {model_id} не найдена.")
                return False, f"Модель с ID {model_id} не найдена", None

            logger.debug(
                f"[{operation_id}] Найдена модель: ID: {model.id}, Имя: {model.name}, Активна: {model.is_active}"
            )

            if model.is_active:
                logger.info(f"[{operation_id}] Модель с ID {model_id} уже активна.")
                return True, "Модель уже активна", model

            updated = await self.model_repository.update_status(model_id, True)
            logger.info(
                f"[{operation_id}] Модель с ID {model_id} успешно активирована."
            )
            return True, "Модель успешно активирована", updated
        except Exception as e:
            logger.exception(
                f"[{operation_id}] Ошибка при активации модели с ID {model_id}: {str(e)}"
            )
            return False, f"Ошибка при активации модели: {str(e)}", None

    async def deactivate_model(
        self, model_id: UUID
    ) -> Tuple[bool, str, Optional[MLModel]]:
        """
        Деактивировать ML модель.

        Args:
            model_id: ID модели

        Returns:
            Tuple[bool, str, Optional[MLModel]]: (успех, сообщение, обновленная модель)
        """
        operation_id = str(uuid4())
        logger.info(f"[{operation_id}] Запрос на деактивацию модели с ID {model_id}")

        try:
            model = await self.model_repository.get_by_id(model_id)
            if not model:
                logger.error(f"[{operation_id}] Модель с ID {model_id} не найдена.")
                return False, f"Модель с ID {model_id} не найдена", None

            logger.debug(
                f"[{operation_id}] Найдена модель: ID: {model.id}, Активна: {model.is_active}"
            )

            if not model.is_active:
                logger.info(f"[{operation_id}] Модель уже деактивирована.")
                return True, "Модель уже деактивирована", model

            updated = await self.model_repository.update_status(model_id, False)
            logger.info(f"[{operation_id}] Модель успешно деактивирована.")
            return True, "Модель успешно деактивирована", updated
        except Exception as e:
            logger.exception(f"[{operation_id}] Ошибка при деактивации: {str(e)}")
            return False, f"Ошибка при деактивации: {str(e)}", None


class ModelVersionUseCase:
    """Использование версии ML модели."""

    def __init__(
        self,
        model_repository: MLModelRepository,
        version_repository: MLModelVersionRepository,
        model_storage_path: str = "models",
    ):
        """
        Инициализация use case с репозиториями моделей и версий.

        Args:
            model_repository: Репозиторий моделей
            version_repository: Репозиторий версий моделей
            model_storage_path: Путь для хранения файлов моделей
        """
        self.model_repository = model_repository
        self.version_repository = version_repository
        self.model_storage_path = model_storage_path

        os.makedirs(self.model_storage_path, exist_ok=True)

    async def create_version(
        self,
        model_id: UUID,
        version_data: Dict[str, Any],
        model_file: UploadFile,
        vectorizer_file: Optional[UploadFile] = None,
        user_id: UUID = None,
    ) -> Tuple[bool, str, Optional[MLModelVersion]]:
        """
        Создать новую версию модели с файлом модели и опциональным векторизатором.

        Args:
            model_id: ID модели
            version_data: Данные версии
            model_file: Файл модели
            vectorizer_file: Файл векторизатора (опционально)
            user_id: ID пользователя

        Returns:
            Tuple[bool, str, Optional[MLModelVersion]]: (успех, сообщение, созданная версия модели)
        """
        model = await self.model_repository.get_by_id(model_id)
        if not model:
            logger.error(f"Модель с ID {model_id} не найдена.")
            return False, f"Модель с ID {model_id} не найдена", None

        version = version_data.get("version")
        if not version or not self._is_valid_semver(version):
            logger.warning(f"Неверный формат версии для модели с ID {model_id}.")
            return (
                False,
                "Неверный формат версии. Используйте семантическое версионирование (например, 1.0.0)",
                None,
            )

        existing = await self.version_repository.get_by_model_id_and_version(
            model_id, version
        )
        if existing:
            logger.warning(
                f"Версия {version} уже существует для модели с ID {model_id}."
            )
            return False, f"Версия {version} уже существует", None

        model_dir = os.path.join(self.model_storage_path, str(model_id))
        os.makedirs(model_dir, exist_ok=True)

        version_id = uuid.uuid4()
        version_dir = os.path.join(model_dir, str(version_id))
        os.makedirs(version_dir, exist_ok=True)

        model_file_path = os.path.join(version_dir, "model.joblib")
        vectorizer_file_path = None

        try:
            model_contents = await model_file.read()
            model_file_size = len(model_contents)

            with open(model_file_path, "wb") as f:
                f.write(model_contents)

            try:
                joblib.load(model_file_path)
            except Exception as e:
                if os.path.exists(model_file_path):
                    os.remove(model_file_path)
                logger.error(f"Ошибка при загрузке файла модели: {str(e)}")
                return False, f"Неверный файл модели: {str(e)}", None
            if vectorizer_file:
                vectorizer_file_path = os.path.join(version_dir, "vectorizer.pkl")
                vectorizer_contents = await vectorizer_file.read()

                with open(vectorizer_file_path, "wb") as f:
                    f.write(vectorizer_contents)

                try:
                    joblib.load(vectorizer_file_path)
                except Exception as e:
                    if os.path.exists(vectorizer_file_path):
                        os.remove(vectorizer_file_path)
                    if os.path.exists(model_file_path):
                        os.remove(model_file_path)
                    logger.error(f"Ошибка при загрузке файла векторизатора: {str(e)}")
                    return False, f"Неверный файл векторизатора: {str(e)}", None
            is_default = await self._check_is_default(model_id)

            version_entity = MLModelVersion(
                id=version_id,
                model_id=model_id,
                version=version,
                file_path=model_file_path,
                metrics=version_data.get("metrics", {}),
                parameters=version_data.get("parameters", {}),
                is_default=is_default,
                created_by=user_id,
                file_size=model_file_size,
                status=ModelVersionStatus(version_data.get("status", "trained")),
            )

            created = await self.version_repository.create(version_entity)
            logger.info(
                f"Версия модели с ID {model_id} и версией {version} успешно создана."
            )
            return True, "Версия модели успешно создана", created

        except Exception as e:
            if os.path.exists(model_file_path):
                os.remove(model_file_path)
            if vectorizer_file_path and os.path.exists(vectorizer_file_path):
                os.remove(vectorizer_file_path)
            logger.exception(
                f"Ошибка при создании версии модели с ID {model_id}: {str(e)}"
            )
            return False, f"Ошибка при создании версии модели: {str(e)}", None

    async def _check_is_default(self, model_id: UUID) -> bool:
        """Проверка, должна ли эта версия быть дефолтной."""
        versions = await self.version_repository.get_by_model_id(model_id)
        return len(versions) == 0

    async def get_version(self, version_id: UUID) -> Optional[MLModelVersion]:
        """
        Получить версию модели по ID.

        Args:
            version_id: ID версии

        Returns:
            Optional[MLModelVersion]: Найдена версия или None
        """
        return await self.version_repository.get_by_id(version_id)

    async def list_versions(self, model_id: UUID) -> List[MLModelVersion]:
        """
        Получить все версии модели.

        Args:
            model_id: ID модели

        Returns:
            List[MLModelVersion]: Все версии модели
        """
        return await self.version_repository.get_by_model_id(model_id)

    async def set_default_version(
        self, version_id: UUID
    ) -> Tuple[bool, str, Optional[MLModelVersion]]:
        """
        Установить версию как дефолтную для модели.

        Args:
            version_id: ID версии

        Returns:
            Tuple[bool, str, Optional[MLModelVersion]]: (успех, сообщение, обновленная версия)
        """
        version = await self.version_repository.get_by_id(version_id)
        if not version:
            return False, f"Версия с ID {version_id} не найдена", None

        try:
            await self.version_repository.unset_default_versions(version.model_id)

            updated = await self.version_repository.set_default_version(version_id)
            return True, "Дефолтная версия успешно установлена", updated
        except Exception as e:
            return False, f"Ошибка при установке дефолтной версии: {str(e)}", None

    async def delete_version(self, version_id: UUID) -> Tuple[bool, str]:
        """
        Удалить версию модели.

        Args:
            version_id: ID версии

        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        version = await self.version_repository.get_by_id(version_id)
        if not version:
            return False, f"Версия с ID {version_id} не найдена"

        if version.is_default:
            versions = await self.version_repository.get_by_model_id(version.model_id)
            if len(versions) > 1:
                return (
                    False,
                    "Невозможно удалить дефолтную версию. Сначала установите другую версию как дефолтную.",
                )

        try:
            if os.path.exists(version.file_path):
                os.remove(version.file_path)

            success = await self.version_repository.delete(version_id)
            if success:
                return True, "Версия успешно удалена"
            else:
                return False, "Не удалось удалить версию"
        except Exception as e:
            return False, f"Ошибка при удалении версии: {str(e)}"

    async def get_default_version(self, model_id: UUID) -> Optional[MLModelVersion]:
        """
        Получить дефолтную версию модели.

        Args:
            model_id: ID модели

        Returns:
            Optional[MLModelVersion]: Дефолтная версия или None
        """
        return await self.version_repository.get_default_version(model_id)

    async def compare_versions(
        self, version_id1: UUID, version_id2: UUID
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Сравнить метрики двух версий моделей.

        Args:
            version_id1: ID первой версии
            version_id2: ID второй версии

        Returns:
            Tuple[bool, str, Optional[Dict]]: (успех, сообщение, результат сравнения)
        """
        version1 = await self.version_repository.get_by_id(version_id1)
        if not version1:
            return False, f"Версия с ID {version_id1} не найдена", None

        version2 = await self.version_repository.get_by_id(version_id2)
        if not version2:
            return False, f"Версия с ID {version_id2} не найдена", None

        if version1.model_id != version2.model_id:
            return False, "Невозможно сравнить версии из разных моделей", None

        try:
            metrics1 = version1.metrics
            metrics2 = version2.metrics

            common_metrics = set(metrics1.keys()) & set(metrics2.keys())

            result = {
                "version1": {
                    "id": str(version1.id),
                    "version": version1.version,
                    "metrics": metrics1,
                },
                "version2": {
                    "id": str(version2.id),
                    "version": version2.version,
                    "metrics": metrics2,
                },
                "comparison": {},
            }

            for metric in common_metrics:
                if isinstance(metrics1[metric], (int, float)) and isinstance(
                    metrics2[metric], (int, float)
                ):
                    diff = metrics2[metric] - metrics1[metric]
                    result["comparison"][metric] = {
                        "value_1": metrics1[metric],
                        "value_2": metrics2[metric],
                        "difference": diff,
                    }
            return True, "Сравнение выполнено", result
        except Exception as e:
            logger.exception(
                f"Ошибка при сравнении версий {version_id1} и {version_id2}: {str(e)}"
            )
            return False, f"Ошибка при сравнении версий: {str(e)}", None

    def _is_valid_semver(self, version: str) -> bool:
        """
        Проверка, соответствует ли версия семантическому версионированию.

        Args:
            version: строка версии

        Returns:
            bool: True если версия корректна, иначе False
        """
        semver_pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(semver_pattern, version))
