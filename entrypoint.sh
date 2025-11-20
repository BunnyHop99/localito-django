#!/bin/bash

echo "Esperando a PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL iniciado"

echo "Aplicando migraciones..."
python manage.py makemigrations
python manage.py migrate

echo "Creando superusuario si no existe..."
python manage.py shell << PYEOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@localito.com', 'admin123')
    print('Superusuario creado: admin / admin123')
else:
    print('Superusuario ya existe')
PYEOF

echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "Iniciando servidor..."
exec "$@"