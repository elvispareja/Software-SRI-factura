FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No correr como root: si algún día hay una ejecución remota de código, que no
# tenga privilegios de root dentro del contenedor. Se crea un usuario sin
# privilegios dueño de /app. El certificado se firma en /tmp, que appuser puede
# escribir; la app no escribe en /app en tiempo de ejecución (usa PostgreSQL).
RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:aplicacion", "--host", "0.0.0.0", "--port", "8000"]
