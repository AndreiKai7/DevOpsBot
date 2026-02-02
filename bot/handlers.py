from telegram import Update
from telegram.ext import ContextTypes
from bot.config import is_authorized, TELEGRAM_USER_ID
from bot.logger import setup_logger
from bot.metrics import get_cpu_usage, get_load_avg, get_ram_usage, get_disk_usage, get_uptime
from bot.graphs import create_pie_chart
import subprocess
import socket  # <--- Добавляем импорт socket

logger = setup_logger()

# Определяем имя сервера один раз при старте скрипта
HOSTNAME = socket.gethostname()

async def check_access(update: Update) -> bool:
    """ Middleware для проверки доступа."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Access Denied. You are not authorized.")
        logger.warning(f"Unauthorized access attempt from ID: {user_id}")
        return False
    return True

async def send_server_message(update: Update, text: str, **kwargs):
    """
    Вспомогательная функция: отправляет сообщение, автоматически добавляя имя сервера.
    Используется для всех команд мониторинга.
    """
    header = f"🖥️ *Server: {HOSTNAME}*\n\n"
    await update.message.reply_text(header + text, **kwargs)

# --- Команды БЕЗ имени сервера (общие для всех инстансов) ---

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
        "🔹 /start - Проверка доступа и запуск бота\n"
        "🔹 /help - Показать это сообщение\n\n"
        
        "📊 *Мониторинг & Визуализация:*\n"
        "🔹 /status - Общая сводка состояния сервера\n"
        "🔹 /graph - 📈 График использования RAM\n"
        "🔹 /alerts - Статус активных аномалий\n\n"
        
        "🤖 *ChatOps (Управление Docker):*\n"
        "🔹 /ps - 🐳 Список запущенных контейнеров\n"
        "🔹 /logs <name> - 📋 Логи контейнера (последние 20 строк)\n"
        "🔹 /restart <name> - 🔄 Перезагрузка контейнера\n"  # <--- ДОБАВИЛИ ЭТО
        "🔹 /fix - 🩹 Авто-ремонт (очистка кэша, если диск переполнен)\n\n"
        
        "📈 *Точные метрики:*\n"
        "🔹 /cpu - Загрузка процессора\n"
        "🔹 /ram - Использование оперативной памяти\n"
        "🔹 /disk - Использование дискового пространства\n"
        "🔹 /uptime - Время работы сервера\n\n"
        
        "💡 *Совет:* Нажмите на кнопку меню (☰) слева от поля ввода для быстрого доступа к командам."
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested help.")

# --- Команды С ИМЕНЕМ СЕРВЕРА (используем send_server_message) ---

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return

    cpu = get_cpu_usage()
    load = get_load_avg()
    ram = get_ram_usage()
    disk = get_disk_usage()
    uptime = get_uptime()

    text = (
        f"📊 *Status*\n\n"
        f"🖥 CPU: {cpu}%\n"
        f"⚖ Load: {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}\n"
        f"🧠 RAM: {ram['used_gb']:.2f}GB / {ram['total_gb']:.2f}GB ({ram['percent']}%)\n"
        f"💾 Disk: {disk['used_gb']:.2f}GB / {disk['total_gb']:.2f}GB ({disk['percent']}%)\n"
        f"⏳ Uptime: {uptime}"
    )
    # Используем хелпер
    await send_server_message(update, text, parse_mode="Markdown")

async def graph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return

    await update.message.reply_text("📊 Generating chart... please wait.")
    
    try:
        image_buffer = create_pie_chart()
        
        # Имя сервера добавляем в caption (подпись к фото)
        caption = f"💾 Memory Usage for *{HOSTNAME}*"
        
        await update.message.reply_photo(
            photo=image_buffer,
            caption=caption,
            parse_mode="Markdown"
        )
        logger.info("Graph sent successfully.")
    except Exception as e:
        logger.error(f"Error generating graph: {e}")
        await update.message.reply_text("❌ Failed to generate graph.")

async def docker_ps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            # Отправляем список контейнеров с заголовком сервера
            await send_server_message(update, f"🐳 *Docker Containers:*\n```\n{result.stdout}\n```", parse_mode="Markdown")
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
    
    try:
        result = subprocess.run(['docker', 'logs', '--tail', '20', container_name], 
                                capture_output=True, text=True)
        
        await send_server_message(update, f"📋 *Logs for {container_name}:*\n```\n{result.stdout}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch logs: {e}")

async def docker_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    if not context.args:
        await update.message.reply_text("Usage: /restart <container_name>")
        return

    container_name = context.args[0]
    
    await update.message.reply_text(f"🔄 Restarting container *{container_name}*...", parse_mode="Markdown")

    try:
        # Запускаем рестарт
        result = subprocess.run(['docker', 'restart', container_name], 
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            # Если код возврата 0, значит команда прошла успешно
            await send_server_message(update, f"✅ Container *{container_name}* restarted successfully!")
        else:
            await update.message.reply_text(f"❌ Failed to restart. Error: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def fix_disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    disk = get_disk_usage()
    if disk['percent'] < 90:
        await update.message.reply_text("✅ Disk usage is normal. No action needed.")
        return

    await update.message.reply_text(
        f"⚠️ Disk is critical ({disk['percent']}%). Attempting to clean Docker cache...\n"
        f"Running: `docker system prune -f`"
    )

    try:
        result = subprocess.run(['docker', 'system', 'prune', '-f'], capture_output=True, text=True)
        
        if result.returncode == 0:
            new_disk = get_disk_usage()
            await send_server_message(update, f"✅ Cleanup complete!\nNew disk usage: {new_disk['percent']}%")
        else:
            await update.message.reply_text("❌ Cleanup failed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_cpu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    await send_server_message(update, f"🖥 CPU Usage: {get_cpu_usage()}%")

async def cmd_ram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    ram = get_ram_usage()
    await send_server_message(update, f"🧠 RAM: {ram['percent']}% ({ram['used_gb']:.2f}GB used)")

async def cmd_disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    disk = get_disk_usage()
    await send_server_message(update, f"💾 Disk: {disk['percent']}% ({disk['used_gb']:.2f}GB used)")

async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    await send_server_message(update, f"⏳ Server Uptime: {get_uptime()}")

async def alerts_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    from bot.alerts import check_alerts
    
    alert_msg = check_alerts(cooldown=0) 
    
    if alert_msg:
        await send_server_message(update, f"🚨 *Active Alerts:* \n\n{alert_msg}", parse_mode="Markdown")
    else:
        await send_server_message(update, "✅ No active alerts at the moment.")