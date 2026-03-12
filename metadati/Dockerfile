# 1. Immagine Base: Partiamo da un sistema operativo Linux minimale con Python 3.11 preinstallato.
# Usare le versioni 'slim' riduce drasticamente il peso del container in MB.
FROM python:3.11-slim

# 2. Directory di Lavoro: Diciamo a Docker "Tutte le operazioni da ora in poi falle dentro la cartella /app"
WORKDIR /app

# 3. Ottimizzazione della Cache: Copiamo PRIMA solo il file dei requisiti.
# Questo è un trucco DevOps: se modifichi il codice (app.py) ma non le librerie, 
# Docker non dovrà riscaricare Flask da capo, risparmiando minuti preziosi di build!
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copia del Codice: Ora copiamo il nostro app.py (e tutto il resto) dentro /app
COPY . .

# 5. Documentazione Porta: Segnaliamo che questo container comunicherà sulla porta 5001
EXPOSE 5001

# 6. Comando di Esecuzione: Il comando che Docker lancerà appena il container si accende
CMD ["python", "app.py"]