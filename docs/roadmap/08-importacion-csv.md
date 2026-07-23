# 📥 Importación CSV

**Estado:** ⬜ Pendiente · **Prioridad:** Media · **Esfuerzo:** L (3+ días) · **Dependencias:** Ninguna

## Por qué
Poblar el historial desde estados de cuenta bancarios sin captura manual. Sin esto, migrar a la app implica semanas de datos perdidos o captura tediosa.

## Alcance
**Incluye:**
- Preview de CSV con mapeo sugerido de columnas y detección de duplicados.
- Commit en lote de las filas seleccionadas.
- Wizard de 3 pasos en frontend.

**No incluye:**
- Formatos distintos a CSV (OFX, QIF, Excel, PDF).
- Mapeo automático de categorías por descripción (reglas de clasificación).
- Importación recurrente/programada.

## Diseño propuesto
### Backend
- `POST /import/preview` (multipart CSV) → parsea y devuelve:
  - Filas detectadas con mapeo sugerido de columnas (fecha / monto / descripción) por heurística de headers y tipos de dato.
  - Posibles duplicados marcados: misma fecha + monto + nota que una transacción existente del hogar.
- `POST /import/commit` con el mapeo confirmado, `accountId` destino y las filas seleccionadas → bulk insert de transacciones (`type` inferido del signo del monto: negativo = `expense`, positivo = `income`).
- **Decisión recomendada**: crear una categoría default "Sin clasificar" por hogar para las filas importadas, en lugar de permitir `categoryId` null — mantiene invariantes del esquema y del summary.
- Límite de 1000 filas por importación (rechazar con error claro si se excede).
- Todo el commit dentro de una sola transacción de DB.
### Frontend
- Página `/importar` (entrada desde Ajustes y/o Movimientos) con wizard de 3 pasos:
  1. **Subir archivo**: input de archivo, selección de cuenta destino.
  2. **Revisar**: mapeo de columnas (editable), tabla de filas con checkboxes, duplicados pre-marcados para excluir.
  3. **Resultado**: conteo de importadas/omitidas, link a Movimientos.
- Estados de carga y error por paso (archivo inválido, columnas no detectables).
### Infra
- Sin cambios (parseo en memoria; no se guarda el CSV).

## Criterios de aceptación
- [ ] Un CSV de banco real importa N filas como transacciones con fecha, monto y nota correctas.
- [ ] Los duplicados se detectan en el preview y se pueden excluir con un checkbox global o por fila.
- [ ] Reintentar la misma importación no duplica transacciones (los duplicados aparecen marcados en el segundo intento).
- [ ] Un CSV con más de 1000 filas se rechaza con mensaje claro.
- [ ] Las transacciones importadas aparecen con categoría "Sin clasificar" y la cuenta destino elegida.
- [ ] Tests: parseo, detección de duplicados, commit idempotente, límite de filas.

## Notas
- Riesgo: formatos de fecha ambiguos (DD/MM vs MM/DD) — el mapeo en el paso 2 debe dejar elegir el formato explícitamente.
- Riesgo: montos con separadores de miles o moneda ("$1,234.56") — normalizar en el parseo.
- Decisión abierta: guardar un hash de fila (`date+amount+note`) para dedupe más robusto a futuro; para MVP alcanza con la comparación directa.
