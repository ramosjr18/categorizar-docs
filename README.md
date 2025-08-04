# 📂 Categorizar Docs

Sistema web para la **gestión, carga, categorización, visualización y análisis gráfico** de documentos como PDF, DOCX, XLSX y CSV mediante OCR y procesamiento automático.

> Proyecto dividido en dos partes: `frontend/` (HTML/JS) y `backend/` (Flask + SQLAlchemy).

---

## 📌 Características

- 🧾 Subida de documentos con control de versiones y detección de duplicados
- 📑 Extracción de texto automática mediante OCR
- 🏷️ Categorización inteligente basada en contenido y metadatos
- 📊 Visualización gráfica de datos en archivos `.csv` y `.xlsx`
- 🛡️ Autenticación segura con sesiones
- 🧹 Limpieza automática de archivos no registrados
- 🔎 Exploración y descarga de documentos cargados

---

## 🚀 Instalación rápida

### 1. Clonar el repositorio

```bash
git clone https://github.com/ramosjr18/categorizar-docs.git
cd categorizar-docs/backend
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Crear estructura de carpetas

```bash
mkdir uploads
```

### 4. Ejecutar la app

```bash
python run.py
```

> El servidor Flask estará corriendo en: [http://localhost:5000](http://localhost:5000)

### 5. En nueva ventana entrar en el frontend

```bash
cd categorizar-docs/frontend
```

### 6. Ejecutar Servidor Python

```bash
python -m http.server 8000
```

---

## 🗃️ Estructura del proyecto

```
CATEGORIZAR-DOCS/
├── backend/
│   ├── app/
│   │   ├── templates/
│   │   ├── utils/
│   │   │   ├── instance/
│   │   │   ├── categorize.py
│   │   │   ├── es_graficable.py
│   │   │   ├── file_comparator.py
│   │   │   ├── limpieza_programada.py
│   │   │   ├── ocr.py
│   │   │   └── __init__.py
│   │   ├── auth_routes.py
│   │   ├── config.py
│   │   ├── models.py
│   │   └── routes.py
│   ├── instance/
│   ├── uploads/
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── favicon_io/
│   ├── detalle.html
│   ├── detallebackup.html
│   ├── graficar-multiple.html
│   ├── graficar.html
│   ├── index_backup.html
│   ├── index.html
│   ├── inventario.html
│   ├── ip-graficos.html
│   ├── login.html
│   ├── preview.html
│   ├── register.html
│   ├── main.js
│   ├── main-graficar.js   
│   ├── styles.css
├── .gitignore
└── README.md

```

---

## 🔐 Autenticación

- `POST /api/register` – Registro de usuario
- `POST /api/login` – Inicio de sesión
- `POST /api/logout` – Cierre de sesión
- Las rutas protegidas validan la sesión con `@login_required`

---

## 📁 Gestión de documentos

- `POST /upload` – Subir documento (PDF, DOCX, XLSX, CSV)
- `GET /documentos` – Listar documentos
- `GET /documentos/<id>` – Ver detalle
- `GET /documentos/<id>/descargar` – Descargar documento
- `DELETE /documentos/<id>` – Eliminar documento

---

## 📊 Gráficos

- `GET /api/hojas/<id>` – Obtener hojas o columnas
- `GET /graficos?id=<id>&hojas=...` – Ver gráfico simple
- `POST /api/graficos-multiples` – Enviar múltiples archivos con hojas para graficar
- `POST /validar_graficable` – Validar si un archivo es graficable

---

## 🧼 Limpieza automática

La app elimina archivos huérfanos (que ya no están en la base de datos) automáticamente cada 7 días mediante `APScheduler`.

Configurado en `run.py`:

```python
from app.utils.limpieza_programada import limpiar_archivos_no_registrados
```

---

## ⚙️ Requisitos

- Python 3.8+
- Flask
- SQLAlchemy
- APScheduler
- pandas
- openpyxl
- python-docx
- pytesseract
- y más...

Instala todo con:

```bash
pip install -r requirements.txt
```

---

## ✅ TODO / Mejoras futuras

- [ ] Implementar pruebas unitarias y de integración
- [ ] Mejorar la interfaz de usuario
- [ ] Añadir documentación Swagger/OpenAPI

