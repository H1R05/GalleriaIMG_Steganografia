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
# 2. MOTORE DI RETE (Ricerca Lista Immagini)
# ==========================================
def richiedi_immagini_server(token, termine_ricerca, callback_risposta):
    """Interroga il server Metadati per avere la lista dei file."""
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
                callback_risposta(True, lista_file)
            else:
                callback_risposta(False, f"Errore {risposta.status_code}: {risposta.text}")

        except requests.exceptions.ConnectionError:
            callback_risposta(False, "Errore di connessione: Il server Flask è spento?")
        except Exception as e:
            callback_risposta(False, f"Errore di rete: {str(e)}")

    thread_get = threading.Thread(target=worker)
    thread_get.daemon = True
    thread_get.start()


# ==========================================
# 3. MOTORE DI RETE (Dettagli Singola Immagine)
# ==========================================
def richiedi_metadati_immagine(token, nome_file, callback_risposta):
    """Interroga il server Metadati per avere il JSON di una foto specifica."""
    def worker():
        url_flask = f"http://127.0.0.1:5001/api/metadata/{nome_file}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            risposta = requests.get(url_flask, headers=headers, timeout=5)

            if risposta.status_code == 200:
                dati_json = risposta.json()
                callback_risposta(True, dati_json)
            else:
                callback_risposta(False, f"Errore {risposta.status_code}: {risposta.text}")

        except requests.exceptions.ConnectionError:
            callback_risposta(False, "Errore di connessione al server Metadati.")
        except Exception as e:
            callback_risposta(False, f"Errore imprevisto: {str(e)}")

    thread_meta = threading.Thread(target=worker)
    thread_meta.daemon = True
    thread_meta.start()