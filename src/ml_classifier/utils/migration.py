# src/ml_classifier/utils/migration.py
"""Утилиты для работы с миграциями."""
import os
import subprocess
from pathlib import Path

from loguru import logger


async def run_migrations() -> bool:
    """Запуск миграций базы данных перед запуском приложения.

    Returns:
        bool: True, если миграции выполнены успешно, иначе False
    """
    try:
        logger.info("Running database migrations...")
        project_root = Path(__file__).parents[3]
        alembic_path = os.path.join(project_root, "alembic.ini")

        result = subprocess.run(
            ["alembic", "-c", alembic_path, "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info(f"Migrations completed successfully: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Migration error: {str(e)}")
        return False
