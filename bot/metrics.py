import psutil
import os
from datetime import datetime

def get_cpu_usage():
    """Загрузка CPU в %."""
    return psutil.cpu_percent(interval=1)

def get_load_avg():
    """Load Average (1, 5, 15 min)."""
    return os.getloadavg()

def get_ram_usage():
    """Использование RAM в % и ГБ."""
    mem = psutil.virtual_memory()
    return {
        "percent": mem.percent,
        "used_gb": mem.used / (1024 ** 3),
        "total_gb": mem.total / (1024 ** 3)
    }

def get_disk_usage():
    """Использование диска / в % и ГБ."""
    disk = psutil.disk_usage('/')
    return {
        "percent": disk.percent,
        "used_gb": disk.used / (1024 ** 3),
        "total_gb": disk.total / (1024 ** 3)
    }

def get_uptime():
    """Время работы сервера в человекочитаемом формате."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    return str(datetime.now() - boot_time).split('.')[0]