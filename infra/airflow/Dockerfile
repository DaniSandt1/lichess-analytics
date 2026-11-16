# Imagen de Airflow con los drivers de las tres bases de datos ya instalados.
# Si agregan una librería que el DAG necesita, súmenla a requirements.txt (de esta carpeta)
# y reconstruyan con:  docker compose build airflow && docker compose up -d airflow
FROM apache/airflow:2.10.5-python3.11

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.11.txt"
