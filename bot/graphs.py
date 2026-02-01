import matplotlib.pyplot as plt
import io
import psutil

# Говорим matplotlib, чтобы он не пытался открыть GUI (у нас сервер без монитора)
plt.switch_backend('Agg')

def create_pie_chart():
    """Создает график использования RAM и возвращает байты изображения."""
    mem = psutil.virtual_memory()
    
    # Данные для графика
    labels = [f'Used: {mem.percent}%', f'Free: {100-mem.percent}%']
    sizes = [mem.percent, 100 - mem.percent]
    colors = ['#ff6b6b', '#51cf66']
    explode = (0.1, 0) 

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, explode=explode, labels=labels, colors=colors,
           autopct='%1.1f%%', shadow=True, startangle=90)
    ax.axis('equal')  # Делает круг круглым
    
    plt.title(f"Memory Usage (Total: {mem.total/(1024**3):.1f} GB)")

    # Сохраняем картинку в оперативную память (BytesIO), а не в файл
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig) # Важно закрывать фигуру, чтобы не течь память
    return buf