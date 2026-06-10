# ⚡ Compu-Global-Hyper-Meganet ERP

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge\&logo=fastapi\&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge\&logo=postgresql\&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?style=for-the-badge\&logo=streamlit\&logoColor=white)

A modern ERP dashboard built with **Python**, **FastAPI**, **PostgreSQL** and **Streamlit**.

This project combines a REST API backend, a relational PostgreSQL database and a modern Streamlit frontend for managing master data, purchasing, sales, exports and reporting.

---

## ✨ Overview

**Compu-Global-Hyper-Meganet ERP** is a lightweight business management system created as a full-stack database project.

The application demonstrates how backend APIs, database structures and an interactive frontend can work together in a practical ERP scenario. It includes core ERP features such as customer and supplier management, product data, purchase orders, invoices, exports and business reporting.

The user interface was redesigned with a clean and modern dashboard layout to make the project suitable for a professional GitHub and portfolio presentation.

---

## 🎓 Project Background

This ERP system was originally developed as a school project during my training program at **COMCAVE College**, in cooperation with **Enders Training**.

For my personal learning goals and portfolio, I redesigned and extended the project further. This included improving the user interface, modernizing the Streamlit frontend, refining the project presentation and expanding the overall look and feel of the application.

The project therefore represents both the original educational assignment and my own continued development work. My goal was to turn the basic project into a more polished and portfolio-ready full-stack application.

---

## 🖥️ Preview

The frontend was redesigned with a modern dashboard style, custom sidebar navigation, clean KPI cards, page-specific browser tab titles and improved visual structure across all pages.

> Screenshots can be added here after uploading the project to GitHub.

```md
![Dashboard Preview](docs/dashboard-preview.png)
```

---

## 🧱 Tech Stack

| Layer                | Technology |
| -------------------- | ---------- |
| Programming Language | Python     |
| Backend API          | FastAPI    |
| Database             | PostgreSQL |
| Frontend             | Streamlit  |
| Data Handling        | Pandas     |
| Visualization        | Plotly     |
| Testing              | Pytest     |

---

## 📌 Main Features

### 🏠 Home Dashboard

* central overview of important ERP metrics
* KPI cards for customers, suppliers, open orders and invoices
* stock reorder warnings
* refresh functionality
* modern dashboard header

### 🗃️ Master Data

* management of customers, suppliers and combined business contacts
* article and product data overview
* search and filter functionality
* structured data tables
* action buttons for future CRUD extensions

### 🛒 Purchasing

* purchase order overview
* supplier-related purchasing data
* stock and reorder support
* purchasing workflow foundation

### 🧾 Sales

* invoice and sales overview
* open invoice indicators
* overdue invoice tracking
* customer-related sales information

### 📤 Export

* export-oriented backend structure
* prepared routes for business data exports
* separate export module for future file generation

### 📊 Reporting

* reporting dashboard structure
* KPI-based business insights
* foundation for charts and advanced analytics

---

## 🎨 UI Improvements

The Streamlit frontend was customized and modernized to create a cleaner portfolio presentation.

Implemented design improvements include:

* custom sidebar branding
* modern navigation with icons
* replacement of the default Streamlit page label
* page-specific browser tab titles
* gradient hero sections
* clean KPI cards
* improved table styling
* compact system stack section
* consistent layout across all pages
* more professional spacing, typography and visual hierarchy

---

## 📁 Project Structure

```text
Database-ERP-Project/
├── backend/
│   ├── api.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── logger.py
│   ├── routers/
│   │   ├── stammdaten.py
│   │   ├── einkauf.py
│   │   ├── verkauf.py
│   │   ├── export.py
│   │   └── reporting.py
│   └── services/
│       ├── stammdaten_service.py
│       ├── einkauf_service.py
│       └── verkauf_service.py
│
├── frontend/
│   ├── streamlit_app.py
│   ├── utils.py
│   └── pages/
│       ├── 01_Stammdaten.py
│       ├── 02_Einkauf.py
│       ├── 03_Verkauf.py
│       ├── 04_Export.py
│       └── 05_Reporting.py
│
├── exports/
├── logs/
├── tests/
├── erp_setup.sql
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

---

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate the virtual environment.

**Windows:**

```bash
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env.development
```

Then update the database credentials inside `.env.development`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=erp
DB_USER=postgres
DB_PASSWORD=your_password_here
API_URL=http://localhost:8000
KLINIK_ENV=development
LOG_LEVEL=INFO
```

---

### 5. Set up the PostgreSQL database

Make sure PostgreSQL is installed and running.

Then execute the SQL setup file:

```bash
psql -U postgres -f erp_setup.sql
```

This creates the required database structure and inserts sample data.

---

### 6. Start the FastAPI backend

```bash
uvicorn backend.api:app --reload
```

The backend API will be available at:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

---

### 7. Start the Streamlit frontend

Open a second terminal and run:

```bash
streamlit run frontend/streamlit_app.py
```

The frontend will be available at:

```text
http://localhost:8501
```

---

## 🔌 API Modules

| Module      | Prefix        | Description                                |
| ----------- | ------------- | ------------------------------------------ |
| Master Data | `/stammdaten` | persons, customers, suppliers and articles |
| Purchasing  | `/einkauf`    | purchase orders and purchasing data        |
| Sales       | `/verkauf`    | invoices and sales-related data            |
| Export      | `/export`     | export routes and generated files          |
| Reporting   | `/reporting`  | reporting and KPI endpoints                |

---

## 🧪 Testing

Run tests with:

```bash
pytest
```

---

## 📚 Learning Goals

This project helped me improve my skills in:

* building REST APIs with FastAPI
* connecting Python applications to PostgreSQL
* structuring backend routes and services
* working with relational database models
* creating an interactive Streamlit frontend
* designing a more modern dashboard interface
* preparing a technical project for GitHub and portfolio use

---

## 🔮 Possible Future Improvements

Planned or possible improvements include:

* user authentication and role management
* Docker setup for backend, frontend and database
* full CRUD dialogs for all ERP modules
* invoice PDF generation
* advanced reporting charts
* automated API endpoint tests
* deployment guide
* improved error handling and validation
* responsive layout optimization

---

## 👤 Author

Created and further developed by **Lesley Fournier**.

Originally created as part of a school project at **COMCAVE College** in cooperation with **Enders Training**.
Redesigned, extended and prepared as a portfolio project for personal learning and presentation purposes.

---

## 📄 License

This project is intended for educational and portfolio purposes.

You can add a dedicated license file depending on how you want to publish or reuse the project.
