from flask import Flask, request, jsonify
from functools import wraps
import jwt
import os
from pymongo import MongoClient
from datetime import datetime, timezone

app = Flask(__name__)

# --- 1. CONFIGURAZIONI ---
SECRET_KEY = "la_tua_chiave_segreta_super_sicura" 
CARTELLA_IMMAGINI = "./immagini_server"
os.makedirs(CARTELLA_IMMAGINI, exist_ok=True)

# --- 2. CONNESSIONE AL DATABASE (MONGODB) ---
try:
    # Usiamo il nome del container 'mongodb' come indirizzo IP
    client = MongoClient("mongodb://mongodb:27017/", serverSelectionTimeoutMS=5000)
    db = client['db_galleria']
    
    # Prepariamo le due "scatole" (Collection) per i nostri dati
    collezione_statistiche = db['log_ricerche']
    collezione_metadati = db['dettagli_foto']
except Exception as e:
    print(f"ATTENZIONE: Impossibile connettersi a MongoDB: {e}")

# --- 3. IL GUARDIANO (MIDDLEWARE JWT) ---
def token_richiesto(f):
    @wraps(f)
    def decoratore(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parti = request.headers['Authorization'].split(" ")
            if len(parti) == 2:
                token = parti[1]

        if not token:
            return jsonify({'message': 'Accesso negato. Manca il token JWT!'}), 401

        try:
            dati_utente = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            # Estraiamo l'autore in modo sicuro usando .get()
            username = dati_utente.get("username") or dati_utente.get("sub") or "utente_sconosciuto"
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token scaduto. Effettua nuovamente il login.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token non valido o manomesso.'}), 403

        # Passiamo l'username alla funzione successiva
        return f(username, *args, **kwargs)
    
    return decoratore

# ==========================================
# --- 4. LE ROTTE API (GLI ENDPOINT) ---
# ==========================================

# API 1: Ricerca Immagini e Salvataggio Statistiche (Punto 3)
@app.route('/api/images', methods=['GET'])
@token_richiesto
def get_immagini(username_richiedente):
    try:
        etichetta = request.args.get('label')
        tutti_i_file = [f for f in os.listdir(CARTELLA_IMMAGINI) if os.path.isfile(os.path.join(CARTELLA_IMMAGINI, f))]
        
        if etichetta:
            # Filtriamo i file che contengono la parola cercata
            file_filtrati = [f for f in tutti_i_file if etichetta.lower() in f.lower()]
            
            # Scriviamo il log su MongoDB
            try:
                nuovo_log = {
                    "utente": username_richiedente,
                    "tipo_immagine": etichetta.lower(),
                    "data_ricerca": datetime.now(timezone.utc)
                }
                collezione_statistiche.insert_one(nuovo_log)
                print(f"[LOG] {username_richiedente} ha cercato: '{etichetta}'.")
            except Exception as db_err:
                print(f"[ERRORE LOG] Impossibile salvare la statistica: {db_err}")
        else:
            file_filtrati = tutti_i_file

        return jsonify({"images": file_filtrati}), 200
    except Exception as e:
        return jsonify({"error": f"Errore server: {str(e)}"}), 500


# API 2: Dettagli Singola Immagine (Punto 4)
@app.route('/api/metadata/<nome_file>', methods=['GET'])
@token_richiesto
def get_metadati_singoli(username_richiedente, nome_file):
    try:
        # Cerchiamo i metadati specifici di questo file nel database
        dati_immagine = collezione_metadati.find_one({"file": nome_file}, {"_id": 0})
        
        if dati_immagine:
            return jsonify(dati_immagine), 200
        else:
            # Se il database non ha dati per questa foto, creiamo un JSON fittizio per non bloccare la GUI
            estensione = nome_file.split('.')[-1].upper() if '.' in nome_file else "SCONOSCIUTO"
            return jsonify({
                "file": nome_file,
                "descrizione": "Nessun metadato avanzato presente nel database.",
                "formato": estensione,
                "caricato_da": "Sistema"
            }), 200
            
    except Exception as e:
        return jsonify({"error": f"Errore DB: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)