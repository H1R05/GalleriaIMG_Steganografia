# Usa un'immagine Python minimale
FROM python:3.11-slim

# Imposta la directory di lavoro dentro il container
WORKDIR /app

# Copia e installa prima le dipendenze (sfrutta la cache di Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia l'intero codice sorgente e la cartella immagini_server dentro il container
COPY . .

# Esponi la porta 5000
EXPOSE 5000

# Avvia il server
CMD ["python", "app.py"]