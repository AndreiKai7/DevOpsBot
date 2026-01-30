import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from bot.config import BOT_TOKEN, CHECK_INTERVAL, ALERT_COOLDOWN
from bot.logger import setup_logger
from bot.handlers import (
    start, status, cmd_cpu, cmd_ram, cmd_disk, cmd_uptime, alerts_status
)
from bot.alerts import check_alerts

logger = setup_logger()

async def alarm_job(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача для проверки алертов."""
    logger.info("Running scheduled alert check...")
    alert_msg = check_alerts(ALERT_COOLDOWN)
    if alert_msg:
        await context.bot.send_message(
            chat_id=context.job.data, 
            text=alert_msg
        )
        logger.info("Alert sent to Telegram")

def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set in environment variables.")
        return

    # Создаем приложение
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("cpu", cmd_cpu))
    application.add_handler(CommandHandler("ram", cmd_ram))
    application.add_handler(CommandHandler("disk", cmd_disk))
    application.add_handler(CommandHandler("uptime", cmd_uptime))
    application.add_handler(CommandHandler("alerts", alerts_status))

    # Получаем ID админа для JobQueue (куда слать алерты)
    from bot.config import TELEGRAM_USER_ID
    
    # Добавляем задачу в очередь (JobQueue)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(alarm_job, interval=CHECK_INTERVAL, first=10, data=TELEGRAM_USER_ID)
    else:
        logger.error("JobQueue is not initialized.")

    logger.info("Bot started successfully.")
    
    # Запускаем бота (polling)
    application.run_polling()

if __name__ == "__main__":
    main()