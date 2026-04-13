import threading
import requests
import io
import os
from PIL import Image

modello_yolo_globale = None
errore_modello_yolo = None
_lock_modello = threading.Lock()


def _carica_modello_yolo_se_necessario():
    global modello_yolo_globale, errore_modello_yolo
    if modello_yolo_globale is not None:
        return modello_yolo_globale

    with _lock_modello:
        if modello_yolo_globale is not None:
            return modello_yolo_globale
        if errore_modello_yolo is not None:
            return None

        try:
            from ultralytics import YOLO

            percorso_modello = os.path.join(os.path.dirname(__file__), "yolov8n.pt")
            modello_yolo_globale = YOLO(percorso_modello)
        except Exception as e:
            errore_modello_yolo = str(e)
            modello_yolo_globale = None

    return modello_yolo_globale

sessione_http = requests.Session()

# ==========================================
# TRADUTTORE UFFICIALE (Basato sul PDF del Prof)
# ==========================================
def traduci_etichetta_yolo(etichetta_inglese):
    """Traduce i risultati di YOLO nelle 5 categorie del PDF."""
    etichetta = etichetta_inglese.lower()
    if etichetta == "person": return "persona"
    elif etichetta in ["car", "truck", "bus"]: return "auto"
    elif etichetta == "train": return "treno"
    elif etichetta == "airplane": return "aereo"
    else: return "altro"

# ==========================================
# 1. MOTORE IA LOCALE 
# ==========================================
def esegui_rilevamento_yolo_locale(image_path, callback_aggiornamento_ui):
    def worker():
        try:
            modello = _carica_modello_yolo_se_necessario()
            if not modello:
                dettaglio = f": {errore_modello_yolo}" if errore_modello_yolo else ""
                callback_aggiornamento_ui(f"❌ Errore Modello YOLO{dettaglio}", "inverse-danger", None)
                return
                
            risultati = modello(image_path)
            
            oggetti_trovati = []
            for risultato in risultati:
                for box in risultato.boxes:
                    class_id = int(box.cls[0])
                    # TRADUCIAMO SUBITO IN ITALIANO
                    nome_italiano = traduci_etichetta_yolo(modello.names[class_id])
                    oggetti_trovati.append(nome_italiano)
            
            if not oggetti_trovati:
                callback_aggiornamento_ui("Nessun oggetto.", "inverse-warning", None)
            else:
                etichetta_dominante = oggetti_trovati[0] 
                esito = f"✅ Trovato: {etichetta_dominante}"
                callback_aggiornamento_ui(esito, "inverse-success", etichetta_dominante)
                
        except Exception as e:
            callback_aggiornamento_ui(f"❌ Errore IA: {str(e)}", "inverse-danger", None)

    threading.Thread(target=worker, daemon=True).start()

# ==========================================
# 2. RICERCA IMMAGINI (Conforme al PDF)
# ==========================================
def richiedi_immagini_server(token, termine_ricerca, callback_risposta):
    def worker():
        # Il PDF usa il parametro 'tipoImmagine'
        if termine_ricerca:
            url_flask = f"http://127.0.0.1:5000/api/images?tipoImmagine={termine_ricerca}"
        else:
            url_flask = "http://127.0.0.1:5000/api/images"
            
        headers = {"Authorization": f"Bearer {token}"}
        try:
            risposta = sessione_http.get(url_flask, headers=headers, timeout=5)
            if risposta.status_code == 200:
                callback_risposta(True, risposta.json().get("images", []))
            else:
                callback_risposta(False, f"Errore: {risposta.text}")
        except Exception as e:
            callback_risposta(False, f"Errore di rete: {str(e)}")

    threading.Thread(target=worker, daemon=True).start()

# ==========================================
# 3. METADATI (Conforme al PDF)
# ==========================================
def richiedi_metadati_immagine(token, nome_file, tipo_immagine, callback_risposta):
    def worker():
        # Il PDF richiede nomeImmagine e tipo come parametri!
        url_flask = f"http://127.0.0.1:5000/api/metadata?nomeImmagine={nome_file}&tipo={tipo_immagine}"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            risposta = sessione_http.get(url_flask, headers=headers, timeout=5)
            if risposta.status_code == 200:
                callback_risposta(True, risposta.json())
            else:
                callback_risposta(False, f"Errore: {risposta.text}")
        except Exception as e:
            callback_risposta(False, f"Errore imprevisto: {str(e)}")

    threading.Thread(target=worker, daemon=True).start()

# ==========================================
# 4. DOWNLOAD IMMAGINE 
# ==========================================
def scarica_immagine_dal_server(token, nome_file, callback_risposta):
    def worker():
        url_flask = f"http://127.0.0.1:5000/api/images/download/{nome_file}"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            risposta = sessione_http.get(url_flask, headers=headers, stream=True, timeout=10)
            if risposta.status_code == 200:
                image_bytes = io.BytesIO(risposta.content)
                img = Image.open(image_bytes)
                img.load() # FONDAMENTALE PER FAR APPARIRE L'IMMAGINE NELLA GUI!
                callback_risposta(True, img)
            else:
                callback_risposta(False, f"Errore nel download.")
        except Exception as e:
            callback_risposta(False, f"Errore: {str(e)}")

    threading.Thread(target=worker, daemon=True).start()