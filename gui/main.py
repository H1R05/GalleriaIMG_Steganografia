# --- Importazione Librerie Essenziali ---
import tkinter as tk
# ttkbootstrap migliora l'aspetto di tkinter
import ttkbootstrap as ttk
from ttkbootstrap.constants import * # Importa costanti di stile (es. PRIMARY, INFO)
from tkinter import filedialog, messagebox, scrolledtext # Widget standard Tkinter
import os # Per operazioni sul sistema operativo (path, file)
from PIL import Image, ImageTk, UnidentifiedImageError # Per manipolazione immagini
import sys # Per controllare l'ambiente di esecuzione (es. se è un eseguibile)
import traceback # Per ottenere dettagli sugli errori
import requests as req

# --- Importazione Libreria Steganografia (con controllo) ---
# La steganografia permette di nascondere dati (testo) dentro immagini
try:
    from stegano import lsb # Usiamo il metodo LSB (Least Significant Bit)
except ImportError:
    # Se la libreria manca, avvisa l'utente ed esci
    messagebox.showerror("Errore Dipendenza", "Libreria 'stegano' non trovata.\nInstallala con: pip install stegano")
    sys.exit(1) # Termina l'applicazione


# --- Classe Principale dell'Applicazione ---
class GalleriaImmagini(ttk.Window):
    """Finestra principale dell'applicazione Galleria Immagini con funzioni di steganografia."""

    # --- Metodi per Ricerca Dinamica ---

    def _on_search_change(self, event=None):
        """Chiamato quando il testo nella barra di ricerca cambia (KeyRelease).
           Avvia un timer (debounce) per eseguire la ricerca effettiva.
        """
        # Se c'è già un timer in attesa, cancellalo
        if self._search_debounce_job:
            self.after_cancel(self._search_debounce_job)

        # Avvia un nuovo timer per chiamare _perform_search dopo 300ms
        # self.after è un metodo Tkinter per eseguire codice dopo un ritardo
        self._search_debounce_job = self.after(300, self._perform_search)

    def _perform_search(self):
        """Esegue la ricerca effettiva basandosi sul contenuto attuale della barra.
        Questa funzione viene chiamata dopo il ritardo di debounce.
        """
        self._search_debounce_job = None # Resetta il job ID

        # Esegui la ricerca solo se una cartella è aperta
        if self.directory_corrente:
            termine_ricerca = self.txt_ricerca.get()
            # Riutilizza la funzione esistente per caricare/filtrare le immagini
            self.carica_immagini_da_cartella(self.directory_corrente, termine_ricerca)
        # else:
        # Potrebbe voler pulire la griglia se non c'è una cartella,
        # ma lascia che carica_immagini_da_cartella gestisca il caso
        # in cui self.directory_corrente è vuoto.


    # --- Costanti di Configurazione ---
    APP_TITLE = "Galleria Immagini Samu v1.2 (Steganografia)" # Titolo finestra
    DEFAULT_GEOMETRY = "1150x700" # Dimensioni iniziali
    MIN_WINDOW_SIZE = (650, 450) # Dimensioni minime
    THUMBNAIL_SIZE = (150, 150) # Dimensione miniature nella griglia
    THUMBNAIL_PADDING = 8 # Spaziatura attorno alle miniature
    ICON_SIZE = (20, 20) # Dimensione icone nella toolbar

    # Dizionario dei formati immagine supportati e le loro estensioni
    SUPPORTED_EXT_MAP = {
        "JPEG": ('.jpg', '.jpeg'),
        "PNG": ('.png',),
        "GIF": ('.gif',),
        "BMP": ('.bmp',),
    }
    # Lista piatta di tutte le estensioni supportate (per i dialoghi file)
    ALL_SUPPORTED_EXT_FLAT = [ext for group in SUPPORTED_EXT_MAP.values() for ext in group]
    # Tipi di file per il dialogo "Apri"
    FILEDIALOG_TYPES = [
        ("Immagini Supportate", "*" + " *".join(ALL_SUPPORTED_EXT_FLAT)),
        *[(name, "*" + " *".join(exts)) for name, exts in SUPPORTED_EXT_MAP.items()],
        ("Tutti i file", "*.*")
    ]
    # Tipi di file per il dialogo "Salva Come..." (conversione base)
    SAVE_FILEDIALOG_TYPES = [
        ("JPEG", "*.jpg"),
        ("PNG", "*.png"),
        ("GIF", "*.gif"),
        ("BMP", "*.bmp"),
        ("Tutti i file", "*.*")
    ]
    # Tipi di file specifici per salvare con steganografia (solo PNG è affidabile)
    STEGANO_SAVE_FILETYPES = [
        ("PNG (Lossless)", "*.png"),
    ]

    # --- Costruttore della Classe ---
    def __init__(self):
        """Inizializza la finestra principale e i suoi componenti."""
        # Chiama il costruttore della classe base (ttk.Window) con un tema
        super().__init__(themename="superhero") # Prova altri temi: "litera", "pulse", "darkly"
        self.title(self.APP_TITLE)
        self.geometry(self.DEFAULT_GEOMETRY)
        self.minsize(*self.MIN_WINDOW_SIZE)
        # Associa la chiusura della finestra (bottone X) al metodo self.quit
        self.protocol("WM_DELETE_WINDOW", self.quit)

        # Trova il percorso base per caricare risorse (es. icone)
        self.base_path = self._get_base_path()
        self.icon_path = os.path.join(self.base_path, "icons") # Cartella icone

        # Inizializza le variabili di stato
        self._initialize_state()

        # Crea la barra di stato in fondo alla finestra
        self.barra_stato = ttk.Label(self, text="Pronto", relief=tk.FLAT, anchor=tk.W, bootstyle=PRIMARY)
        self.barra_stato.pack(side=tk.BOTTOM, fill=tk.X)

        # Crea tutti i widget (menu, toolbar, area visualizzazione, etc.)
        self._create_widgets()
        # Collega gli eventi (es. tasti freccia, resize) alle funzioni corrispondenti
        self._bind_events()
        # Imposta lo stato iniziale dell'interfaccia (es. cosa mostrare all'inizio)
        self._initial_ui_update()
        print(f"{self.APP_TITLE} inizializzata.")

    # --- Metodo per Inizializzare lo Stato ---
    def _initialize_state(self):
        """Inizializza le variabili che mantengono lo stato dell'applicazione."""
        self.immagini = [] # Lista delle immagini caricate (dizionari con 'path')
        self.indice_corrente = tk.IntVar(value=-1) # Indice dell'immagine selezionata (-1 = nessuna)
        self.modalita_visualizzazione = tk.StringVar(value="Griglia") # "Griglia" o "Presentazione"
        self.directory_corrente = "" # Cartella attualmente aperta
        self.current_photo_image = None # Riferimento all'oggetto PhotoImage per evitare garbage collection

        # Variabili booleane per i filtri tipo file
        self.filtro_jpeg = tk.BooleanVar(value=True)
        self.filtro_png = tk.BooleanVar(value=True)
        self.filtro_gif = tk.BooleanVar(value=True)
        self.filtro_bmp = tk.BooleanVar(value=True)

        # Dizionario per conservare le icone caricate
        self.icons = {}

        # Variabile per attivare/disattivare la modalità steganografia
        self.stegano_mode = tk.BooleanVar(value=False)
        self._search_debounce_job = None #Tiene traccia del timer

    # --- Metodo per Trovare il Percorso Base ---
    def _get_base_path(self):
        """Restituisce il percorso base dell'applicazione (utile per trovare risorse)."""
        # Se l'app è "congelata" (es. eseguibile PyInstaller), usa il percorso dell'eseguibile
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        # Altrimenti (esecuzione normale .py), usa il percorso dello script
        else:
            return os.path.dirname(os.path.abspath(__file__))

    # --- Metodo per Caricare Icone ---
    def _load_icon(self, filename):
        """Carica un'icona dal file specificato, la ridimensiona e la restituisce come PhotoImage."""
        try:
            full_path = os.path.join(self.icon_path, filename)
            # Se il file non esiste, non fare nulla (gestione silenziosa)
            if not os.path.exists(full_path):
                # print(f"Attenzione: Icona non trovata: {full_path}") # Debug
                return None
            # Apre l'immagine con PIL
            img = Image.open(full_path)
            # Ridimensiona l'immagine con antialiasing di alta qualità
            img_resized = img.resize(self.ICON_SIZE, Image.Resampling.LANCZOS)
            # Converte in formato utilizzabile da Tkinter
            photo_image = ImageTk.PhotoImage(img_resized)
            # Conserva un riferimento all'icona per evitare che venga eliminata
            self.icons[filename] = photo_image
            return photo_image
        except FileNotFoundError:
            # print(f"Errore: Impossibile trovare l'icona '{filename}' in {self.icon_path}") # Debug
            return None
        except Exception as e:
            # print(f"Errore durante il caricamento dell'icona '{filename}': {e}") # Debug
            return None

    # --- Metodo per Creare i Widget ---
    def _create_widgets(self):
        """Crea e organizza tutti i widget principali dell'interfaccia."""
        self._create_menu() # Barra menu in alto

        # Frame principale che contiene tutto il resto
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True) # Occupa tutto lo spazio disponibile

        # Barra degli strumenti sotto il menu
        self.toolbar = self._create_toolbar(main_frame)
        self.toolbar.pack(fill=tk.X, pady=(0, 10)) # Occupa tutta la larghezza

        # Area centrale per visualizzare immagini (griglia o presentazione)
        self.display_frame = self._create_display_area(main_frame)
        self.display_frame.pack(fill=tk.BOTH, expand=True) # Occupa lo spazio rimanente

        # Pannello inferiore per dettagli immagine / input steganografia
        self.details_panel = self._create_details_panel(main_frame)
        self.details_panel.pack(fill=tk.X, pady=(10, 0)) # Occupa larghezza, sotto l'area display

        # Barra inferiore con i filtri per tipo file
        self.filter_bar = self._create_filter_bar(main_frame)
        self.filter_bar.pack(fill=tk.X, pady=(5, 0)) # Occupa larghezza, sotto i dettagli

    # --- Metodo per Creare il Menu ---
    def _create_menu(self):
        """Crea la barra dei menu superiore."""
        menubar = tk.Menu(self) # Contenitore principale del menu

        # --- Menu File ---
        file_menu = tk.Menu(menubar, tearoff=0) # tearoff=0 impedisce di "staccare" il menu
        file_menu.add_command(label="Apri Immagine...", command=self.apri_immagine)
        file_menu.add_command(label="Apri Cartella...", command=self.apri_cartella)
        file_menu.add_separator() # Linea separatrice
        file_menu.add_command(label="Salva Immagine Come...", command=self.salva_immagine, state=tk.DISABLED) # Inizialmente disabilitato
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu) # Aggiunge il menu "File" alla barra
        self.file_menu = file_menu # Salva riferimento per poterlo modificare dopo

        # --- Menu Visualizza ---
        view_menu = tk.Menu(menubar, tearoff=0)
        # Radiobutton permettono una sola scelta tra Griglia e Presentazione
        view_menu.add_radiobutton(label="Griglia", variable=self.modalita_visualizzazione,
                                value="Griglia", command=self.cambia_visualizzazione)
        view_menu.add_radiobutton(label="Presentazione", variable=self.modalita_visualizzazione,
                                value="Presentazione", command=self.cambia_visualizzazione)
        menubar.add_cascade(label="Visualizza", menu=view_menu)
        self.view_menu = view_menu

        # --- Menu Steganografia ---
        steg_menu = tk.Menu(menubar, tearoff=0)
        # Checkbutton per attivare/disattivare la modalità
        steg_menu.add_checkbutton(label="Modalità Steganografia", variable=self.stegano_mode,
                                  command=self._toggle_stegano_mode)
        steg_menu.add_separator()
        # Comandi per nascondere/estrarre testo (inizialmente disabilitati)
        steg_menu.add_command(label="Nascondi Testo nell'Immagine...", command=self.nascondi_testo, state=tk.DISABLED)
        steg_menu.add_command(label="Estrai Testo dall'Immagine", command=self.estrai_testo, state=tk.DISABLED)
        menubar.add_cascade(label="Steganografia", menu=steg_menu)
        self.steg_menu = steg_menu

        # Applica la menubar creata alla finestra principale
        self.config(menu=menubar)

    # --- Metodo per Creare la Toolbar ---
    def _create_toolbar(self, parent):
        """Crea la barra degli strumenti con i bottoni principali e le icone."""
        toolbar = ttk.Frame(parent, padding=(5, 5))
        btn_compound = tk.LEFT # Posiziona l'icona a sinistra del testo nei bottoni

        # --- Caricamento Icone per la Toolbar ---
        icon_open_menu = self._load_icon("folder-plus.png")
        icon_save = self._load_icon("save.png")
        icon_grid = self._load_icon("grid.png")
        icon_prev = self._load_icon("arrow-left.png")
        icon_next = self._load_icon("arrow-right.png")
        icon_search = self._load_icon("search.png")
        # Icone specifiche per Steganografia
        icon_hide_text = self._load_icon("hide-text.png") # Es: icona lucchetto, occhio barrato
        icon_extract_text = self._load_icon("extract-text.png") # Es: icona chiave, occhio aperto
        icon_help = self._load_icon("help.png")# icona aiuto
        # --- Creazione Bottoni Toolbar ---

        # Menubutton "Apri" (un bottone che apre un menu a tendina)
        open_menubutton = ttk.Menubutton(toolbar, text="Apri", image=icon_open_menu,
                                         compound=btn_compound, bootstyle=INFO)
        open_menubutton.pack(side=tk.LEFT, padx=2)
        open_menu = tk.Menu(open_menubutton, tearoff=0) # Menu associato al Menubutton
        open_menu.add_command(label="Apri Immagine...", command=self.apri_immagine)
        open_menu.add_command(label="Apri Cartella...", command=self.apri_cartella)
        open_menubutton["menu"] = open_menu # Collega il menu al bottone

        # Bottone Salva
        self.btn_salva = ttk.Button(toolbar, text="Salva Come...", image=icon_save, compound=btn_compound,
                                    command=self.salva_immagine, bootstyle=SUCCESS, state=tk.DISABLED)
        self.btn_salva.pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y) # Separatore verticale

        # Bottone per tornare alla Griglia (visibile solo in Presentazione)
        self.btn_mostra_griglia = ttk.Button(toolbar, text="Griglia", image=icon_grid, compound=btn_compound,
                                             command=self.mostra_modalita_griglia, bootstyle=INFO, state=tk.DISABLED)
        self.btn_mostra_griglia.pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        # Bottoni Navigazione (Precedente/Successivo)
        self.btn_prev = ttk.Button(toolbar, text="Prec", image=icon_prev, compound=btn_compound,
                                   command=self.mostra_precedente, bootstyle=SECONDARY, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=2)
        self.btn_next = ttk.Button(toolbar, text="Succ", image=icon_next, compound=btn_compound,
                                   command=self.mostra_successivo, bootstyle=SECONDARY, state=tk.DISABLED)
        self.btn_next.pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        # Bottoni Steganografia (Nascondi/Estrai)
        self.btn_hide = ttk.Button(toolbar, text="Nascondi", image=icon_hide_text, compound=btn_compound,
                                   command=self.nascondi_testo, bootstyle=WARNING, state=tk.DISABLED)
        self.btn_hide.pack(side=tk.LEFT, padx=2)
        self.btn_extract = ttk.Button(toolbar, text="Estrai", image=icon_extract_text, compound=btn_compound,
                                      command=self.estrai_testo, bootstyle=WARNING, state=tk.DISABLED)
        self.btn_extract.pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        # --- Widget Ricerca (allineati a destra) ---
        self.btn_help = ttk.Button(toolbar, text="Aiuto", image=icon_help, compound=btn_compound, command=self.mostra_info, bootstyle=INFO)#Usa la stessa funzione del menu
        self.btn_help.pack(side=tk.RIGHT, padx=5)
        search_frame = ttk.Frame(toolbar) # Frame contenitore per allineare a destra
        search_frame.pack(side=tk.RIGHT, padx=5)
        self.btn_cerca = ttk.Button(search_frame, text="Cerca", image=icon_search, compound=btn_compound,
                                    command=self.cerca_immagini, bootstyle=PRIMARY, state=tk.DISABLED)
        self.btn_cerca.pack(side=tk.RIGHT) # Bottone a destra nel frame
        self.txt_ricerca = ttk.Entry(search_frame, width=20) # Campo di testo per la ricerca
        self.txt_ricerca.pack(side=tk.RIGHT, padx=5) # Campo testo a sinistra del bottone Cerca

        return toolbar

    # --- Metodo per Creare l'Area di Visualizzazione ---
    def _create_display_area(self, parent):
        """Crea l'area centrale dove verranno mostrate la griglia o l'immagine singola."""
        display_frame = ttk.Frame(parent) # Contenitore principale
        # Frame interno che conterrà alternativamente la griglia o la presentazione
        self.frame_immagini_container = ttk.Frame(display_frame)
        self.frame_immagini_container.pack(fill=tk.BOTH, expand=True)

        # Frame per la visualizzazione a griglia (inizialmente vuoto e non visibile)
        self.frame_griglia = ttk.Frame(self.frame_immagini_container)
        # Frame per la visualizzazione a presentazione (singola immagine)
        self.frame_presentazione = ttk.Frame(self.frame_immagini_container)

        # Canvas: l'area "disegnabile" dove mostrare l'immagine in modalità presentazione
        canvas_bg = self.style.lookup('TFrame', 'background') # Usa colore sfondo del tema
        self.canvas_immagine = tk.Canvas(self.frame_presentazione, bg=canvas_bg, highlightthickness=0) # highlightthickness=0 toglie bordo
        self.canvas_immagine.pack(fill=tk.BOTH, expand=True) # Occupa tutto lo spazio del frame presentazione

        return display_frame

    # --- Metodo per Creare il Pannello Dettagli ---
    def _create_details_panel(self, parent):
        """Crea il pannello inferiore per i dettagli immagine o l'input/output steganografia."""
        # LabelFrame: un frame con un bordo e un titolo
        details_frame_outer = ttk.LabelFrame(parent, text="Dettagli / Steganografia")
        details_frame_outer.pack(fill=X, padx=10, pady=5)

        # Checkbutton per attivare/disattivare la modalità Steganografia
        self.stegano_toggle_btn = ttk.Checkbutton(
            details_frame_outer,
            text="Modalità Steganografia (Modifica Testo)",
            variable=self.stegano_mode, # Collega alla variabile di stato
            command=self._toggle_stegano_mode, # Funzione chiamata al click
            bootstyle="info-round-toggle" # Stile "interruttore" arrotondato
        )
        self.stegano_toggle_btn.pack(anchor=tk.W, pady=(0, 5)) # Allinea a sinistra, con spazio sotto

        # Area di testo scorrevole per mostrare dettagli o inserire/mostrare testo nascosto
        self.area_dettagli = scrolledtext.ScrolledText(details_frame_outer, height=4, wrap=tk.WORD, # wrap=WORD manda a capo parole intere
                                                     padx=5, pady=5, state=tk.DISABLED, relief=tk.FLAT, borderwidth=1) # Inizialmente non modificabile
        self.area_dettagli.pack(fill=tk.BOTH, expand=True) # Occupa lo spazio rimanente nel pannello

        return details_frame_outer

    # --- Metodo per Creare la Barra Filtri ---
    def _create_filter_bar(self, parent):
        """Crea la barra in basso con i checkbox per filtrare i tipi di file."""
        filter_frame = ttk.Frame(parent, padding=(0, 5))
        chk_style = ('info', 'round-toggle') # Stile "interruttore" per i filtri
        ttk.Label(filter_frame, text="Filtri:").pack(side=tk.LEFT, padx=(0, 5))

        # Crea un Checkbutton per ogni formato supportato
        ttk.Checkbutton(filter_frame, text="JPEG", variable=self.filtro_jpeg,
                        command=self.applica_filtri, bootstyle=chk_style).pack(side=tk.LEFT, padx=3)
        ttk.Checkbutton(filter_frame, text="PNG", variable=self.filtro_png,
                        command=self.applica_filtri, bootstyle=chk_style).pack(side=tk.LEFT, padx=3)
        ttk.Checkbutton(filter_frame, text="GIF", variable=self.filtro_gif,
                        command=self.applica_filtri, bootstyle=chk_style).pack(side=tk.LEFT, padx=3)
        ttk.Checkbutton(filter_frame, text="BMP", variable=self.filtro_bmp,
                        command=self.applica_filtri, bootstyle=chk_style).pack(side=tk.LEFT, padx=3)
        return filter_frame

    # --- Metodo per Associare Eventi ---
    def _bind_events(self):
        """Collega eventi dell'interfaccia (es. tasti, resize) a metodi specifici."""
        # Evento <Configure> viene generato quando la finestra cambia dimensione
        self.bind("<Configure>", self._handle_resize)
        # Tasti freccia sinistra/destra per navigare tra le immagini
        self.bind("<Left>", lambda e: self.mostra_precedente() if self.immagini else None)
        self.bind("<Right>", lambda e: self.mostra_successivo() if self.immagini else None)
        # Tasto Invio nel campo di ricerca esegue la ricerca
        self.txt_ricerca.bind("<Return>", lambda e: self.cerca_immagini())
        self.txt_ricerca.bind("<KP_Enter>", lambda e: self.cerca_immagini()) # Invio da tastierino numerico

        self.txt_ricerca.bind("<KeyRelease>", self._on_search_change)

    # --- Metodo per Aggiornamento UI Iniziale ---
    def _initial_ui_update(self):
        """Imposta lo stato iniziale dell'interfaccia dopo la creazione dei widget."""
        self._toggle_stegano_mode() # Applica lo stato iniziale del pannello dettagli/stegano
        self.cambia_visualizzazione() # Mostra la vista iniziale (Griglia vuota)

    # --- Gestione Eventi ---
    def _handle_resize(self, event=None):
        """Chiamato quando la finestra viene ridimensionata."""
        # Se siamo in modalità Presentazione e ci sono immagini, ridisegna l'immagine corrente
        if self.modalita_visualizzazione.get() == "Presentazione" and self.immagini:
            # Usa after per ritardare leggermente, assicurando che le dimensioni del canvas siano aggiornate
            self.after(50, self.mostra_immagine_corrente)
        # La griglia si ridimensiona automaticamente grazie al binding sul suo canvas interno

    # --- Logica Applicazione ---

    def cambia_visualizzazione(self):
        """Passa dalla visualizzazione Griglia a Presentazione e viceversa."""
        current_mode = self.modalita_visualizzazione.get()
        # Nasconde entrambi i frame principali (griglia e presentazione)
        self.frame_presentazione.pack_forget()
        self.frame_griglia.pack_forget()

        if current_mode == "Griglia":
            # Mostra il frame della griglia e la popola
            self.frame_griglia.pack(fill=tk.BOTH, expand=True)
            self.mostra_griglia()
        else: # Modalità Presentazione
            # Mostra il frame della presentazione e l'immagine corrente
            self.frame_presentazione.pack(fill=tk.BOTH, expand=True)
            # Usa after per assicurarsi che il canvas abbia dimensioni prima di disegnare
            self.after(50, self.mostra_immagine_corrente)

        # Aggiorna lo stato dei bottoni, menu, barra stato, etc.
        self.aggiorna_stato()

    def aggiorna_stato(self):
        """Aggiorna la barra di stato e abilita/disabilita i controlli UI in base allo stato corrente."""
        num_immagini = len(self.immagini)
        current_index = self.indice_corrente.get()
        is_valid_index = 0 <= current_index < num_immagini # C'è un'immagine valida selezionata?
        is_griglia = self.modalita_visualizzazione.get() == "Griglia"
        in_stegano_mode = self.stegano_mode.get() # Siamo in modalità steganografia?

        # --- Verifica se l'immagine corrente è adatta per steganografia ---
        can_stegano = False # Può fare operazioni di steganografia sull'immagine corrente?
        is_png = False # L'immagine corrente è PNG? (Ideale per steganografia LSB)
        if is_valid_index:
            try:
                path = self.immagini[current_index].get("path", "")
                if path and path.lower().endswith(".png"):
                    can_stegano = True # PNG è ottimo
                    is_png = True
                elif path and any(path.lower().endswith(ext) for ext in self.ALL_SUPPORTED_EXT_FLAT):
                    # Permetti estrazione anche da altri formati (potrebbe fallire)
                    # Permetti nascondi (ma avviserà e salverà come PNG)
                    can_stegano = True
            except Exception:
                pass # Ignora errori nel controllo del path

        # --- Aggiorna Testo Barra di Stato ---
        status_text = "Nessuna immagine caricata"
        if is_valid_index:
            indice_display = current_index + 1
            status_text = f"Img: {indice_display}/{num_immagini}"
            try: # Aggiunge nome file e cartella se possibile
                nome_file = os.path.basename(self.immagini[current_index]["path"])
                cartella = os.path.basename(self.directory_corrente) or self.directory_corrente
                status_text += f" | {nome_file} | Cartella: {cartella}"
            except Exception: pass
        if in_stegano_mode:
            status_text += " | Modalità Steganografia ATTIVA" # Indica se la modalità è attiva
        self.barra_stato.config(text=status_text)

        # --- Determina Stato Abilitazione Controlli ---
        nav_state = tk.NORMAL if num_immagini > 1 else tk.DISABLED # Navigazione attiva solo con >1 immagine
        save_state = tk.NORMAL if is_valid_index else tk.DISABLED # Salva attivo solo se c'è immagine
        search_state = tk.NORMAL if self.directory_corrente else tk.DISABLED # Cerca attivo solo se una cartella è aperta
        grid_btn_state = tk.NORMAL if not is_griglia and self.immagini else tk.DISABLED # Bottone Griglia attivo solo in Presentazione con immagini

        # Stato controlli Steganografia
        stegano_general_state = tk.NORMAL if can_stegano else tk.DISABLED # Toggle e menu base attivi se l'immagine è potenzialmente compatibile
        stegano_hide_state = tk.NORMAL if can_stegano and in_stegano_mode else tk.DISABLED # Nascondi attivo solo se compatibile E in modalità stegano
        stegano_extract_state = tk.NORMAL if can_stegano and in_stegano_mode else tk.DISABLED # Estrai attivo solo se compatibile E in modalità stegano

        # --- Applica Stati ai Widget ---
        # Toolbar
        self.btn_prev.config(state=nav_state)
        self.btn_next.config(state=nav_state)
        self.btn_salva.config(state=save_state)
        self.btn_cerca.config(state=search_state)
        self.txt_ricerca.config(state=search_state) # Abilita/disabilita anche campo ricerca
        self.btn_mostra_griglia.config(state=grid_btn_state)
        self.btn_hide.config(state=stegano_hide_state)
        self.btn_extract.config(state=stegano_extract_state)
        # Pannello Dettagli/Stegano
        self.stegano_toggle_btn.config(state=stegano_general_state) # Abilita/disabilita il toggle stesso

        # Menu (usa try/except perché il menu potrebbe non essere pronto all'inizio)
        try:
            self.file_menu.entryconfig("Salva Immagine Come...", state=save_state)
            # Aggiorna voci menu Steganografia
            self.steg_menu.entryconfig("Modalità Steganografia", state=stegano_general_state)
            self.steg_menu.entryconfig("Nascondi Testo nell'Immagine...", state=stegano_hide_state)
            self.steg_menu.entryconfig("Estrai Testo dall'Immagine", state=stegano_extract_state)
        except tk.TclError: pass # Ignora errori se il menu non è ancora completamente creato

        # --- Gestisci Stato Area Dettagli ---
        # Se siamo in modalità steganografia, l'area deve essere modificabile
        if in_stegano_mode:
            # Assicurati che sia modificabile (potrebbe essere già NORMAL)
            try: self.area_dettagli.config(state=tk.NORMAL)
            except tk.TclError: pass
        else:
            # Se NON siamo in modalità steganografia, l'area mostra i dettagli e non è modificabile
            try:
                self.area_dettagli.config(state=tk.DISABLED)
                # Ricarica i dettagli immagine (sovrascrive eventuale testo stegano)
                self.aggiorna_dettagli()
            except tk.TclError: pass


    def mostra_modalita_griglia(self):
        """Forza la visualizzazione in modalità Griglia (usato dal bottone toolbar)."""
        if self.modalita_visualizzazione.get() != "Griglia":
            self.modalita_visualizzazione.set("Griglia")
            self.cambia_visualizzazione()

    def mostra_griglia(self):
        """Popola l'area della griglia con le miniature delle immagini caricate."""
        # Pulisci la griglia precedente
        for widget in self.frame_griglia.winfo_children():
            widget.destroy()

        # Se non ci sono immagini, mostra un messaggio
        if not self.immagini:
            ttk.Label(self.frame_griglia, text="Nessuna immagine da visualizzare.",
                      bootstyle=DEFAULT, font="-size 12", justify=tk.CENTER).pack(pady=50, padx=20, expand=True)
            return

        # --- Configurazione Canvas Scorrevole per la Griglia ---
        canvas_bg = self.style.lookup('TFrame', 'background')
        grid_canvas = tk.Canvas(self.frame_griglia, highlightthickness=0, bg=canvas_bg)
        scrollbar = ttk.Scrollbar(self.frame_griglia, orient=tk.VERTICAL, command=grid_canvas.yview, bootstyle=ROUND)
        # Frame interno al canvas che conterrà effettivamente le miniature
        scrollable_frame = ttk.Frame(grid_canvas)
        # Quando il frame interno cambia dimensione, aggiorna l'area scrollabile del canvas
        scrollable_frame.bind("<Configure>", lambda e: grid_canvas.configure(scrollregion=grid_canvas.bbox("all")))
        # Inserisce il frame scorrevole dentro il canvas
        canvas_window = grid_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        # Collega la scrollbar al canvas
        grid_canvas.configure(yscrollcommand=scrollbar.set)

        # --- Funzione per Riorganizzare la Griglia al Resize ---
        def _on_canvas_configure(event):
            """Chiamata quando il canvas della griglia viene ridimensionato."""
            canvas_width = event.width
            # Adatta la larghezza del frame interno a quella del canvas
            grid_canvas.itemconfig(canvas_window, width=canvas_width)
            # Ridisponi le miniature in base alla nuova larghezza
            self._organizza_griglia_items(scrollable_frame, canvas_width)
        # Collega la funzione all'evento <Configure> del canvas
        grid_canvas.bind("<Configure>", _on_canvas_configure)

        # Posiziona canvas e scrollbar
        grid_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Forza l'aggiornamento per ottenere le dimensioni iniziali e popola la griglia
        self.frame_griglia.update_idletasks()
        initial_width = max(1, grid_canvas.winfo_width()) # Evita larghezza 0
        self._organizza_griglia_items(scrollable_frame, initial_width)

    def _organizza_griglia_items(self, container_frame, available_width):
        """Dispone le miniature nel frame scorrevole in base alla larghezza disponibile."""
        # Pulisci il frame prima di ridisporre
        for widget in container_frame.winfo_children():
            widget.destroy()

        if not self.immagini or available_width <= 1: return # Niente da fare

        # Calcola quante colonne entrano nella larghezza disponibile
        grid_item_width = self.THUMBNAIL_SIZE[0] + self.THUMBNAIL_PADDING * 2
        cols = max(1, int(available_width // grid_item_width)) # Almeno 1 colonna

        row, col = 0, 0 # Indici per la griglia
        # Itera su tutte le immagini caricate
        for i, img_info in enumerate(self.immagini):
            path = img_info.get("path")
            if not path: continue # Salta se manca il percorso

            try:
                # --- Crea Elemento Griglia (Miniatura + Nome) ---
                # Frame contenitore per una singola miniatura
                item_frame = ttk.Frame(container_frame, borderwidth=1, relief=tk.SOLID, padding=self.THUMBNAIL_PADDING // 2, bootstyle=SECONDARY)

                # Carica, ridimensiona (thumbnail) e visualizza l'immagine
                img = Image.open(path)
                img_copy = img.copy() # Lavora su una copia
                img_copy.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS) # Ridimensiona mantenendo proporzioni
                photo = ImageTk.PhotoImage(img_copy)
                img.close() # Chiudi file originale

                img_label = ttk.Label(item_frame, image=photo)
                img_label.image = photo # Mantiene riferimento!
                img_label.pack(pady=(0, 5))

                # Mostra il nome del file (troncato se troppo lungo)
                nome_file = os.path.basename(path)
                display_name = (nome_file[:20] + '...') if len(nome_file) > 23 else nome_file
                name_label = ttk.Label(item_frame, text=display_name, anchor=tk.CENTER, justify=tk.CENTER, wraplength=self.THUMBNAIL_SIZE[0])
                name_label.pack(fill=tk.X)

                # --- Associa Evento Click ---
                # Funzione lambda cattura l'indice 'i' corrente per passarlo al metodo
                click_handler = lambda e, idx=i: self.seleziona_immagine_da_griglia(idx)
                # Rendi cliccabile il frame, l'immagine e il nome
                item_frame.bind("<Button-1>", click_handler)
                img_label.bind("<Button-1>", click_handler)
                name_label.bind("<Button-1>", click_handler)

                # Posiziona il frame nella griglia
                item_frame.grid(row=row, column=col, padx=self.THUMBNAIL_PADDING // 2, pady=self.THUMBNAIL_PADDING // 2, sticky="nsew")

                # Passa alla cella successiva
                col += 1
                if col >= cols: # Se abbiamo riempito la riga
                    col = 0 # Torna alla prima colonna
                    row += 1 # Passa alla riga successiva

            except Exception as e: # Gestione errori caricamento miniatura
                print(f"Errore Griglia: Caricamento miniatura {path}: {e}")
                # Crea un placeholder di errore al posto della miniatura
                error_frame = ttk.Frame(container_frame, bootstyle=DANGER, borderwidth=1, relief=tk.SOLID, padding=5,
                                        width=self.THUMBNAIL_SIZE[0], height=self.THUMBNAIL_SIZE[1])
                error_frame.grid(row=row, column=col, padx=self.THUMBNAIL_PADDING // 2, pady=self.THUMBNAIL_PADDING // 2, sticky="nsew")
                error_frame.grid_propagate(False) # Impedisce al frame di restringersi
                ttk.Label(error_frame, text=f"ERRORE\n{os.path.basename(path)}", bootstyle=(INVERSE, DANGER),
                          wraplength=self.THUMBNAIL_SIZE[0] - 10, justify=tk.CENTER, anchor=tk.CENTER).pack(expand=True, fill=tk.BOTH)
                # Passa comunque alla cella successiva
                col += 1;
                if col >= cols: col = 0; row += 1

        # Configura le colonne del container_frame per espandersi uniformemente
        for c in range(cols):
            container_frame.columnconfigure(c, weight=1, uniform="grid_col")

        # Aggiorna il layout per ricalcolare le dimensioni (necessario per scrollregion)
        container_frame.update_idletasks()

    def seleziona_immagine_da_griglia(self, indice):
        """Chiamato quando si clicca su una miniatura nella griglia."""
        if 0 <= indice < len(self.immagini):
            self.indice_corrente.set(indice) # Imposta l'indice selezionato
            self.modalita_visualizzazione.set("Presentazione") # Passa a modalità presentazione
            self.cambia_visualizzazione() # Aggiorna l'interfaccia
        else:
            # Questo non dovrebbe succedere se la griglia è corretta
            print(f"Indice non valido selezionato dalla griglia: {indice}")

    def mostra_immagine_corrente(self):
        """Visualizza l'immagine attualmente selezionata nell'area di presentazione."""
        # Pulisci il canvas da disegni precedenti
        self.canvas_immagine.delete("all")
        self.current_photo_image = None # Rilascia riferimento vecchia immagine

        current_index = self.indice_corrente.get()
        # Se non ci sono immagini o l'indice non è valido
        if not self.immagini or not (0 <= current_index < len(self.immagini)):
            # Mostra un messaggio sul canvas vuoto
            self.canvas_immagine.update_idletasks() # Assicura dimensioni canvas
            cw, ch = self.canvas_immagine.winfo_width(), self.canvas_immagine.winfo_height()
            if cw > 1 and ch > 1: # Disegna solo se il canvas è visibile
                 self.canvas_immagine.create_text(cw/2, ch/2, text="Nessuna immagine selezionata",
                                                  fill=self.style.lookup('TLabel', 'foreground'), # Colore testo del tema
                                                  font="-size 14", anchor=tk.CENTER)
            self.aggiorna_dettagli() # Aggiorna comunque i dettagli (mostrerà vuoto)
            self.aggiorna_stato() # Aggiorna stato bottoni etc.
            return

        # --- Carica e Visualizza Immagine ---
        img_info = self.immagini[current_index]
        path = img_info.get("path")
        if not path:
             messagebox.showerror("Errore", "Percorso immagine mancante.")
             self.aggiorna_dettagli(); self.aggiorna_stato(); return

        try:
            # Apre l'immagine con PIL
            img = Image.open(path)

            # Ottieni dimensioni canvas (dopo update_idletasks per sicurezza)
            self.canvas_immagine.update_idletasks()
            canvas_width = self.canvas_immagine.winfo_width()
            canvas_height = self.canvas_immagine.winfo_height()

            # Se il canvas non ha ancora dimensioni, riprova tra poco
            if canvas_width <= 1 or canvas_height <= 1:
                self.after(100, self.mostra_immagine_corrente); return

            # --- Ridimensiona Immagine per Adattarla al Canvas ---
            img_width, img_height = img.size
            # Calcola il rapporto di ridimensionamento per far stare l'immagine nel canvas
            ratio = min(canvas_width / img_width, canvas_height / img_height)
            # Calcola nuove dimensioni (assicurandosi che siano almeno 1 pixel)
            new_width = max(1, int(img_width * ratio))
            new_height = max(1, int(img_height * ratio))

            # Ridimensiona l'immagine
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Converti in formato Tkinter
            self.current_photo_image = ImageTk.PhotoImage(img_resized)
            img.close() # Chiudi file originale

            # --- Posiziona Immagine al Centro del Canvas ---
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            # Disegna l'immagine sul canvas
            self.canvas_immagine.create_image(x, y, anchor=tk.NW, image=self.current_photo_image)

            # Aggiorna dettagli e stato DOPO aver mostrato l'immagine
            self.aggiorna_dettagli()
            self.aggiorna_stato()

        except UnidentifiedImageError: # Errore specifico PIL per formati non riconosciuti
             messagebox.showerror("Errore Formato", f"Formato immagine non riconosciuto o file corrotto:\n{path}")
             self.aggiorna_dettagli(); self.aggiorna_stato()
        except Exception as e: # Altri errori (es. file non trovato se cancellato dopo apertura cartella)
            messagebox.showerror("Errore Visualizzazione", f"Impossibile visualizzare l'immagine:\n{path}\n\nErrore: {e}")
            traceback.print_exc() # Stampa errore dettagliato in console
            self.aggiorna_dettagli(); self.aggiorna_stato()

    def aggiorna_dettagli(self):
        """Recupera e visualizza i dettagli dell'immagine corrente SE non in modalità stegano."""
        # Se siamo in modalità steganografia, l'area dettagli serve per input/output testo, non mostrare dettagli immagine
        if self.stegano_mode.get():
            return # Esce subito

        # --- Se NON in modalità stegano, mostra i dettagli ---
        try:
            # Rendi l'area modificabile temporaneamente per pulirla
            self.area_dettagli.config(state=tk.NORMAL)
            self.area_dettagli.delete(1.0, tk.END) # Cancella contenuto precedente
        except tk.TclError: return # Ignora se l'area non esiste ancora

        current_index = self.indice_corrente.get()
        # Se non c'è immagine selezionata, lascia l'area vuota e disabilitala
        if not self.immagini or not (0 <= current_index < len(self.immagini)):
            self.area_dettagli.config(state=tk.DISABLED); return

        # --- Recupera e Formatta Dettagli Immagine ---
        img_info = self.immagini[current_index]
        path = img_info.get("path")
        if not path:
             self.area_dettagli.insert(tk.END, "Errore: Percorso mancante."); self.area_dettagli.config(state=tk.DISABLED); return

        try:
            # Prova a leggere dimensioni e formato con PIL (apre solo header se possibile)
            img_width, img_height, img_format = "N/D", "N/D", "N/D" # Valori default
            try:
                 with Image.open(path) as img:
                     img_width, img_height = img.size; img_format = img.format or "N/D"
            except Exception as e: print(f"WARN: Impossibile leggere dettagli PIL per {path}: {e}") # Avviso non bloccante

            # Ottieni nome file e dimensione da OS
            nome_file = os.path.basename(path)
            dimensione_bytes = 0; dim_str = "N/D"
            try:
                 dimensione_bytes = os.path.getsize(path)
                 dim_kb = dimensione_bytes / 1024; dim_mb = dim_kb / 1024
                 if dim_mb >= 1: dim_str = f"{dim_mb:.1f} MB" # Mostra in MB se >= 1
                 elif dimensione_bytes > 0: dim_str = f"{dim_kb:.1f} KB" # Altrimenti in KB
            except OSError: pass # Ignora se non può leggere dimensione

            # Componi la stringa dei dettagli
            dettagli = f"Nome: {nome_file}\n"
            dettagli += f"Dimensione: {dim_str}\n"
            dettagli += f"Dimensioni: {img_width} × {img_height} px\n"
            dettagli += f"Formato: {img_format}"

            # Inserisci i dettagli nell'area di testo
            self.area_dettagli.insert(tk.END, dettagli)
        except Exception as e: # Errore generico lettura metadati
            self.area_dettagli.insert(tk.END, f"Errore lettura metadati:\n{e}")

        # Infine, rendi l'area di nuovo non modificabile
        self.area_dettagli.config(state=tk.DISABLED)

    def mostra_precedente(self):
        """Passa all'immagine precedente nella lista (ciclico)."""
        if not self.immagini or len(self.immagini) <= 1: return # Niente da fare
        current_index = self.indice_corrente.get()
        num_immagini = len(self.immagini)
        # Calcola nuovo indice (gestisce il caso in cui siamo al primo elemento)
        nuovo_indice = (current_index - 1 + num_immagini) % num_immagini
        self.indice_corrente.set(nuovo_indice)

        # Aggiorna la visualizzazione
        if self.modalita_visualizzazione.get() == "Presentazione":
            self.mostra_immagine_corrente() # Ridisegna immagine
        else: # In modalità Griglia, non serve ridisegnare tutto
            # Aggiorna solo dettagli (se non in stegano mode) e stato
            if not self.stegano_mode.get():
                self.aggiorna_dettagli()
            self.aggiorna_stato()

    def mostra_successivo(self):
        """Passa all'immagine successiva nella lista (ciclico)."""
        if not self.immagini or len(self.immagini) <= 1: return # Niente da fare
        current_index = self.indice_corrente.get()
        num_immagini = len(self.immagini)
        # Calcola nuovo indice (gestisce il caso in cui siamo all'ultimo elemento)
        nuovo_indice = (current_index + 1) % num_immagini
        self.indice_corrente.set(nuovo_indice)

        # Aggiorna la visualizzazione
        if self.modalita_visualizzazione.get() == "Presentazione":
            self.mostra_immagine_corrente()
        else:
            if not self.stegano_mode.get():
                self.aggiorna_dettagli()
            self.aggiorna_stato()

    # --- Operazioni File ---

    def apri_immagine(self):
        """Apre una singola immagine selezionata dall'utente."""
        # Chiede all'utente di selezionare un file
        file_path = filedialog.askopenfilename(title="Seleziona un'immagine", filetypes=self.FILEDIALOG_TYPES)
        if not file_path: return # Utente ha annullato

        try:
            # Verifica rapida se PIL può aprire l'immagine (legge solo header)
            with Image.open(file_path) as img: img.verify()

            # Aggiorna stato applicazione
            self.directory_corrente = os.path.dirname(file_path) # Memorizza cartella
            self.immagini = [{"path": file_path}] # Lista con solo questa immagine
            self.indice_corrente.set(0) # Seleziona la prima (e unica) immagine
            self.txt_ricerca.delete(0, tk.END) # Pulisci campo ricerca
            self.modalita_visualizzazione.set("Presentazione") # Mostra subito l'immagine singola
            self.cambia_visualizzazione() # Aggiorna UI (mostra immagine, stato, dettagli)
        except UnidentifiedImageError: # Errore specifico PIL
             messagebox.showerror("Errore Formato", f"Formato immagine non riconosciuto o file corrotto:\n{file_path}")
             # Resetta stato se apertura fallisce
             self.immagini = []; self.indice_corrente.set(-1); self.cambia_visualizzazione()
        except Exception as e: # Altri errori
            messagebox.showerror("Errore Apertura", f"Impossibile aprire o verificare l'immagine:\n{file_path}\n\nErrore: {e}")
            traceback.print_exc()
            self.immagini = []; self.indice_corrente.set(-1); self.cambia_visualizzazione()

    def apri_cartella(self):
        """Apre una cartella selezionata dall'utente e carica le immagini."""
        # Chiede all'utente di selezionare una cartella
        directory = filedialog.askdirectory(title="Seleziona una cartella", mustexist=True) # mustexist=True richiede che la cartella esista
        if directory: # Se l'utente non ha annullato
            self.directory_corrente = directory # Memorizza cartella
            self.txt_ricerca.delete(0, tk.END) # Pulisci campo ricerca
            self.carica_immagini_da_cartella(directory) # Carica le immagini

    def _get_active_extensions(self):
        """Restituisce una lista delle estensioni di file attualmente attive nei filtri."""
        estensioni = []
        if self.filtro_jpeg.get(): estensioni.extend(self.SUPPORTED_EXT_MAP['JPEG'])
        if self.filtro_png.get(): estensioni.extend(self.SUPPORTED_EXT_MAP['PNG'])
        if self.filtro_gif.get(): estensioni.extend(self.SUPPORTED_EXT_MAP['GIF'])
        if self.filtro_bmp.get(): estensioni.extend(self.SUPPORTED_EXT_MAP['BMP'])
        return estensioni

    def carica_immagini_da_cartella(self, directory, termine_ricerca=""):
        """Scansiona una cartella, filtra i file per estensione e termine di ricerca, e aggiorna la lista immagini."""
        self.immagini = [] # Pulisci lista precedente
        active_extensions = self._get_active_extensions() # Ottieni estensioni dai filtri
        termine_ricerca = termine_ricerca.strip().lower() # Pulisci e metti in minuscolo il termine di ricerca

        # Se nessun filtro è attivo, non caricare nulla e avvisa
        if not active_extensions:
            messagebox.showwarning("Nessun Filtro Attivo", "Selezionare almeno un formato di immagine nei filtri.")
            self.indice_corrente.set(-1); self.cambia_visualizzazione(); return

        immagini_trovate = []
        try:
            # Ordina i file alfabeticamente (case-insensitive)
            files_in_dir = sorted(os.listdir(directory), key=str.lower)
            # Itera su tutti i file nella cartella
            for filename in files_in_dir:
                file_path = os.path.join(directory, filename)
                # Controlla se è un file (e non una sottocartella)
                if os.path.isfile(file_path):
                    name_lower = filename.lower()
                    # Verifica se l'estensione è tra quelle attive
                    has_valid_ext = any(name_lower.endswith(ext) for ext in active_extensions)
                    # Verifica se il nome file contiene il termine di ricerca (se presente)
                    matches_search = not termine_ricerca or termine_ricerca in name_lower
                    # Se entrambe le condizioni sono vere, aggiungi alla lista
                    if has_valid_ext and matches_search:
                        immagini_trovate.append({"path": file_path})

            # Aggiorna la lista principale e l'indice
            self.immagini = immagini_trovate
            if self.immagini:
                self.indice_corrente.set(0) # Seleziona la prima immagine trovata
                # Aggiorna barra stato con numero immagini
                status_msg = f"Caricate {len(self.immagini)} immagini"
                if termine_ricerca: status_msg += f" per '{termine_ricerca}'"
                self.barra_stato.config(text=status_msg)
            else:
                # Se non trova immagini, resetta indice e mostra messaggio
                self.indice_corrente.set(-1)
                info_msg = f"Nessuna immagine trovata{' per ' + termine_ricerca if termine_ricerca else ''} con i filtri attivi."
                # Mostra popup solo se non era una ricerca (altrimenti è ovvio che non ha trovato)
                if not termine_ricerca: messagebox.showinfo("Nessuna Immagine", f"{info_msg}\nCartella: {directory}")
                self.barra_stato.config(text="Nessuna immagine trovata")

            # Aggiorna la visualizzazione (mostra griglia/presentazione vuota o con le nuove immagini)
            self.cambia_visualizzazione()

        except Exception as e: # Errore durante lettura cartella
            messagebox.showerror("Errore Caricamento Cartella", f"Impossibile leggere la cartella:\n{directory}\n\nErrore: {e}")
            traceback.print_exc()
            self.indice_corrente.set(-1); self.cambia_visualizzazione() # Resetta stato

    def salva_immagine(self):
        """Salva l'immagine corrente in un nuovo file, permettendo conversione formato base."""
        current_index = self.indice_corrente.get()
        # Controlla se c'è un'immagine selezionata
        if not self.immagini or not (0 <= current_index < len(self.immagini)):
            messagebox.showwarning("Nessuna Immagine", "Nessuna immagine selezionata da salvare."); return

        img_path_originale = self.immagini[current_index].get("path")
        if not img_path_originale: messagebox.showerror("Errore", "Percorso originale mancante."); return

        # Prepara dialogo "Salva Come..."
        nome_file_originale = os.path.basename(img_path_originale)
        _, ext_originale = os.path.splitext(nome_file_originale)
        # Chiede all'utente nome e percorso per il nuovo file
        file_path_salvataggio = filedialog.asksaveasfilename(
            title="Salva immagine come...",
            initialdir=self.directory_corrente or os.path.expanduser("~"), # Parte dalla cartella corrente o home
            initialfile=nome_file_originale, # Suggerisce nome originale
            defaultextension=ext_originale, # Suggerisce estensione originale
            filetypes=self.SAVE_FILEDIALOG_TYPES # Mostra i tipi di file per salvare
        )
        if not file_path_salvataggio: return # Utente ha annullato

        try:
            # Apre l'immagine originale
            with Image.open(img_path_originale) as img:
                save_format_ext = os.path.splitext(file_path_salvataggio)[1].lower()
                img_to_save = img # Immagine da salvare (potrebbe essere convertita)

                # --- Gestione Conversione Formato (opzionale ma utile) ---
                # Se salva come JPG e l'originale ha trasparenza (RGBA), la rimuove (es. sfondo bianco)
                if save_format_ext in ['.jpg', '.jpeg']:
                    if img.mode == 'RGBA' or 'A' in img.mode:
                        # Crea sfondo bianco e incolla immagine sopra usando maschera alpha
                        img_to_save = Image.new("RGB", img.size, (255, 255, 255))
                        try: img_to_save.paste(img, mask=img.split()[3]) # Indice 3 è il canale Alpha
                        except Exception: img_to_save = img.convert('RGB') # Fallback: conversione semplice
                    elif img.mode != 'RGB' and img.mode != 'L': # Converti altri modi (es. P, LA) a RGB
                        img_to_save = img.convert('RGB')
                # Se salva come BMP e ha trasparenza, converti a RGB (BMP non la supporta)
                elif save_format_ext == '.bmp':
                     if img_to_save.mode == 'RGBA' or 'A' in img_to_save.mode:
                          img_to_save = img_to_save.convert('RGB')

                # Salva l'immagine (PIL determina formato da estensione se non specificato)
                img_to_save.save(file_path_salvataggio)

            # Aggiorna barra stato
            self.barra_stato.config(text=f"Immagine salvata: {os.path.basename(file_path_salvataggio)}")
        except Exception as e: # Errore durante salvataggio
            messagebox.showerror("Errore Salvataggio", f"Impossibile salvare l'immagine:\n{file_path_salvataggio}\n\nErrore: {e}")
            traceback.print_exc()

    def cerca_immagini(self):
        """Esegue una ricerca di immagini nella cartella corrente usando il testo nel campo di ricerca."""
        # Controlla se una cartella è aperta
        if not self.directory_corrente:
            messagebox.showwarning("Nessuna Cartella Aperta", "Aprire prima una cartella per poter effettuare una ricerca.")
            return
        # Ottieni il termine di ricerca dal campo di testo
        termine_ricerca = self.txt_ricerca.get()
        # Ricarica le immagini applicando il filtro di ricerca
        self.carica_immagini_da_cartella(self.directory_corrente, termine_ricerca)

    def applica_filtri(self):
        """Ricarica le immagini dalla cartella corrente quando un filtro viene cambiato."""
        # Funziona solo se una cartella è già stata aperta
        if self.directory_corrente:
            # Esegue una nuova ricerca (con termine vuoto se non c'è nulla nel campo)
            # Questo ricaricherà la lista usando i filtri aggiornati
            self.cerca_immagini()

    # --- Metodi Steganografia ---

    def _toggle_stegano_mode(self):
        """Attiva/Disattiva la modalità steganografia, cambiando l'aspetto e la funzione del pannello dettagli."""
        if self.stegano_mode.get():
            # --- Entra in Modalità Steganografia ---
            try:
                self.area_dettagli.config(state=tk.NORMAL) # Rende l'area di testo modificabile
                self.area_dettagli.delete(1.0, tk.END)     # Cancella i dettagli immagine precedenti
                # Inserisce un testo guida
                placeholder_text = "Inserisci qui il testo da nascondere o visualizza il testo estratto."
                self.area_dettagli.insert(tk.END, placeholder_text)

                # Posiziona il cursore all'inizio e deseleziona il testo placeholder
                self.area_dettagli.mark_set(tk.INSERT, "1.0")
                self.area_dettagli.tag_remove(tk.SEL, "1.0", tk.END)
                # self.area_dettagli.focus_set() # Opzionale: dà focus all'area

                # Cambia il titolo del pannello
                self.details_panel.config(text="Steganografia (Testo Nascosto)")
            except tk.TclError:
                 print("Errore: Impossibile configurare l'area dettagli (potrebbe non esistere).")

        else:
            # --- Esce dalla Modalità Steganografia ---
            try:
                # Rende l'area di testo non modificabile
                self.area_dettagli.config(state=tk.DISABLED)
                # Ripristina il titolo originale del pannello
                self.details_panel.config(text="Dettagli Immagine")
                # Ricarica i dettagli dell'immagine corrente (cancella eventuale testo stegano)
                self.aggiorna_dettagli()
            except tk.TclError:
                 print("Errore: Impossibile configurare l'area dettagli (potrebbe non esistere).")

        # Aggiorna lo stato di tutti i controlli (specialmente i bottoni/menu stegano)
        self.aggiorna_stato()

    def nascondi_testo(self):
        """Nasconde il testo dall'area dettagli nell'immagine corrente, salvando come NUOVO file PNG."""
        current_index = self.indice_corrente.get()
        # Controlli preliminari
        if not self.immagini or not (0 <= current_index < len(self.immagini)):
            messagebox.showwarning("Nessuna Immagine", "Seleziona un'immagine prima di nascondere il testo.")
            return

        img_path_originale = self.immagini[current_index].get("path")
        if not img_path_originale:
            messagebox.showerror("Errore", "Percorso immagine originale mancante.")
            return

        # Ottieni il testo dall'area, rimuovendo spazi bianchi iniziali/finali
        testo_da_nascondere = self.area_dettagli.get(1.0, tk.END).strip()
        # Controlla se c'è testo effettivo da nascondere (diverso dal placeholder)
        if not testo_da_nascondere or testo_da_nascondere == "Inserisci qui il testo da nascondere o visualizza il testo estratto.":
            messagebox.showwarning("Testo Mancante", "Inserisci il testo da nascondere nell'area di testo.")
            return

        # --- Avviso se l'immagine originale non è PNG ---
        if not img_path_originale.lower().endswith(".png"):
            # Chiedi conferma all'utente perché il salvataggio forzerà il formato PNG
            if not messagebox.askyesno("Formato Immagine", "L'immagine originale non è PNG. La steganografia funziona meglio con PNG (lossless).\nIl file risultante verrà salvato come PNG.\n\nContinuare?"):
                return # Utente ha annullato

        # --- Chiedi dove salvare il NUOVO file PNG con testo nascosto ---
        # Suggerisce un nome file (es. originale_con_testo.png)
        nome_file_suggerito = os.path.splitext(os.path.basename(img_path_originale))[0] + "_con_testo.png"
        file_path_salvataggio = filedialog.asksaveasfilename(
            title="Salva immagine con testo nascosto come...",
            initialdir=self.directory_corrente or os.path.expanduser("~"),
            initialfile=nome_file_suggerito,
            defaultextension=".png", # Forza estensione .png
            filetypes=self.STEGANO_SAVE_FILETYPES # Mostra solo opzione PNG
        )
        if not file_path_salvataggio:
            return # Utente ha annullato

        # Assicura che l'estensione sia .png (asksaveasfilename non sempre la aggiunge)
        if not file_path_salvataggio.lower().endswith(".png"):
            file_path_salvataggio += ".png"

        # --- Esegui Steganografia (Nascondi) ---
        try:
            # Usa la libreria stegano per nascondere il testo nell'immagine originale
            # NOTA: lsb.hide() carica l'immagine, nasconde il testo e restituisce un NUOVO oggetto Immagine PIL
            secret_image = lsb.hide(img_path_originale, testo_da_nascondere)
            # Salva la nuova immagine (che contiene il testo nascosto) nel percorso scelto
            secret_image.save(file_path_salvataggio)

            # Messaggio di successo
            messagebox.showinfo("Successo", f"Testo nascosto con successo!\nImmagine salvata come:\n{file_path_salvataggio}")
            self.barra_stato.config(text=f"Testo nascosto in {os.path.basename(file_path_salvataggio)}")
        except FileNotFoundError:
             messagebox.showerror("Errore", f"File originale non trovato:\n{img_path_originale}")
        except ValueError as ve: # Errore comune: testo troppo lungo per l'immagine
             messagebox.showerror("Errore Steganografia", f"Impossibile nascondere il testo:\n{ve}\n\nProva con un testo più corto o un'immagine più grande.")
        except Exception as e: # Altri errori dalla libreria stegano
            messagebox.showerror("Errore Steganografia", f"Errore durante il tentativo di nascondere il testo:\n{e}")
            traceback.print_exc()

    def estrai_testo(self):
        """Estrae il testo nascosto dall'immagine corrente e lo mostra nell'area dettagli."""
        current_index = self.indice_corrente.get()
        # Controlli preliminari
        if not self.immagini or not (0 <= current_index < len(self.immagini)):
            messagebox.showwarning("Nessuna Immagine", "Seleziona un'immagine prima di estrarre il testo.")
            return

        img_path = self.immagini[current_index].get("path")
        if not img_path:
            messagebox.showerror("Errore", "Percorso immagine mancante.")
            return

        try:
            # --- Prepara Area Dettagli per Output ---
            # Assicurati che sia modificabile per poter inserire il testo estratto
            self.area_dettagli.config(state=tk.NORMAL)
            self.area_dettagli.delete(1.0, tk.END) # Pulisci contenuto precedente

            # --- Esegui Steganografia (Estrai) ---
            # Usa la libreria stegano per rivelare il testo nascosto
            testo_estratto = lsb.reveal(img_path)

            # --- Mostra Risultato ---
            if testo_estratto: # Se è stato trovato del testo
                self.area_dettagli.insert(tk.END, testo_estratto)
                messagebox.showinfo("Successo", "Testo estratto con successo!")
                self.barra_stato.config(text=f"Testo estratto da {os.path.basename(img_path)}")
            else:
                # Se lsb.reveal() restituisce None o stringa vuota
                self.area_dettagli.insert(tk.END, "[Nessun testo nascosto trovato nell'immagine]")
                messagebox.showinfo("Nessun Testo", "Non è stato trovato alcun testo nascosto in questa immagine.")
                self.barra_stato.config(text=f"Nessun testo nascosto trovato in {os.path.basename(img_path)}")

            # Riporta l'area dettagli allo stato corretto (modificabile solo se stegano_mode è ancora attivo)
            if not self.stegano_mode.get():
                 self.area_dettagli.config(state=tk.DISABLED)

        except FileNotFoundError:
             messagebox.showerror("Errore", f"File immagine non trovato:\n{img_path}")
             # Pulisci area e ripristina stato corretto
             self.area_dettagli.delete(1.0, tk.END)
             if not self.stegano_mode.get(): self.area_dettagli.config(state=tk.DISABLED)
        except Exception as e: # Altri errori (es. formato non supportato da stegano, file corrotto)
            messagebox.showerror("Errore Estrazione", f"Errore durante l'estrazione del testo:\n{e}\n\nL'immagine potrebbe non contenere testo nascosto o essere corrotta.")
            traceback.print_exc()
            # Mostra messaggio di errore nell'area dettagli
            self.area_dettagli.delete(1.0, tk.END)
            self.area_dettagli.insert(tk.END, f"[Errore durante l'estrazione: {e}]")
            # Ripristina stato corretto
            if not self.stegano_mode.get(): self.area_dettagli.config(state=tk.DISABLED)

    # --- Metodo Info e Uscita ---

    def mostra_info(self):
        """Mostra una finestra di dialogo con informazioni in stile più discorsivo."""
        titolo = f"Informazioni - {self.APP_TITLE}"

        messaggio = f"{self.APP_TITLE}\n\n"
        messaggio += "Benvenuto! Ecco cosa puoi fare con questa galleria:\n\n"

        messaggio += "APRIRE IMMAGINI:\n"
        messaggio += "Usa 'Apri Immagine' o 'Apri Cartella' dal menu File o dalla barra degli strumenti per caricare le tue foto.\n\n"

        messaggio += "VISUALIZZARE:\n"
        messaggio += "Scegli tra 'Griglia' per vedere le miniature o 'Presentazione' per vedere un'immagine ingrandita (menu Visualizza). Scorri tra le immagini usando i tasti freccia sinistra e destra.\n\n"

        messaggio += "ORGANIZZARE:\n"
        messaggio += "Hai aperto una cartella? Usa il campo 'Cerca' nella toolbar per trovare immagini per nome. Puoi anche filtrare i tipi di file (JPEG, PNG, ecc.) usando gli interruttori colorati in basso.\n\n"

        messaggio += "SALVARE:\n"
        messaggio += "Seleziona un'immagine e vai su 'File > Salva Immagine Come...' per salvarla, anche in un formato diverso se necessario.\n\n"

        messaggio += "NASCONDERE TESTO (Steganografia):\n"
        messaggio += "Vuoi nascondere un messaggio segreto? Attiva la 'Modalità Steganografia' (menu o pannello inferiore), seleziona un'immagine (meglio PNG!), scrivi il testo nell'area apposita, clicca 'Nascondi' e salva il nuovo file PNG generato.\n\n"

        messaggio += "ESTRARRE TESTO NASCOSTO:\n"
        messaggio += "Apri l'immagine che contiene il messaggio, attiva la 'Modalità Steganografia' e clicca 'Estrai'. Il testo segreto apparirà nell'area inferiore.\n\n"

        formati_supportati = ', '.join(sorted(self.SUPPORTED_EXT_MAP.keys()))
        messaggio += f"Formati Supportati: {formati_supportati}\n"
        # Mostra la finestra di dialogo. Si chiude cliccando su "OK".
        messagebox.showinfo(titolo, messaggio)

    def quit(self):
        """Chiude l'applicazione."""
        print("Chiusura applicazione.")
        self.destroy() # Distrugge la finestra Tkinter e termina il mainloop


class FinestraLogin(ttk.Toplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.title("Autenticazione DevOps")
        self.geometry("350x250")
        self.resizable(False, False)
        
        self.protocol("WM_DELETE_WINDOW", self.chiusura_forzata)
        
        # Chiamiamo la funzione che "arreda" la stanza
        self._crea_widget_login()

    def chiusura_forzata(self):
        """Utente preme x termina programma"""
        self.master.destroy()

    def _crea_widget_login(self):
        """Crea fisicamente le etichette, le caselle di testo e il bottone."""
        # Un frame con un po' di margine (padding) per non avere tutto appiccicato ai bordi
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Titolo
        ttk.Label(frame, text="Inserisci le credenziali", font=("Arial", 12, "bold")).pack(pady=(0, 15))

        # --- Campo Username ---
        ttk.Label(frame, text="Username:").pack(anchor=tk.W)
        # ttk.Entry è la casella in cui l'utente può digitare
        self.entry_username = ttk.Entry(frame)
        self.entry_username.pack(fill=tk.X, pady=(0, 10))

        # --- Campo Password ---
        ttk.Label(frame, text="Password:").pack(anchor=tk.W)
        # show="*" è il trucco di sicurezza per coprire i caratteri digitati
        self.entry_password = ttk.Entry(frame, show="*")
        self.entry_password.pack(fill=tk.X, pady=(0, 20))

        # --- Bottone di Invio ---
        # Il parametro command=self._tenta_connessione dice al bottone quale funzione eseguire al click
        self.btn_accedi = ttk.Button(frame, text="Accedi", command=self._tenta_connessione, bootstyle=PRIMARY)
        self.btn_accedi.pack(fill=tk.X)

    def _tenta_connessione(self):
        """La funzione che scatta quando l'utente preme 'Accedi'."""
        # 1. Aspiriamo il testo che l'utente ha digitato nelle caselle
        user = self.entry_username.get()
        pwd = self.entry_password.get()

        # Se l'utente ha lasciato i campi vuoti, lo blocchiamo subito (risparmiamo una chiamata di rete inutile)
        if not user or not pwd:
            messagebox.showwarning("Attenzione", "Devi inserire sia username che password.")
            return

        # 2. Prepariamo la busta da spedire al nostro container Docker
        url_server = "http://localhost:5000/login"
        dati_da_inviare = {"username": user, "password": pwd}

        # Cambiamo il testo del bottone per far capire all'utente che stiamo caricando
        self.btn_accedi.config(text="Connessione in corso...", state=tk.DISABLED)
        self.update() # Forza Tkinter ad aggiornare la grafica immediatamente

        # 3. La telefonata vera e propria (dentro un try/except per sicurezza)
        try:
            # Ricordi? Il professore ha usato methods=['GET'], quindi usiamo requests.get
            # Il parametro 'timeout=3' è vitale per un DevOps: se il server non risponde in 3 secondi, annulla tutto.
            risposta = req.post(url_server, json=dati_da_inviare, timeout=3)

            # 4. Leggiamo la risposta
            if risposta.status_code == 200:
                # Login corretto!
                dati_json = risposta.json()
                self.master.token_acquisito = dati_json.get("token")
                
                # messagebox.showinfo("Successo", "Autenticazione riuscita!")

                self.master.deiconify()
                
                # Chiudiamo la finestra di login. Questo sblocca il mainloop() nel blocco di avvio!
                self.destroy() 
            else:
                # Se il server ha risposto con Errore di autenticazione
                messagebox.showerror("Accesso Negato", "Username o password errati.")
                
        except req.exceptions.ConnectionError:
             messagebox.showerror("Errore di Rete", "Impossibile contattare il server.\nHai acceso il container Docker?")
        except req.exceptions.Timeout:
             messagebox.showerror("Errore di Rete", "Il server ci sta mettendo troppo tempo a rispondere.")
        finally:
            # Qualsiasi cosa succeda (successo o errore), se la finestra esiste ancora, riattiviamo il bottoneccendere il servizio)
            if self.winfo_exists():
                self.btn_accedi.config(text="Accedi", state=tk.NORMAL)



# --- Blocco di Esecuzione Principale ---
if __name__ == "__main__":
    print(f"Avvio {GalleriaImmagini.APP_TITLE}...")
    try:
        # 1. Creiamo l'app principale (che accende il motore Tkinter)
        app = GalleriaImmagini()
        
        # 2. LA NASCONDIAMO SUBITO! L'utente non deve vederla senza essersi loggato.
        app.withdraw()
        
        # 3. Creiamo la finestrella di login come "figlia" dell'app
        finestra_login = FinestraLogin(app)
        
        # 4. Facciamo partire il ciclo continuo. 
        # Si fermerà solo quando chiuderemo definitivamente 'app'
        app.mainloop() 

    except Exception as e:
        error_msg = f"Errore critico non gestito:\n\n{traceback.format_exc()}"
        print(error_msg)
        try:
            root = tk.Tk(); root.withdraw()
            messagebox.showerror("Errore Critico", error_msg); root.destroy()
        except Exception: pass
    finally:
         print("Applicazione terminata.")