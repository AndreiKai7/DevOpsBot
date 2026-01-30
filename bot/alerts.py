import time
from bot.logger import setup_logger
from bot.metrics import get_cpu_usage, get_ram_usage, get_disk_usage

logger = setup_logger()

# Хранилище времени последнего алерта
last_alert_time = {
    "cpu": 0,
    "ram": 0,
    "disk": 0
}

def check_alerts(cooldown: int):
    """Проверяет метрики и возвращает сообщение, если порог превышен."""
    current_time = time.time()
    alerts = []

    # CPU Check
    cpu = get_cpu_usage()
    if cpu > 85 and (current_time - last_alert_time["cpu"] > cooldown):
        msg = f"🚨 ALERT: CPU > 85% (Current: {cpu}%)"
        alerts.append(msg)
        last_alert_time["cpu"] = current_time
        logger.warning(f"CPU Alert triggered: {cpu}%")

    # RAM Check
    ram = get_ram_usage()
    if ram["percent"] > 90 and (current_time - last_alert_time["ram"] > cooldown):
        msg = f"🚨 ALERT: RAM > 90% (Current: {ram['percent']:.1f}%)"
        alerts.append(msg)
        last_alert_time["ram"] = current_time
        logger.warning(f"RAM Alert triggered: {ram['percent']}%")

    # Disk Check
    disk = get_disk_usage()
    if disk["percent"] > 90 and (current_time - last_alert_time["disk"] > cooldown):
        msg = f"🚨 ALERT: Disk > 90% (Current: {disk['percent']:.1f}%)"
        alerts.append(msg)
        last_alert_time["disk"] = current_time
        logger.warning(f"Disk Alert triggered: {disk['percent']}%")

    return "\n".join(alerts) if alerts else None