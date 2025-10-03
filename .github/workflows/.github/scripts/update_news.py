import json
import os
from datetime import datetime

def update_website_news():
    """Обновляет новости на сайте при получении данных от бота"""
    
    # Файл для временного хранения новых новостей
    NEWS_TEMP_FILE = ".github/data/new_news.json"
    WEBSITE_NEWS_FILE = "news_data.json"  # Файл с новостями для сайта
    
    # Загружаем существующие новости сайта
    if os.path.exists(WEBSITE_NEWS_FILE):
        with open(WEBSITE_NEWS_FILE, 'r', encoding='utf-8') as f:
            website_news = json.load(f)
    else:
        website_news = []
    
    # Проверяем наличие новых новостей от бота
    if os.path.exists(NEWS_TEMP_FILE):
        with open(NEWS_TEMP_FILE, 'r', encoding='utf-8') as f:
            new_news = json.load(f)
        
        # Добавляем новые новости в начало списка
        for news_item in new_news:
            news_item['id'] = len(website_news) + 1
            news_item['added_to_site'] = datetime.now().isoformat()
            website_news.insert(0, news_item)
        
        # Сохраняем обновленные новости
        with open(WEBSITE_NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(website_news, f, ensure_ascii=False, indent=2)
        
        # Очищаем временный файл
        os.remove(NEWS_TEMP_FILE)
        
        print(f"✅ Добавлено {len(new_news)} новых новостей на сайт")
        return True
    
    print("ℹ️ Новых новостей для добавления нет")
    return False

if __name__ == "__main__":
    update_website_news()
