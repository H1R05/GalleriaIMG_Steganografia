import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.constants import *
import os
import sys
from PIL import Image, ImageTk

class PannelloGalleria(ttk.Frame):
    # Riprendiamo le tue costanti originali
    ICON_SIZE = (20, 20)

    def __init__(self, master_app):
        super().__init__(master_app, padding=10)
        self.app_principale = master_app 
        
        # 1. Configurazione percorsi e icone (Essenziale per la toolbar)
        self.base_path = self._get_base_path()
        self.icon_path = os.path.join(self.base_path, "icons")
        self.icons = {}
        
        # 2. Inizializziamo le variabili di stato minime necessarie alla grafica
        self.modalita_visualizzazione = tk.StringVar(value="Griglia")
        
        # 3. Disegniamo l'interfaccia
        self._crea_interfaccia()

    # --- METODI DI SUPPORTO (Copiati dal tuo codice originale) ---
    def _get_base_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def _load_icon(self, filename):
        try:
            full_path = os.path.join(self.icon_path, filename)
            if not os.path.exists(full_path):
                return None
            img = Image.open(full_path)
            img_resized = img.resize(self.ICON_SIZE, Image.Resampling.LANCZOS)
            photo_image = ImageTk.PhotoImage(img_resized)
            self.icons[filename] = photo_image
            return photo_image
        except Exception as e:
            print(f"Errore icona {filename}: {e}")
            return None

    # --- COSTRUZIONE DELLA GRAFICA ---
    def _crea_interfaccia(self):
        """Costruisce lo scheletro della galleria"""
        # Creiamo un frame principale che conterrà tutto
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. La tua amata Toolbar!
        self.toolbar = self._create_toolbar(main_frame)
        self.toolbar.pack(fill=tk.X, pady=(0, 10))

        # 2. L'area centrale per la griglia/presentazione
        self.display_frame = self._create_display_area(main_frame)
        self.display_frame.pack(fill=tk.BOTH, expand=True)

        # 3. La barra di stato in fondo
        self.barra_stato = ttk.Label(self, text="Token JWT caricato in memoria", bootstyle=PRIMARY)
        self.barra_stato.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

    def _create_toolbar(self, parent):
        """La tua toolbar originale, scollegata momentaneamente dalle funzioni complesse"""
        toolbar = ttk.Frame(parent, padding=(5, 5))
        btn_compound = tk.LEFT

        # Carichiamo le icone (se non le trova nel tuo PC, non mostrerà nulla, non crasherà)
        icon_open_menu = self._load_icon("folder-plus.png")
        icon_save = self._load_icon("save.png")
        icon_grid = self._load_icon("grid.png")
        icon_prev = self._load_icon("arrow-left.png")
        icon_next = self._load_icon("arrow-right.png")

        # Bottoni Base (Ho tolto i "command=" per ora, li ricollegheremo dopo)
        self.btn_apri = ttk.Button(toolbar, text="Apri", image=icon_open_menu, compound=btn_compound, bootstyle=INFO)
        self.btn_apri.pack(side=tk.LEFT, padx=2)
        
        self.btn_salva = ttk.Button(toolbar, text="Salva Come...", image=icon_save, compound=btn_compound, bootstyle=SUCCESS)
        self.btn_salva.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        self.btn_mostra_griglia = ttk.Button(toolbar, text="Griglia", image=icon_grid, compound=btn_compound, bootstyle=INFO)
        self.btn_mostra_griglia.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        self.btn_prev = ttk.Button(toolbar, text="Prec", image=icon_prev, compound=btn_compound, bootstyle=SECONDARY)
        self.btn_prev.pack(side=tk.LEFT, padx=2)
        
        self.btn_next = ttk.Button(toolbar, text="Succ", image=icon_next, compound=btn_compound, bootstyle=SECONDARY)
        self.btn_next.pack(side=tk.LEFT, padx=2)

        return toolbar

    def _create_display_area(self, parent):
        """Il frame centrale vuoto che un domani ospiterà le tue immagini"""
        display_frame = ttk.Frame(parent, bootstyle="secondary") 
        
        # Una scritta provvisoria per farti vedere dove andrà la griglia
        ttk.Label(
            display_frame, 
            text="[ Area della Griglia Immagini ]", 
            font=("Arial", 16), 
            bootstyle="inverse-secondary"
        ).pack(expand=True)
        
        return display_frame