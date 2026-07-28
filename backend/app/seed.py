"""Categorías por defecto que se copian a cada hogar nuevo.

Los colores siguen la paleta categórica validada de la guía de diseño
(docs/design-guidelines.md §4): ocho tonos en orden fijo, con separación
comprobada bajo daltonismo en modo claro y oscuro. Los gastos toman los
slots 1..8; los ingresos reinician la asignación porque nunca comparten
gráfica con los gastos.
"""

DEFAULT_CATEGORIES: list[dict] = [
    {"name": "Supermercado", "icon": "shopping-cart", "color": "#2563eb", "type": "expense"},
    {"name": "Comida fuera", "icon": "utensils", "color": "#ea580c", "type": "expense"},
    {"name": "Transporte", "icon": "car", "color": "#0d9488", "type": "expense"},
    {"name": "Vivienda", "icon": "house", "color": "#b77c05", "type": "expense"},
    {"name": "Servicios", "icon": "zap", "color": "#db2777", "type": "expense"},
    {"name": "Salud", "icon": "heart-pulse", "color": "#4d7c0f", "type": "expense"},
    {"name": "Ocio", "icon": "gamepad-2", "color": "#7c3aed", "type": "expense"},
    {"name": "Suscripciones", "icon": "repeat", "color": "#9a5b26", "type": "expense"},
    {"name": "Sueldo", "icon": "banknote", "color": "#0d9488", "type": "income"},
    {"name": "Otros ingresos", "icon": "hand-coins", "color": "#2563eb", "type": "income"},
]
