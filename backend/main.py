from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse
import shutil
import sqlite3
from typing import List, Optional
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "warehouse.db"
STATIC_DIR = BASE_DIR / "static"
IMG_DIR = STATIC_DIR / "img"

app = FastAPI(
    title="Склад",
    description="Сервер для учета хранимых предметов на объекте",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class Item(BaseModel):
    name: str = Field(min_length=2, max_length=250)
    storage_sector: int = Field(gt=0)
    weight: float = Field(ge=0)
    quantity: int = Field(gt=0)
    is_dangerous: bool = False
    image_url: str | None = None

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    storage_sector: Optional[int] = None
    weight: Optional[float] = None
    quantity: Optional[int] = None
    is_dangerous: Optional[bool] = None
    image_url: Optional[str] = None

# Контекстный менеджер для подключения к БД
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Функция для форматирования строки БД в словарь
def format_db_row(row):
    return dict(row) if row else None

def format_db_rows(rows):
    return [dict(row) for row in rows]

# Инициализация базы данных
def init_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Создание таблицы товаров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                storage_sector INTEGER NOT NULL,
                weight REAL NOT NULL,
                quantity INTEGER NOT NULL,
                is_dangerous INTEGER NOT NULL DEFAULT 0,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создание таблицы корзины пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_carts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE,
                UNIQUE(user_id, item_id)
            )
        ''')
        
        # Создание индексов для ускорения запросов
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_sector ON items(storage_sector)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cart_user ON user_carts(user_id)')

# Вызываем инициализацию при запуске
init_database()

# Эндпоинты
@app.get("/items", tags=["Товары"])
def get_all_items():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM items ORDER BY id')
        rows = cursor.fetchall()
        return format_db_rows(rows)

@app.get("/items/search", tags=["Просмотр"])
def search_items(name: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM items 
            WHERE name LIKE ? 
            ORDER BY name
        ''', (f'%{name}%',))
        rows = cursor.fetchall()
        return format_db_rows(rows)

@app.get("/items/count", tags=["Аналитика"])
def get_count():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as total FROM items')
        result = cursor.fetchone()
        return {"total": result['total']}

@app.get("/items/dangerous", tags=["Аналитика"])
def get_dangerous_items():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM items WHERE is_dangerous = 1')
        rows = cursor.fetchall()
        return format_db_rows(rows)

@app.get("/items/{item_id}", tags=["Просмотр"])
def get_one_item(item_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM items WHERE id = ?', (item_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Предмет с таким Id не найден")
        return format_db_row(row)

@app.post("/items", tags=["Редактирование"], status_code=201)
async def create_item(
    name: str = Form(...),
    storage_sector: int = Form(...),
    weight: float = Form(0.0),
    quantity: int = Form(...),
    is_dangerous: bool = Form(False),
    image_file: UploadFile = File(None),
):
    # Обработка изображения
    image_url = None
    if image_file and image_file.filename:
        IMG_DIR.mkdir(parents=True, exist_ok=True)

        file_path = IMG_DIR / image_file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        image_url = f"/static/img/{image_file.filename}"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO items (name, storage_sector, weight, quantity, is_dangerous, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, storage_sector, weight, quantity, int(is_dangerous), image_url))
        
        new_id = cursor.lastrowid
        
        # Возвращаем созданный предмет
        cursor.execute('SELECT * FROM items WHERE id = ?', (new_id,))
        new_item = cursor.fetchone()
        return format_db_row(new_item)

