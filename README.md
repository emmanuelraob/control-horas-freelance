# Control de Horas Freelance

App de escritorio para Windows que lleva el control de horario laboral de forma **automática**: entrada, salida, almuerzo y merienda, detectando la actividad real de mouse y teclado — sin necesidad de marcar nada a mano. Calcula una calificación semanal de cumplimiento de horario (0-100) y muestra un dashboard con métricas detalladas.

> 🚧 Proyecto en construcción activa. Este README y los enlaces de descarga se van actualizando a medida que avanza el desarrollo.

## Características

- **Registro automático**: entrada, salida y pausas se detectan solas por inactividad de mouse/teclado (`GetLastInputInfo` de Windows). No hace falta apretar botones.
- **Popup de clasificación de pausas**: al superar el umbral de inactividad configurado (5 min por defecto), aparece un aviso no bloqueante con un contador en vivo y botones rápidos (Almuerzo / Merienda / Baño / Otra cosa). Responder es opcional.
- **Inferencia por horario**: si no se responde el popup, el sistema clasifica la pausa solo comparando el horario real contra las ventanas configuradas (ej. almuerzo entre 12:00 y 14:30).
- **Botones manuales de respaldo**: disponibles en el ícono de la bandeja del sistema para corregir o marcar algo a mano si hace falta.
- **Calificación semanal (0-100)**: puntualidad de entrada/salida, cumplimiento de almuerzo/merienda, horas trabajadas vs. esperadas, y ratio de actividad real.
- **Dashboard con métricas**: línea de tiempo diaria, heatmap tipo calendario, tendencia de score semanal, gráfico de horas trabajadas, KPIs (horas trabajadas, puntualidad, horas idle, pausas confirmadas vs. inferidas) y export a CSV — todo en HTML/CSS/JS sin dependencias externas (sin CDN, sin internet).
- **Autoarranque**: la app se registra sola para iniciar con el login de Windows y corre en la bandeja del sistema durante toda la jornada.
- **100% local**: todos los datos se guardan en un archivo SQLite en la propia máquina, sin enviar nada a servidores externos.

## Descarga

La última versión empaquetada (`.exe` para Windows, no requiere tener Python instalado) está disponible en:

**[github.com/emmanuelraob/control-horas-freelance/releases/latest](https://github.com/emmanuelraob/control-horas-freelance/releases/latest)**

*(Todavía no hay releases publicados — el primer `.exe` se sube cuando el flujo principal esté funcional de punta a punta.)*

## Instalación y uso

### Opción 1: ejecutable (recomendado para uso diario)
1. Descargá el `.exe` desde la sección [Descarga](#descarga).
2. Ejecutalo una vez — se registra automáticamente para iniciar con Windows y queda corriendo en la bandeja del sistema (junto al reloj, abajo a la derecha).
3. Click derecho en el ícono de la bandeja para configurar tu horario esperado (entrada, salida, ventana de almuerzo, ventanas de merienda) antes del primer uso.
4. A partir de ahí no hace falta hacer nada más: la app detecta sola entrada, salida y pausas. Cuando te alejás de la compu más del tiempo configurado, aparece un popup opcional para clasificar la pausa.
5. Click en "Ver Dashboard" desde el ícono de la bandeja para ver tus métricas.

### Opción 2: correr desde el código fuente (desarrollo)
```bash
git clone https://github.com/emmanuelraob/control-horas-freelance.git
cd control-horas-freelance
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
python control_horas/main.py
```

Requiere Windows (usa APIs nativas de `user32.dll` para detectar inactividad) y Python 3.11+.

## Capturas de pantalla

*(Se agregan a medida que las pantallas estén implementadas.)*

| Bandeja del sistema | Popup de pausa | Dashboard |
|---|---|---|
| _pendiente_ | _pendiente_ | _pendiente_ |

## Cómo funciona la calificación (0-100)

| Factor | Peso |
|---|---|
| Puntualidad de entrada | 25% |
| Puntualidad de salida | 20% |
| Horas trabajadas vs. esperadas | 20% |
| Cumplimiento de almuerzo | 15% |
| Cumplimiento de merienda | 10% |
| Ratio de actividad real (no-idle) | 10% |

El score semanal es el promedio de los scores diarios de los días laborales configurados. Las pausas que no se pudieron clasificar automáticamente no penalizan el score — quedan marcadas como "a revisar" en el dashboard.

## Stack técnico

- Python 3.11+ / [PySide6](https://doc.qt.io/qtforpython/) (Qt) para la bandeja, la configuración y el host del dashboard.
- `QtWebEngine` para el dashboard (HTML/CSS/JS con gráficos SVG hechos a mano, sin librerías externas ni internet).
- SQLite (librería estándar) para almacenamiento local.
- `ctypes` sobre `GetLastInputInfo` (user32.dll) para detección de inactividad.
- `pywin32` para autoarranque y notificaciones nativas.
- `PyInstaller` para empaquetar como `.exe` standalone.

## Estado del proyecto / roadmap

- [x] Capa de datos SQLite
- [x] Detección de inactividad y generación automática de entrada/salida
- [x] Popup de clasificación de pausas
- [x] Clasificador automático por horario configurado
- [x] Ícono de bandeja con menú manual de respaldo
- [x] Motor de scoring
- [x] Ventana de configuración
- [x] Dashboard (HTML/JS embebido, sin dependencias externas)
- [x] Autoarranque con Windows
- [ ] Probado en una PC Windows real (desarrollado y testeado hasta acá en macOS de forma "offscreen"; falta validar `GetLastInputInfo`, el acceso directo de autoarranque y la experiencia real de la bandeja en Windows)
- [ ] Primer `.exe` empaquetado con PyInstaller y publicado en Releases
- [ ] Capturas de pantalla reales

El código completo (lógica de negocio + UI) ya está en `control_horas/`, con pruebas automatizadas (`pytest`) para la capa de datos, el clasificador y el motor de scoring.

## Privacidad

La app **no** registra qué teclas se presionan ni capta el contenido de pantalla — solo mide *si* hubo actividad de mouse/teclado y *cuándo*, para poder calcular tiempos. Todos los datos quedan en un archivo local en la propia máquina.
