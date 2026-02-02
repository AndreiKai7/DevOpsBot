import subprocess
import socket
import io
import os
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import is_authorized, TELEGRAM_USER_ID
from bot.logger import setup_logger
from bot.metrics import get_cpu_usage, get_load_avg, get_ram_usage, get_disk_usage, get_uptime
from bot.graphs import create_pie_chart

logger = setup_logger()

# Определяем имя сервера один раз при старте скрипта
HOSTNAME = socket.gethostname()

# Определяем IP сервера
# Приоритет за переменной окружения (.env), если нет - ставим "Unknown"
SERVER_IP = os.getenv("SERVER_IP", "Unknown")

# Если IP не задан в .env, можно попробовать угадать (но часто это будет IP контейнера)
if SERVER_IP == "Unknown":
    logger.warning("SERVER_IP is not set in .env. Trying to auto-detect (might be container IP)...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        SERVER_IP = s.getsockname()[0]
        s.close()
    except Exception:
        pass

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
    Вспомогательная функция: отправляет сообщение, автоматически добавляя имя сервера и IP.
    Используется для всех команд мониторинга.
    """
    # Выводим как: Server: DB-Server (192.168.1.50)
    header = f"🖥️ *Server: {HOSTNAME} ({SERVER_IP})*\n\n"
    await update.message.reply_text(header + text, **kwargs)

def check_target(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет, предназначена ли команда этому серверу.
    Логика:
    - Если аргументов нет -> Команда для ВСЕХ (return True).
    - Если первый аргумент совпадает с HOSTNAME -> Команда для НАС (return True).
    - Иначе -> Команда не для нас (return False).
    """
    if context.args:
        target_host = context.args[0]
        return target_host == HOSTNAME
    return True

# --- Команды БЕЗ имени сервера (общие) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    await update.message.reply_text(
        f"👋 Hello! Access granted.\n"
        f"Your ID: {TELEGRAM_USER_ID}\n"
        f"Use /status to check server health."
    )
    logger.info(f"User {update.effective_user.id} started the bot.")

