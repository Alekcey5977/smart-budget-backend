#!/usr/bin/env python3
"""
Скрипт для генерации тестовых данных для сервиса изображений.
Создает JSON файл с ~50 записями: аватарки, категории, мерчанты.
"""

import json
import base64
from typing import List, Dict


def create_avatar_svg(color: str, letter: str) -> str:
    """Создать SVG аватарку с цветным фоном и буквой"""
    return f'''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
  <circle cx="100" cy="100" r="100" fill="{color}"/>
  <text x="100" y="130" font-size="80" fill="white" text-anchor="middle" font-family="Arial">{letter}</text>
</svg>'''


def create_category_icon_svg(emoji: str, color: str) -> str:
    """Создать SVG иконку категории с эмодзи"""
    return f'''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
  <circle cx="100" cy="100" r="100" fill="{color}"/>
  <text x="100" y="130" font-size="80" fill="white" text-anchor="middle">{emoji}</text>
</svg>'''


def create_merchant_logo_svg(name: str, bg_color: str, text_color: str = "white") -> str:
    """Создать простой SVG логотип мерчанта"""
    return f'''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="200" height="200" fill="{bg_color}"/>
  <text x="100" y="110" font-size="24" fill="{text_color}" text-anchor="middle" font-family="Arial" font-weight="bold">{name}</text>
</svg>'''


def generate_test_data() -> List[Dict]:
    """Генерация всех тестовых данных"""
    test_data = []

    # 10 предустановленных аватарок
    avatars = [
        ("blue", "#3B82F6", "A"),
        ("green", "#10B981", "B"),
        ("red", "#EF4444", "C"),
        ("purple", "#8B5CF6", "D"),
        ("orange", "#F59E0B", "E"),
        ("pink", "#EC4899", "F"),
        ("cyan", "#06B6D4", "G"),
        ("indigo", "#6366F1", "H"),
        ("lime", "#84CC16", "I"),
        ("teal", "#14B8A6", "J"),
    ]

    for idx, (name, color, letter) in enumerate(avatars, 1):
        svg_content = create_avatar_svg(color, letter)
        test_data.append({
            "entity_type": "user_avatar",
            "entity_id": None,
            "mime_type": "image/svg+xml",
            "is_default": True,
            "file_data_svg": svg_content,
            "description": f"Предустановленная аватарка {name}"
        })

    # 20 категорий с иконками
    categories = [
        ("1", "🛒", "#10B981", "Продукты"),
        ("2", "🚗", "#3B82F6", "Транспорт"),
        ("3", "🎬", "#EC4899", "Развлечения"),
        ("4", "💊", "#EF4444", "Здоровье"),
        ("5", "📚", "#8B5CF6", "Образование"),
        ("6", "👕", "#F59E0B", "Одежда"),
        ("7", "🍽️", "#F97316", "Рестораны"),
        ("8", "⚽", "#06B6D4", "Спорт"),
        ("9", "💻", "#6366F1", "Электроника"),
        ("10", "🏠", "#84CC16", "Дом"),
        ("11", "✈️", "#0EA5E9", "Путешествия"),
        ("12", "💄", "#DB2777", "Красота"),
        ("13", "🎁", "#DC2626", "Подарки"),
        ("14", "🐾", "#D97706", "Питомцы"),
        ("15", "📱", "#7C3AED", "Связь"),
        ("16", "💰", "#059669", "Финансы"),
        ("17", "💡", "#FBBF24", "Коммунальные услуги"),
        ("18", "☂️", "#2563EB", "Страхование"),
        ("19", "🎨", "#9333EA", "Хобби"),
        ("20", "❤️", "#BE123C", "Благотворительность"),
    ]

    for category_id, emoji, color, description in categories:
        svg_content = create_category_icon_svg(emoji, color)
        test_data.append({
            "entity_type": "category",
            "entity_id": category_id,
            "mime_type": "image/svg+xml",
            "is_default": True,
            "file_data_svg": svg_content,
            "description": f"Иконка категории: {description}"
        })

    # 20 мерчантов с логотипами
    merchants = [
        ("1", "Пятёрочка", "#DC2626", "white"),
        ("2", "Магнит", "#DC2626", "white"),
        ("3", "Перекрёсток", "#10B981", "white"),
        ("4", "Лента", "#F59E0B", "white"),
        ("5", "Ашан", "#EF4444", "white"),
        ("6", "McDonald's", "#FBBF24", "#DC2626"),
        ("7", "KFC", "#DC2626", "white"),
        ("8", "Burger King", "#F97316", "white"),
        ("9", "Яндекс Такси", "#FBBF24", "black"),
        ("10", "Uber", "black", "white"),
        ("11", "Ozon", "#3B82F6", "white"),
        ("12", "Wildberries", "#A855F7", "white"),
        ("13", "AliExpress", "#EF4444", "white"),
        ("14", "Сбербанк", "#10B981", "white"),
        ("15", "Тинькофф", "#FBBF24", "black"),
        ("16", "Спортмастер", "#3B82F6", "white"),
        ("17", "Decathlon", "#2563EB", "white"),
        ("18", "Читай-город", "#F97316", "white"),
        ("19", "М.Видео", "#DC2626", "white"),
        ("20", "Эльдорадо", "#FBBF24", "#DC2626"),
    ]

    for merchant_id, name, bg_color, text_color in merchants:
        svg_content = create_merchant_logo_svg(name, bg_color, text_color)
        test_data.append({
            "entity_type": "merchant",
            "entity_id": merchant_id,
            "mime_type": "image/svg+xml",
            "is_default": True,
            "file_data_svg": svg_content,
            "description": f"Логотип мерчанта: {name}"
        })

    return test_data


def main():
    """Главная функция"""
    print("Generating test data for Images Service...")

    test_data = generate_test_data()

    # Сохранение в JSON файл
    output_file = "images_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)

    print(f"[OK] Created {len(test_data)} records")
    print(f"[OK] File saved: {output_file}")
    print("\nDistribution by type:")
    print(f"  - Avatars: 10")
    print(f"  - Categories: 20")
    print(f"  - Merchants: 20")


if __name__ == "__main__":
    main()
