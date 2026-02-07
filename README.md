# MOPT-SCIS
Prueba tecnica de mopt para lider tecnico de aplicaciones moviles.

# Creado por : Jorge Luis Iraheta
# Para Prueba de Lider de aplicaciones moviles en el MOPT

## Tecnilogicas que se han ocupado para el desarrollo del proyecto 

Backend:

•	Python 312.10 
•	FastAPI 0.128.0 
•	Starlette 0.50.0
•	Uvicorn 0.24.0 
Persistencia y transacciones
•	SQLAlchemy 2.0.23 
Validación y contratos de datos
•	Pydantic 2.12.5
•	pydantic-core 2.41.5
Seguridad y autenticación
•	python-jose 3.3.0 – JWT
•	passlib 1.7.4 
•	bcrypt 4.0.1
•	cryptography 41.0.7
Configuración y soporte
•	python-dotenv 1.0.0 
•	PyYAML 6.0.3 

## Diseño de ci.yaml 
En la siguiente ruta : MOPT-SCIS/.github /workflows/

Definicion de CI.

name: CI Pipeline - SCIS Backend

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  ci:
    runs-on: ubuntu-latest

    steps:
      #  Checkout del código del backend
      - name: Checkout repository
        uses: actions/checkout@v4

      #  Configuración de Python (stack definido)
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      #  Instalación de dependencias productivas del backend
      - name: Install backend dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install httpx

      #  Instalación de herramientas de CI (solo para el pipeline)
      - name: Install CI tools (Linter, Tests, SAST)
        run: |
          pip install flake8 pytest bandit

      #  BUILD & TEST – Linter (solo código backend)
      - name: Run Linter (Flake8)
        run: |
          flake8 backend/app backend/scripts --max-line-length=120 --extend-ignore=W293,W291,W292,E501,F401,E302,E305,E402,F541


      #  BUILD & TEST – Pruebas unitarias del backend
      - name: Run Unit Tests (Pytest)
        run: |
          python -m pytest backend/tests/test_health.py -v

      #  SECURITY SCAN – SAST sobre el backend
      - name: Run Security Scan (Bandit)
        run: |
          bandit -r backend/app -ll --skip=B104 --skip=B101
