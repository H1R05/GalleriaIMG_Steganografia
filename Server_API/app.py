from flask import Flask, request, jsonify, send_from_directory
from functools import wraps
import jwt
import os
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAZIONE ---
SECRET_KEY = os.environ.get("SECRET_KEY") 
CARTELLA_IMMAGINI = "./immagini_server"
os.makedirs(CARTELLA_IMMAGINI, exist_ok=True)

TIPO_TO_FOLDER = {
    "aereo": "aerei",
    "auto": "auto",
    "persona": "persone",
    "treno": "treni",
    "altro": "altro",
}
ESTENSIONI_IMMAGINE = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# --- CONNESSIONE AL DATABASE CLOUD/LOCALE ---
MONGO_URI = os.environ.get("MONGO_URI") 
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['galleria_cloud']
    collezione_utenti = db['utenti']
    collezione_metadati = db['metadati'] # Da popolare manualmente come da PDF
    collezione_log = db['log_ricerche'] 
except Exception as e:
    print(f"Errore MongoDB: {e}")

# --- MIDDLEWARE JWT ---
def token_richiesto(f):
    @wraps(f)
    def decoratore(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parti = request.headers['Authorization'].split(" ")
            if len(parti) == 2: token = parti[1]
        if not token: return jsonify({'message': 'JWT mancante'}), 401
        try:
            dati_utente = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            username = dati_utente.get("username", "sconosciuto")
        except:
            return jsonify({'message': 'JWT non valido'}), 401
        return f(username, *args, **kwargs)
    return decoratore


def _lista_immagini_relative(directory_base):
    immagini = []
    for root, _, files in os.walk(directory_base):
        for nome_file in files:
            estensione = os.path.splitext(nome_file)[1].lower()
            if estensione not in ESTENSIONI_IMMAGINE:
                continue
            percorso_assoluto = os.path.join(root, nome_file)
            percorso_relativo = os.path.relpath(percorso_assoluto, CARTELLA_IMMAGINI)
            immagini.append(percorso_relativo.replace("\\", "/"))
    return sorted(immagini, key=str.lower)

# =========================================================
# 1. JWT GENERATOR (Pagina 5 del PDF)
# =========================================================
@app.route('/login', methods=['POST'])
def login():
    dati = request.get_json()
    username = dati.get('username')
    password = dati.get('password')
    
    utente = collezione_utenti.find_one({"username": username, "password": password})
    if utente:
        # Il PDF richiede JWT con {"username": String, "data": String}
        data_attuale = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        token = jwt.encode({'username': username, 'data': data_attuale}, SECRET_KEY, algorithm="HS256")
        return jsonify({'token': token}), 200
    return jsonify({'message': 'Credenziali errate'}), 401

# =========================================================
# 2. GET IMAGES & STORE DATA (Pagina 5 del PDF)
# =========================================================
@app.route('/api/images', methods=['GET'])
@token_richiesto
def get_images(username_richiedente):
    # Il PDF chiama il parametro "tipoImmagine"
    tipo_immagine = request.args.get('tipoImmagine')
    
    # Store Data come da diagramma (username, data, tipoImmagine)
    if tipo_immagine:
        collezione_log.insert_one({
            "username": username_richiedente,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tipoImmagine": tipo_immagine
        })
    
    # Supporta sia file nella root che file in sottocartelle.
    tutte_le_immagini = _lista_immagini_relative(CARTELLA_IMMAGINI)

    if tipo_immagine:
        tipo_norm = tipo_immagine.lower().strip()
        cartella_tipo = TIPO_TO_FOLDER.get(tipo_norm)

        if cartella_tipo:
            prefisso = f"{cartella_tipo}/"
            file_filtrati = [f for f in tutte_le_immagini if f.lower().startswith(prefisso)]
        else:
            # Fallback per compatibilita: filtro testuale sul path relativo
            file_filtrati = [f for f in tutte_le_immagini if tipo_norm in f.lower()]
    else:
        file_filtrati = tutte_le_immagini

    return jsonify({"images": file_filtrati}), 200

# =========================================================
# 3. GET METADATA (Pagina 5 del PDF)
# =========================================================
@app.route('/api/metadata', methods=['GET'])
@token_richiesto
def get_metadata(username_richiedente):
    # Il PDF impone di inviare nomeImmagine e tipo
    nome_immagine = request.args.get('nomeImmagine')
    tipo = request.args.get('tipo')
    
    # Cerca nel DB usando i due identificatori univoci imposti dal PDF
    dati_immagine = collezione_metadati.find_one({"nomeImmagine": nome_immagine, "tipo": tipo}, {"_id": 0})
    
    if dati_immagine:
        return jsonify(dati_immagine), 200
    return jsonify({"error": "Metadati non trovati. Li hai caricati manualmente su MongoDB?"}), 404

# =========================================================
# 4. DOWNLOAD IMMAGINE FISICA (Per evitare "Immagine non disponibile")
# =========================================================
@app.route('/api/images/download/<path:nome_file>', methods=['GET'])
@token_richiesto
def scarica_immagine_fisica(username_richiedente, nome_file):
    try:
        percorso_norm = os.path.normpath(nome_file)
        if percorso_norm.startswith(".."):
            return jsonify({"error": "Percorso non valido"}), 400
        return send_from_directory(CARTELLA_IMMAGINI, percorso_norm)
    except Exception as e:
        return jsonify({"error": "File non trovato sul server"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)