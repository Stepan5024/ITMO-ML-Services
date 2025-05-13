from celery.signals import task_prerun, task_success, task_failure, task_retry
import time
from loguru import logger

task_start_times = {}


@task_prerun.connect
def task_prerun_handler(task_id=None, task=None, *args, **kwargs):
    """Логируем начало выполнения задачи."""
    task_start_times[task_id] = time.time()

    # Извлекаем информацию о типе задачи и аргументах
    task_name = task.name if task else "Unknown"

    # Защита чувствительных данных в аргументах
    args_str = str(args)
    if len(args_str) > 1000:
        args_str = args_str[:500] + "... [truncated]"

    filtered_kwargs = {
        k: v for k, v in kwargs.items() if k not in ["password", "token"]
    }

    logger.info(
        f"Task started: {task_name}[{task_id}], args: {args_str}, kwargs: {filtered_kwargs}"
    )


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Логируем успешное завершение задачи."""
    task_id = kwargs.get("task_id")
    task_name = sender.name if sender else "Unknown"

    if task_id in task_start_times:
        duration = time.time() - task_start_times[task_id]
        logger.success(
            f"Task succeeded: {task_name}[{task_id}], duration: {duration:.3f}s"
        )
        # Очищаем данные о времени начала
        del task_start_times[task_id]
    else:
        logger.success(f"Task succeeded: {task_name}[{task_id}]")

    # Защита чувствительных данных в результате
    result_str = str(result)
    if len(result_str) > 1000:
        result_str = result_str[:500] + "... [truncated]"

    logger.debug(f"Task result: {task_name}[{task_id}], result: {result_str}")


@task_failure.connect
def task_failure_handler(
    sender=None, task_id=None, exception=None, traceback=None, **kwargs
):
    """Логируем ошибку при выполнении задачи."""
    task_name = sender.name if sender else "Unknown"

    if task_id in task_start_times:
        duration = time.time() - task_start_times[task_id]
        logger.error(
            f"Task failed: {task_name}[{task_id}], duration: {duration:.3f}s, exception: {exception}"
        )
        # Очищаем данные о времени начала
        del task_start_times[task_id]
    else:
        logger.error(f"Task failed: {task_name}[{task_id}], exception: {exception}")

    if traceback:
        logger.error(f"Task traceback: {task_name}[{task_id}]\n{traceback}")


@task_retry.connect
def task_retry_handler(sender=None, request=None, reason=None, **kwargs):
    """Логируем повторную попытку выполнения задачи."""
    task_id = request.id if request else "Unknown"
    task_name = sender.name if sender else "Unknown"

    logger.warning(f"Task retry: {task_name}[{task_id}], reason: {reason}")
