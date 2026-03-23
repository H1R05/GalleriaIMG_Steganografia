# 1. BASE: Partiamo da un sistema Linux leggero con Python 3.11 già installato
FROM python:3.11-slim

# 2. WORKDIR: Creiamo una cartella virtuale '/app' dentro il container e ci entriamo
WORKDIR /app

# 3. OTTIMIZZAZIONE CACHE: Copiamo prima solo il file dei requisiti
COPY requirements.txt .

# 4. INSTALLAZIONE: Diciamo al sistema Linux di installare le librerie
RUN pip install --no-cache-dir -r requirements.txt

# 5. COPIA DEL CODICE: Ora copiamo il nostro app.py (e tutto il resto) dentro /app
COPY . .

# 6. RETE: Dichiariamo che il container comunicherà sulla porta 5001
EXPOSE 5001

# 7. AVVIO: Il comando che avvierà il server Flask quando il container si accende
CMD ["python", "app.py"]