@app.put("/items/{item_id}", tags=["Администрирование"])
def update_item(item_id: int, updated_item: Item):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем существует ли предмет
        cursor.execute('SELECT id FROM items WHERE id = ?', (item_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Невозможно обновить: предмет не найден")
        
        # Обновляем
        cursor.execute('''
            UPDATE items 
            SET name = ?, storage_sector = ?, weight = ?, quantity = ?, is_dangerous = ?, image_url = ?
            WHERE id = ?
        ''', (updated_item.name, updated_item.storage_sector, updated_item.weight, 
              updated_item.quantity, int(updated_item.is_dangerous), updated_item.image_url, item_id))
        
        # Возвращаем обновленный предмет
        cursor.execute('SELECT * FROM items WHERE id = ?', (item_id,))
        updated = cursor.fetchone()
        return {"message": "Данные обновлены", "item": format_db_row(updated)}

@app.patch("/items/{item_id}", tags=["Администрирование"])
def patch_item(item_id: int, updated_item: ItemUpdate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем существует ли предмет
        cursor.execute('SELECT * FROM items WHERE id = ?', (item_id,))
        current = cursor.fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Предмет не найден")
        
        current_dict = dict(current)
        
        # Обновляем только переданные поля
        update_data = updated_item.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == 'is_dangerous' and value is not None:
                current_dict[key] = int(value)
            elif value is not None:
                current_dict[key] = value
        
        cursor.execute('''
            UPDATE items 
            SET name = ?, storage_sector = ?, weight = ?, quantity = ?, is_dangerous = ?, image_url = ?
            WHERE id = ?
        ''', (current_dict['name'], current_dict['storage_sector'], current_dict['weight'],
              current_dict['quantity'], current_dict['is_dangerous'], current_dict['image_url'], item_id))
        
        cursor.execute('SELECT * FROM items WHERE id = ?', (item_id,))
        updated = cursor.fetchone()
        return {"message": "Данные обновлены", "item": format_db_row(updated)}

@app.delete("/items/{item_id}", tags=["Администрирование"])
def delete_item(item_id: int, confirm: bool = False):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Получаем информацию о предмете
        cursor.execute('SELECT name, is_dangerous FROM items WHERE id = ?', (item_id,))
        item = cursor.fetchone()
        
        if not item:
            raise HTTPException(status_code=404, detail="Предмет не найден")
        
        # Проверка на опасный товар
        if item['is_dangerous'] == 1 and not confirm:
            raise HTTPException(status_code=403, detail="Опасный товар. Подтвердите удаление")
        
        # Удаляем предмет (каскадно удалятся связанные записи в корзине)
        cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
        
        return {"status": "success", "message": f"Предмет '{item['name']}' удален"}

# Эндпоинты для корзины
@app.post("/cart/add/{item_id}", tags=["Корзина"])
def add_to_cart(item_id: int, user_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем существует ли товар
        cursor.execute('SELECT id FROM items WHERE id = ?', (item_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Товар не найден")
        
        # Добавляем или обновляем количество в корзине
        cursor.execute('''
            INSERT INTO user_carts (user_id, item_id, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, item_id) 
            DO UPDATE SET quantity = quantity + 1
        ''', (user_id, item_id))
        
        # Получаем текущую корзину пользователя
        cursor.execute('''
            SELECT item_id, quantity FROM user_carts 
            WHERE user_id = ?
        ''', (user_id,))
        cart_items = cursor.fetchall()
        
        cart = {str(row['item_id']): row['quantity'] for row in cart_items}
        return {"status": "success", "cart": cart}

@app.get("/cart", tags=["Корзина"])
def get_my_cart(user_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT item_id, quantity FROM user_carts 
            WHERE user_id = ?
        ''', (user_id,))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            return {}
        
        # Получаем детальную информацию о товарах в корзине
        item_ids = [row['item_id'] for row in cart_items]
        placeholders = ','.join('?' * len(item_ids))
        cursor.execute(f'''
            SELECT * FROM items WHERE id IN ({placeholders})
        ''', item_ids)
        items = cursor.fetchall()
        
        items_dict = {item['id']: format_db_row(item) for item in items}
        
        cart = {
            str(row['item_id']): {
                "quantity": row['quantity'],
                "item": items_dict.get(row['item_id'])
            }
            for row in cart_items
        }
        
        return cart

@app.delete("/cart/remove/{item_id}", tags=["Корзина"])
def remove_from_cart(item_id: int, user_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM user_carts 
            WHERE user_id = ? AND item_id = ?
        ''', (user_id, item_id))
        
        return {"status": "success", "message": "Товар удален из корзины"}

@app.delete("/cart/clear", tags=["Корзина"])
def clear_cart(user_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_carts WHERE user_id = ?', (user_id,))
        return         {"status": "success", "message": "Корзина очищена"}

# Эндпоинт для получения статистики по секторам
@app.get("/analytics/sectors", tags=["Аналитика"])
def get_sector_stats():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT storage_sector, 
                   COUNT(*) as item_count,
                   SUM(quantity) as total_quantity
            FROM items 
            GROUP BY storage_sector
            ORDER BY storage_sector
        ''')
        rows = cursor.fetchall()
        return format_db_rows(rows)


FRONTEND_DIR = BASE_DIR.parent / "frontend"


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/{page_name}.html", include_in_schema=False)
def serve_frontend_page(page_name: str):
    return FileResponse(str(FRONTEND_DIR / f"{page_name}.html"))