async def list_hosts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда обнаружения: каждый сервер в чате отзовется своим именем и IP.
    """
    if not await check_access(update): return
    await update.message.reply_text(f"🖥️ Host Online: *{HOSTNAME}* IP: `{SERVER_IP}`", parse_mode="Markdown")
    logger.info(f"Host {HOSTNAME} responded to /hosts")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку по командам."""
    if not await check_access(update): return

    help_text = (
        "🤖 *Доступные команды:*\n\n"
        "🔹 /start - Проверка доступа и запуск бота\n"
        "🔹 /help - Показать это сообщение\n"
        "🔹 /hosts - 🌐 Показать список активных серверов\n\n"
        
        "📊 *Мониторинг (Один или Все):*\n"
        "🔹 /status - Сводка (если пусто - ВСЕ, если /status server-1 - точечно)\n"
        "🔹 /cpu - Загрузка процессора\n"
        "🔹 /ram - Использование памяти\n"
        "🔹 /disk - Использование дискового пространства\n"
        "🔹 /uptime - Время работы сервера\n\n"
        
        "🤖 *ChatOps (Управление Docker):*\n"
        "🔹 /ps - 🐳 Список контейнеров\n"
        "🔹 /logs <name> - 📋 Логи контейнера (последние 20 строк)\n"
        "🔹 /dl_logs <name> - 📥 Скачать файл логов (без сохранения на диск)\n"
        "🔹 /tail <name> - 👀 Мониторинг в реальном времени\n"
        "🔹 /stop_tail - 🛑 Остановить мониторинг\n"
        "🔹 /restart <name> - 🔄 Перезагрузка контейнера\n"
        "🔹 /fix - 🩹 Авто-ремонт (очистка кэша)\n\n"
        
        "📈 *Визуализация:*\n"
        "🔹 /graph - 📈 График использования RAM\n"
        "🔹 /alerts - Статус активных аномалий\n\n"
        
        "💡 *Пример:* `/logs server-1 nginx` покажет логи nginx только на server-1."
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested help.")

# --- Команды С ИМЕНЕМ СЕРВЕРА (используем send_server_message) ---

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return

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
    await send_server_message(update, text, parse_mode="Markdown")

async def graph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return

    await update.message.reply_text("📊 Generating chart... please wait.")
    
    try:
        image_buffer = create_pie_chart()
        # Добавляем IP в подпись к фото
        caption = f"💾 Memory Usage for *{HOSTNAME}* ({SERVER_IP})"
        
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
    if not check_target(context): return
    
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            await send_server_message(update, f"🐳 *Docker Containers:*\n```\n{result.stdout}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Error executing docker ps")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def docker_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return
    
    container_name = ""
    if len(context.args) >= 2:
        # Формат: /logs server-1 nginx
        container_name = context.args[1]
    elif len(context.args) == 1:
        # Формат: /logs nginx
        container_name = context.args[0]
    else:
        await update.message.reply_text("Usage: /logs <container_name> or /logs <hostname> <container_name>")
        return
    
    try:
        result = subprocess.run(['docker', 'logs', '--tail', '20', container_name], 
                                capture_output=True, text=True)
        await send_server_message(update, f"📋 *Logs for {container_name}:*\n```\n{result.stdout}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch logs: {e}")

async def docker_download_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return
    
    container_name = ""
    if len(context.args) >= 2:
        container_name = context.args[1]
    elif len(context.args) == 1:
        container_name = context.args[0]
    else:
        await update.message.reply_text("Usage: /dl_logs <container_name> or /dl_logs <hostname> <container_name>")
        return

    await update.message.reply_text(f"📥 Downloading logs for *{container_name}* (last 2000 lines)...", parse_mode="Markdown")
    
    try:
        result = subprocess.run(['docker', 'logs', '--tail', '2000', container_name], 
                                capture_output=True, text=True)
        
        if result.returncode != 0:
            await update.message.reply_text(f"❌ Error: {result.stderr}")
            return

        log_data = io.BytesIO(result.stdout.encode('utf-8'))
        log_data.name = f"{HOSTNAME}_{container_name}_logs.txt"
        
        await update.message.reply_document(
            document=log_data,
            caption=f"📂 Logs for *{container_name}* (Server: {HOSTNAME}) generated in memory.", 
            filename=log_data.name,
            parse_mode="Markdown"
        )
        logger.info(f"User downloaded logs for {container_name}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to generate file: {e}")

async def docker_tail_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return
    
    container_name = ""
    if len(context.args) >= 2:
        container_name = context.args[1]
    elif len(context.args) == 1:
        container_name = context.args[0]
    else:
        await update.message.reply_text("Usage: /tail <container_name> or /tail <hostname> <container_name>")
        return
    
    user_id = update.effective_user.id
    job_name = f"tail_{user_id}"
    
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    if current_jobs:
        await update.message.reply_text(f"⚠️ You are already monitoring `{container_name}`. Use /stop_tail to stop.")
        return

    await update.message.reply_text(f"👀 Started watching logs for *{container_name}*.\nI will update you every 10s.", parse_mode="Markdown")
    
    # Запускаем фоновую задачу. Передаем HOSTNAME чтобы коллбек знал откуда логи
    context.job_queue.run_repeating(
        callback=tail_callback,
        interval=10, 
        first=5,
        data={"name": container_name, "user_id": user_id, "hostname": HOSTNAME},
        name=job_name
    )

async def tail_callback(context: ContextTypes.DEFAULT_TYPE):
    """Функция, которая вызывается каждые 10 секунд."""
    job_data = context.job.data
    container_name = job_data['name']
    current_hostname = job_data['hostname']
    
    result = subprocess.run(['docker', 'logs', '--since', '10s', container_name], 
                            capture_output=True, text=True)
    
    if result.stdout:
        try:
            # Добавляем HOSTNAME в сообщение логов
            text = (
                f"📝 *{current_hostname}* | Logs for `{container_name}`:\n"
                f"```\n{result.stdout[:3000]}\n```"
            )
            await context.bot.send_message(
                chat_id=job_data['user_id'],
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send tail update: {e}")

async def docker_tail_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Останавливает мониторинг."""
    if not await check_access(update): return
    
    user_id = update.effective_user.id
    job_name = f"tail_{user_id}"
    
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    if current_jobs:
        current_jobs[0].schedule_removal()
        await update.message.reply_text("✅ Stopped watching logs.")
    else:
        await update.message.reply_text("ℹ️ No active monitoring found.")

async def docker_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return
    
    container_name = ""
    if len(context.args) >= 2:
        container_name = context.args[1]
    elif len(context.args) == 1:
        container_name = context.args[0]
    else:
        await update.message.reply_text("Usage: /restart <container_name> or /restart <hostname> <container_name>")
        return
    
    await update.message.reply_text(f"🔄 Restarting container *{container_name}*...", parse_mode="Markdown")

    try:
        result = subprocess.run(['docker', 'restart', container_name], 
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            await send_server_message(update, f"✅ Container *{container_name}* restarted successfully!")
        else:
            await update.message.reply_text(f"❌ Failed to restart. Error: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def fix_disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return
    
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
    if not check_target(context): return
    await send_server_message(update, f"🖥 CPU Usage: {get_cpu_usage()}%")

async def cmd_ram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return
    ram = get_ram_usage()
    await send_server_message(update, f"🧠 RAM: {ram['percent']}% ({ram['used_gb']:.2f}GB used)")

async def cmd_disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return
    disk = get_disk_usage()
    await send_server_message(update, f"💾 Disk: {disk['percent']}% ({disk['used_gb']:.2f}GB used)")

async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return
    await send_server_message(update, f"⏳ Server Uptime: {get_uptime()}")

async def alerts_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not check_target(context): return
    from bot.alerts import check_alerts
    
    alert_msg = check_alerts(cooldown=0) 
    
    if alert_msg:
        await send_server_message(update, f"🚨 *Active Alerts:* \n\n{alert_msg}", parse_mode="Markdown")
    else:
        await send_server_message(update, "✅ No active alerts at the moment.")