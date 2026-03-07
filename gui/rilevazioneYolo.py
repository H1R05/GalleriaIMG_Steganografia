import threading
import requests
from ultralytics import YOLO

# ==========================================
# 1. MOTORE IA LOCALE (Edge Computing)
# ==========================================
def esegui_rilevamento_yolo_locale(image_path, callback_aggiornamento_ui):
    """Esegue YOLO in locale senza chiamate di rete."""
    def worker():
        try:
            model = YOLO("yolov8n.pt") 
            risultati = model(image_path)
            
            oggetti_trovati = []
            for risultato in risultati:
                for box in risultato.boxes:
                    class_id = int(box.cls[0])
                    oggetti_trovati.append(model.names[class_id])
            
            if not oggetti_trovati:
                esito = "Nessun oggetto riconosciuto dall'IA."
                callback_aggiornamento_ui(esito, "inverse-warning", None)
            else:
                etichetta_dominante = oggetti_trovati[0] 
                esito = f"✅ Trovati: {', '.join(oggetti_trovati)}"
                callback_aggiornamento_ui(esito, "inverse-success", etichetta_dominante)
                
        except Exception as e:
            callback_aggiornamento_ui(f"❌ Errore IA locale: {str(e)}", "inverse-danger", None)

    thread_ia = threading.Thread(target=worker)
    thread_ia.daemon = True
    thread_ia.start()


# ==========================================
# 2. MOTORE DI RETE (Comunicazione con Flask)
# ==========================================
def richiedi_immagini_server(token, termine_ricerca, callback_risposta):
    """
    Esegue la chiamata GET HTTP al microservizio Metadati.
    - token: il JWT dell'utente.
    - termine_ricerca: l'etichetta trovata da YOLO (es. 'car').
    - callback_risposta: la funzione della GUI a cui restituire la lista o l'errore.
    """
    def worker():
        if termine_ricerca:
            url_flask = f"http://127.0.0.1:5001/api/images?label={termine_ricerca}"
        else:
            url_flask = "http://127.0.0.1:5001/api/images"
            
        headers = {"Authorization": f"Bearer {token}"}

        try:
            risposta = requests.get(url_flask, headers=headers, timeout=5)

            if risposta.status_code == 200:
                dati = risposta.json()
                lista_file = dati.get("images", [])
                # Passiamo 'True' per indicare il successo e la lista dei file
                callback_risposta(True, lista_file)
            else:
                errore = f"Errore {risposta.status_code}: Impossibile scaricare la lista."
                # Passiamo 'False' per indicare l'errore e il messaggio
                callback_risposta(False, errore)

        except requests.exceptions.ConnectionError:
            callback_risposta(False, "Errore di connessione: Il server Flask è spento?")
        except Exception as e:
            callback_risposta(False, f"Errore di rete: {str(e)}")

    thread_get = threading.Thread(target=worker)
    thread_get.daemon = True
    thread_get.start()