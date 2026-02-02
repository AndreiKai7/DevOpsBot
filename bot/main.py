import asyncio
from telegram import Update, BotCommand, MenuButtonCommands
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from bot.config import BOT_TOKEN, CHECK_INTERVAL, ALERT_COOLDOWN, TELEGRAM_USER_ID
from bot.logger import setup_logger
from bot.handlers import (
    start, status, cmd_cpu, cmd_ram, cmd_disk, cmd_uptime, alerts_status, 
    help_command, graph_command, fix_disk, docker_ps, docker_logs, docker_restart,
    docker_download_logs, docker_tail_start, docker_tail_stop,
    list_hosts
)
from bot.alerts import check_alerts

logger = setup_logger()

async def setup_bot_commands(application):
    """
    Устанавливает список команд для бота.
    """
    commands = [
        BotCommand("start", "👋 Проверка доступа"),
        BotCommand("help", "❓ Справка"),
        BotCommand("hosts", "🌐 Список хостов"),
        BotCommand("status", "📊 Сводка (ВСЕ / ИМЯ)"),
        BotCommand("graph", "📈 График RAM (ВСЕ / ИМЯ)"),
        BotCommand("fix", "🩹 Ремонт диска (ВСЕ / ИМЯ)"),
        
        # ChatOps команды
        BotCommand("ps", "🐳 Список контейнеров (ВСЕ / ИМЯ)"),
        BotCommand("logs", "📋 Логи контейнера (ВСЕ / ИМЯ)"),
        BotCommand("dl_logs", "📥 Скачать логи (ВСЕ / ИМЯ)"),
        BotCommand("tail", "👀 Мониторинг логов (ВСЕ / ИМЯ)"),
        BotCommand("stop_tail", "🛑 Остановить мониторинг"),
        BotCommand("restart", "🔄 Рестарт контейнера (ВСЕ / ИМЯ)"),
        
        # Метрики
        BotCommand("cpu", "🖥 Загрузка CPU (ВСЕ / ИМЯ)"),
        BotCommand("ram", "🧠 Использование RAM (ВСЕ / ИМЯ)"),
        BotCommand("disk", "💾 Использование диска (ВСЕ / ИМЯ)"),
        BotCommand("uptime", "⏳ Время работы (ВСЕ / ИМЯ)"),
        BotCommand("alerts", "🚨 Статус алертов (ВСЕ / ИМЯ)"),
    ]
    
    await application.bot.set_my_commands(commands)
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("Bot commands and menu button updated.")

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

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.post_init = setup_bot_commands
    application.post_shutdown = lambda app: logger.info("Bot shutdown.")

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("hosts", list_hosts))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("graph", graph_command))
    application.add_handler(CommandHandler("fix", fix_disk))
    
    # ChatOps обработчики
    application.add_handler(CommandHandler("ps", docker_ps))
    application.add_handler(CommandHandler("logs", docker_logs))
    application.add_handler(CommandHandler("dl_logs", docker_download_logs))
    application.add_handler(CommandHandler("tail", docker_tail_start))
    application.add_handler(CommandHandler("stop_tail", docker_tail_stop))
    application.add_handler(CommandHandler("restart", docker_restart))
    
    # Метрики
    application.add_handler(CommandHandler("cpu", cmd_cpu))
    application.add_handler(CommandHandler("ram", cmd_ram))
    application.add_handler(CommandHandler("disk", cmd_disk))
    application.add_handler(CommandHandler("uptime", cmd_uptime))
    application.add_handler(CommandHandler("alerts", alerts_status))

    # Добавляем задачу в очередь (JobQueue)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(alarm_job, interval=CHECK_INTERVAL, first=10, data=TELEGRAM_USER_ID)
    else:
        logger.error("JobQueue is not initialized.")

    logger.info("Bot started successfully.")
    application.run_polling()

if __name__ == "__main__":
    main()