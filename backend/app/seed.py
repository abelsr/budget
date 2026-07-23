"""Categorías por defecto que se copian a cada hogar nuevo."""

DEFAULT_CATEGORIES: list[dict] = [
    {"name": "Supermercado", "icon": "shopping-cart", "color": "#30b0c7", "type": "expense"},
    {"name": "Comida fuera", "icon": "utensils", "color": "#ff9f0a", "type": "expense"},
    {"name": "Transporte", "icon": "car", "color": "#0a84ff", "type": "expense"},
    {"name": "Vivienda", "icon": "house", "color": "#bf5af2", "type": "expense"},
    {"name": "Servicios", "icon": "zap", "color": "#ffd60a", "type": "expense"},
    {"name": "Salud", "icon": "heart-pulse", "color": "#ff375f", "type": "expense"},
    {"name": "Ocio", "icon": "gamepad-2", "color": "#ff6482", "type": "expense"},
    {"name": "Suscripciones", "icon": "repeat", "color": "#ac8e68", "type": "expense"},
    {"name": "Sueldo", "icon": "banknote", "color": "#30d158", "type": "income"},
    {"name": "Otros ingresos", "icon": "hand-coins", "color": "#64d2ff", "type": "income"},
]
