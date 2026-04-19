# Galleria Immagini con Steganografia

Progetto completo per esplorare, filtrare e gestire immagini con una GUI desktop e un backend API dedicato. L'applicazione unisce galleria locale, accesso autenticato, ricerca immagini dal server, metadati e steganografia basata su LSB per nascondere o leggere un messaggio dentro un file PNG.

## Cosa fa il progetto

- Mostra immagini locali in modalità griglia o presentazione.
- Permette ricerca rapida, filtri per formato e navigazione tra le immagini.
- Consente di nascondere ed estrarre un testo segreto da immagini PNG.
- Si collega a un server Flask protetto da JWT per recuperare immagini e metadati.
- Integra un rilevamento YOLO locale e la consultazione dei risultati lato server.
- Usa Docker Compose per avviare il database MongoDB e la API.

## Anteprima

![Anteprima GUI](./screenshots/ScreenshotGUI2025.png)

## Struttura del progetto

- `gui/`: applicazione desktop Tkinter con login, galleria e steganografia.
- `Server_API/`: server Flask, autenticazione JWT, MongoDB e download immagini.
- `screenshots/`: immagini di anteprima del progetto.
- `docker-compose.yml`: avvio del database e del server API.

## Tecnologie usate

- Python 3.x
- Tkinter + ttkbootstrap
- Pillow
- stegano
- Flask
- PyJWT
- pymongo
- Docker e MongoDB

## Requisiti

Serve Python 3 e, per la parte server, Docker Desktop o un ambiente con Docker e Docker Compose.

Le dipendenze sono divise in due file:

- `gui/requirements.txt` per la GUI.
- `Server_API/requirements.txt` per il backend.

## Avvio della GUI

Da Windows:

```bash
\.venv\Scripts\activate
pip install -r gui\requirements.txt
python gui\main.py
```

Su macOS o Linux:

```bash
source .venv/bin/activate
pip install -r gui/requirements.txt
python gui/main.py
```

## Avvio del backend

Il server API e MongoDB si avviano con Docker Compose:

```bash
docker compose up --build
```

Il file `docker-compose.yml` si aspetta queste variabili d'ambiente:

- `MY_APP_SECRET_KEY`
- `MY_MONGO_URI`

## Flusso generale

1. L'utente accede dalla schermata di login.
2. Se le credenziali sono corrette, la GUI riceve un token JWT.
3. La galleria mostra immagini locali o immagini fornite dal server.
4. I metadati vengono letti da MongoDB tramite API.
5. La steganografia permette di inserire o recuperare un messaggio segreto.

## Steganografia

Il progetto usa la tecnica LSB, cioè la modifica dei bit meno significativi dei pixel. Il risultato visivo dell'immagine resta praticamente invariato, ma il file può contenere informazioni nascoste.

```python
from stegano import lsb

lsb.hide("input.png", "Messaggio segreto").save("output.png")
messaggio = lsb.reveal("output.png")
print(messaggio)
```

👨‍💻 **Creato da:** [Samuele](https://github.com/H1R05)  
