from telegram import Update
from telegram.ext import ContextTypes
from bot.config import is_authorized, TELEGRAM_USER_ID
from bot.logger import setup_logger
from bot.metrics import get_cpu_usage, get_load_avg, get_ram_usage, get_disk_usage, get_uptime
from bot.graphs import create_pie_chart
import subprocess

logger = setup_logger()

async def check_access(update: Update) -> bool:
    """ Middleware для проверки доступа."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Access Denied. You are not authorized.")
        logger.warning(f"Unauthorized access attempt from ID: {user_id}")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    await update.message.reply_text(
        f"👋 Hello! Access granted.\n"
        f"Your ID: {TELEGRAM_USER_ID}\n"
        f"Use /status to check server health."
    )
    logger.info(f"User {update.effective_user.id} started the bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку по командам."""
    if not await check_access(update): return

    help_text = (
        "🤖 *Доступные команды:*\n\n"
        "🔹 /start - Проверить доступ и запустить бота\n"
        "🔹 /help - Показать это сообщение\n"
        "🔹 /status - Общая сводка состояния сервера\n"
        "🔹 /cpu - Загрузка процессора\n"
        "🔹 /ram - Использование оперативной памяти\n"
        "🔹 /disk - Использование дискового пространства\n"
        "🔹 /uptime - Время работы сервера\n"
        "🔹 /alerts - Статус активных предупреждений\n\n"
        "💡 *Совет:* Нажмите на кнопку меню слева от поля ввода для быстрого доступа к командам."
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested help.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return

    cpu = get_cpu_usage()
    load = get_load_avg()
    ram = get_ram_usage()
    disk = get_disk_usage()
    uptime = get_uptime()

    text = (
        f"📊 *Server Status*\n\n"
        f"🖥 CPU: {cpu}%\n"
        f"⚖ Load: {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}\n"
        f"🧠 RAM: {ram['used_gb']:.2f}GB / {ram['total_gb']:.2f}GB ({ram['percent']}%)\n"
        f"💾 Disk: {disk['used_gb']:.2f}GB / {disk['total_gb']:.2f}GB ({disk['percent']}%)\n"
        f"⏳ Uptime: {uptime}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def graph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return

    await update.message.reply_text("📊 Generating chart... please wait.")
    
    try:
        # Генерируем картинку (это может занять время, в идеале вынести в executor, но пока так)
        image_buffer = create_pie_chart()
        
        # Отправляем фото прямо из буфера памяти
        await update.message.reply_photo(
            photo=image_buffer,
            caption="💾 Current Memory Usage Visualization"
        )
        logger.info("Graph sent successfully.")
    except Exception as e:
        logger.error(f"Error generating graph: {e}")
        await update.message.reply_text("❌ Failed to generate graph.")

async def docker_ps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    # Запускаем docker ps как будто мы в консоли
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            # Форматируем моноширинным шрифтом для красоты
            await update.message.reply_text(f"```\n{result.stdout}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Error executing docker ps")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def docker_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    if not context.args:
        await update.message.reply_text("Usage: /logs <container_name>")
        return

    container_name = context.args[0]
    
    # Берем последние 20 строк логов
    try:
        result = subprocess.run(['docker', 'logs', '--tail', '20', container_name], 
                                capture_output=True, text=True)
        
        # Логи могут быть длинными, но Телеграм вывозит
        await update.message.reply_text(f"📋 *Logs for {container_name}:*\n```\n{result.stdout}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch logs: {e}")

async def fix_disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    # Проверяем статус
    disk = get_disk_usage()
    if disk['percent'] < 90:
        await update.message.reply_text("✅ Disk usage is normal. No action needed.")
        return

    await update.message.reply_text(
        f"⚠️ Disk is critical ({disk['percent']}%). Attempting to clean Docker cache...\n"
        f"Running: `docker system prune -f`"
    )

    try:
        # Запускаем очистку
        result = subprocess.run(['docker', 'system', 'prune', '-f'], capture_output=True, text=True)
        
        if result.returncode == 0:
            new_disk = get_disk_usage()
            await update.message.reply_text(
                f"✅ Cleanup complete!\n"
                f"Space reclaimed. New disk usage: {new_disk['percent']}%"
            )
        else:
            await update.message.reply_text("❌ Cleanup failed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_cpu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    await update.message.reply_text(f"🖥 CPU Usage: {get_cpu_usage()}%")

async def cmd_ram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    ram = get_ram_usage()
    await update.message.reply_text(f"🧠 RAM: {ram['percent']}% ({ram['used_gb']:.2f}GB used)")

async def cmd_disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    disk = get_disk_usage()
    await update.message.reply_text(f"💾 Disk: {disk['percent']}% ({disk['used_gb']:.2f}GB used)")

async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    await update.message.reply_text(f"⏳ Server Uptime: {get_uptime()}")

async def alerts_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    # Проверяем текущее состояние алертов
    from bot.alerts import check_alerts
    # Передаем 0 cooldown, чтобы просто проверить, не нарушая таймеры отправки
    alert_msg = check_alerts(cooldown=0) 
    
    if alert_msg:
        # Вручную подменяем текст, так как check_alerts с 0 вернет сообщение, но мы не хотим обновлять время
        await update.message.reply_text(f"🚨 *Active Alerts Detected:* \n\n{alert_msg}", parse_mode="Markdown")
    else:
        await update.message.reply_text("✅ No active alerts at the moment.")