FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copiar proyecto
COPY . /app/

# Crear directorios
RUN mkdir -p /app/staticfiles /app/mediafiles

EXPOSE 8000

# Ejecutar migraciones y servidor directamente
CMD sh -c "echo 'Esperando PostgreSQL...' && \
    while ! nc -z db 5432; do sleep 1; done && \
    echo 'PostgreSQL listo!' && \
    echo 'Ejecutando migraciones...' && \
    python manage.py migrate && \
    echo 'Iniciando servidor...' && \
    python manage.py runserver 0.0.0.0:8000"                