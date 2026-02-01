import psutil
import os
from datetime import datetime
from collections import deque
import statistics

from collections import deque
import statistics

# Храним последние 100 измерений
cpu_history = deque(maxlen=100)

def check_anomaly(current_cpu):
    cpu_history.append(current_cpu)
    
    if len(cpu_history) < 20:
        return False, "Not enough data"

    # Считаем среднее и стандартное отклонение (сигму)
    mean = statistics.mean(cpu_history)
    stdev = statistics.stdev(cpu_history)
    
    # Если текущее значение больше чем Среднее + 2*Сигма (правило 2-х сигм)
    threshold = mean + (2 * stdev)
    
    if current_cpu > threshold and current_cpu > 20: # Игнорируем idle-флуктуации
        return True, f"Anomaly! CPU {current_cpu}% > Norm {threshold:.1f}% (Avg: {mean:.1f}%)"
    
    return False, ""

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