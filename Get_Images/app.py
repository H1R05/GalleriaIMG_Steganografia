from flask import Flask, request, jsonify
from functools import wraps
from datetime import datetime, timezone
import pymongo
import jwt
import os

app = Flask(__name__)

# --- 1. CONFIGURAZIONI DI BASE ---
# ATTENZIONE: Questa chiave deve essere ESATTAMENTE LA STESSA che hai usato 
# nel container 'servizioAutenticazione' per generare il token!
SECRET_KEY = os.environ.get("SECRET_KEY", "chiave_di_riserva_se_docker_fallisce")

# Creiamo una cartella fittizia dove questo server cercherà le immagini
CARTELLA_IMMAGINI = "./immagini_server"
os.makedirs(CARTELLA_IMMAGINI, exist_ok=True)

client = pymongo.MongoClient("mongodb://mongodb:27017/")

db = client["GalleriaImg"]
col = db["log"]

# --- 2. IL DECORATORE (IL MIDDLEWARE DI SICUREZZA) ---
# In Python, un decoratore è una funzione che "avvolge" un'altra funzione.
# Lo usiamo come "buttafuori": prima di eseguire l'API, controlla il passaporto (JWT).
def token_richiesto(f):
    @wraps(f)
    def decoratore(*args, **kwargs):
        token = None
        
        # Cerca l'header "Authorization: Bearer <token>"
        if 'Authorization' in request.headers:
            parti = request.headers['Authorization'].split(" ")
            if len(parti) == 2:
                token = parti[1] # Prende la stringa del token vera e propria

        if not token:
            return jsonify({'message': 'Accesso negato. Manca il token JWT!'}), 401

        try:
            # Il server tenta di decriptare il token con la sua SECRET_KEY.
            # Se la chiave è diversa da quella di chi l'ha creato, l'operazione fallisce.
            dati_utente = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            username = dati_utente.get("user") or dati_utente.get("sub") or "utente_sconosciuto"
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token scaduto. Effettua nuovamente il login.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token non valido o manomesso.'}), 403

        # Se il token è valido, il buttafuori si sposta e lascia eseguire la funzione API
        return f(username, *args, **kwargs)
    
    return decoratore


# --- 3. L'API PRINCIPALE ---
# Metodo GET: riceve richieste per ottenere dati (non per scriverli)
@app.route('/api/images', methods=['GET'])
@token_richiesto  # Applichiamo il nostro "buttafuori" a questa rotta
def get_immagini(username_richiedente):
    try:
        # Catturiamo l'etichetta dai Query Parameters dell'URL (es: ?label=car)
        # Se non c'è nessuna etichetta, request.args.get restituisce 'None'
        etichetta = request.args.get('label')
        
        # Leggiamo tutti i file presenti nella cartella
        tutti_i_file = [f for f in os.listdir(CARTELLA_IMMAGINI) if os.path.isfile(os.path.join(CARTELLA_IMMAGINI, f))]
        
        # Se YOLO ci ha mandato un'etichetta, filtriamo i risultati!
        # (In questo esempio base, controlliamo se la parola 'car' è nel nome del file)
        if etichetta:
            file_filtrati = [f for f in tutti_i_file if etichetta.lower() in f.lower()]
            
            #Store_Data
            nuovo_log = {
                "username": username_richiedente,
                "data_ricerca": datetime.now(timezone.utc),
                "tipo_immagine": etichetta.lower()
            }
            col.insert_one(nuovo_log)
            print(f"[LOG STATISTICHE] Rilevata ricerca per: '{etichetta}'. Preparazione log per MongoDB...")
            
        else:
            # Se l'utente clicca solo su "Sincronizza" senza YOLO, restituiamo tutto
            file_filtrati = tutti_i_file

        # Impacchettiamo la lista in formato JSON e la spediamo alla GUI (Codice 200 = OK)
        return jsonify({"images": file_filtrati}), 200
        
    except Exception as e:
        return jsonify({"error": f"Errore interno del server: {str(e)}"}), 500


# --- 4. AVVIO DEL SERVER ---
if __name__ == '__main__':
    # Usiamo la porta 5001 per non accavallarci con il servizio di autenticazione (porta 5000)
    app.run(host='0.0.0.0', port=5001, debug=True)