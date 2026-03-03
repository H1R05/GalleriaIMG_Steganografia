import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import os
import sys
from PIL import Image, ImageTk

class PannelloGalleria(ttk.Frame):
    # --- COSTANTI ---
    ICON_SIZE = (20, 20)
    THUMBNAIL_SIZE = (150, 150) 
    THUMBNAIL_PADDING = 8 

    SUPPORTED_EXT_MAP = {
        "JPEG": ('.jpg', '.jpeg'),
        "PNG": ('.png',),
        "GIF": ('.gif',),
        "BMP": ('.bmp',),
    }
    ALL_SUPPORTED_EXT_FLAT = [ext for group in SUPPORTED_EXT_MAP.values() for ext in group]

    # --- 1. INIZIALIZZAZIONE (Il Costruttore) ---
    def __init__(self, master_app):
        super().__init__(master_app, padding=10)
        self.app_principale = master_app 
        
        # Configurazione percorsi e icone
        self.base_path = self._get_base_path()
        self.icon_path = os.path.join(self.base_path, "icons")
        self.icons = {}
        
        # Variabili di stato
        self.modalita_visualizzazione = tk.StringVar(value="Griglia")
        self.directory_corrente = ""
        self.immagini = []
        
        # Disegniamo l'interfaccia non appena il pannello viene creato
        self._crea_interfaccia()

    # --- 2. COSTRUZIONE DELLA GRAFICA ---
    def _crea_interfaccia(self):
        """Costruisce lo scheletro della galleria con sistema a Schede (Tabs)"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # La Toolbar in alto
        self.toolbar = self._create_toolbar(main_frame)
        self.toolbar.pack(fill=tk.X, pady=(0, 10))

        # IL SISTEMA A SCHEDE (NOTEBOOK)
        self.notebook = ttk.Notebook(main_frame, bootstyle="info")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scheda 1: Le immagini del PC
        self.tab_locale = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_locale, text=" 📁 Immagini Locali ")

        # Scheda 2: Le immagini dal database
        self.tab_server = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_server, text=" ☁️ Immagini dal Server ")

        # --- AREE DELLA SCHEDA LOCALE ---
        
        # A) Il contenitore della Griglia (visibile all'inizio)
        self.frame_griglia_locale = ttk.Frame(self.tab_locale)
        self.frame_griglia_locale.pack(fill=tk.BOTH, expand=True)

        # B) Il contenitore della Presentazione (nascosto all'inizio)
        self.frame_presentazione = ttk.Frame(self.tab_locale)
        
        # Area Immagine Ingrandita (con correzione del tkapp)
        stile_globale = ttk.Style()
        self.canvas_immagine = tk.Canvas(self.frame_presentazione, bg=stile_globale.lookup('TFrame', 'background'), highlightthickness=0)
        self.canvas_immagine.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Area Dettagli
        self.frame_dettagli = ttk.LabelFrame(self.frame_presentazione, text="Dettagli Immagine")
        self.frame_dettagli.pack(fill=tk.X, padx=10, pady=5)
        self.area_testo_dettagli = tk.Text(self.frame_dettagli, height=4, state=tk.DISABLED, bg="#2b3e50", fg="white") 
        self.area_testo_dettagli.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Barra dei Bottoni Azione (Sotto i dettagli)
        barra_azioni = ttk.Frame(self.frame_presentazione)
        barra_azioni.pack(fill=tk.X, pady=5, padx=10)
        ttk.Button(barra_azioni, text="← Torna alla Griglia", command=self.torna_alla_griglia, bootstyle=SECONDARY).pack(side=tk.LEFT)
        self.btn_invia_server = ttk.Button(barra_azioni, text="Esegui Rilevamento YOLO", bootstyle=WARNING)
        self.btn_invia_server.pack(side=tk.RIGHT)

        # --- AREE DELLA SCHEDA SERVER ---
        ttk.Label(self.tab_server, text="In attesa di collegamento all'API di Flask...", justify=tk.CENTER, font=("Arial", 14)).pack(expand=True)

        # La barra di stato in fondo alla finestra
        self.barra_stato = ttk.Label(self, text="Pronto", bootstyle=PRIMARY)
        self.barra_stato.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

    def _create_toolbar(self, parent):
        """Crea i bottoni della barra degli strumenti in alto"""
        toolbar = ttk.Frame(parent, padding=(5, 5))
        btn_compound = tk.LEFT

        icon_open_menu = self._load_icon("folder-plus.png")
        icon_save = self._load_icon("save.png")
        icon_grid = self._load_icon("grid.png")
        icon_prev = self._load_icon("arrow-left.png")
        icon_next = self._load_icon("arrow-right.png")

        # Menu a tendina "Apri"
        self.btn_apri = ttk.Menubutton(toolbar, text="Apri", image=icon_open_menu, compound=btn_compound, bootstyle=INFO)
        self.btn_apri.pack(side=tk.LEFT, padx=2)

        menu_apri = tk.Menu(self.btn_apri, tearoff=0)
        menu_apri.add_command(label="Apri Singola Immagine...", command=self.apri_immagine)
        menu_apri.add_command(label="Apri Cartella...", command=self.apri_cartella)
        self.btn_apri["menu"] = menu_apri
        
        self.btn_salva = ttk.Button(toolbar, text="Salva Come...", image=icon_save, compound=btn_compound, bootstyle=SUCCESS)
        self.btn_salva.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        self.btn_mostra_griglia = ttk.Button(toolbar, text="Griglia", image=icon_grid, compound=btn_compound, bootstyle=INFO, command=self.torna_alla_griglia)
        self.btn_mostra_griglia.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        self.btn_prev = ttk.Button(toolbar, text="Prec", image=icon_prev, compound=btn_compound, bootstyle=SECONDARY)
        self.btn_prev.pack(side=tk.LEFT, padx=2)
        
        self.btn_next = ttk.Button(toolbar, text="Succ", image=icon_next, compound=btn_compound, bootstyle=SECONDARY)
        self.btn_next.pack(side=tk.LEFT, padx=2)

        return toolbar

    # --- 3. LOGICA DI CARICAMENTO FILE ---
    def apri_cartella(self):
        directory = filedialog.askdirectory(title="Seleziona una cartella", mustexist=True)
        if directory:
            self.directory_corrente = directory
            self.carica_immagini_da_cartella(directory)

    def apri_immagine(self):
        tipi_file = [
            ("Immagini Supportate", "*" + " *".join(self.ALL_SUPPORTED_EXT_FLAT)),
            ("Tutti i file", "*.*")
        ]
        file_path = filedialog.askopenfilename(title="Seleziona un'immagine", filetypes=tipi_file)
        
        if file_path: 
            try:
                self.directory_corrente = os.path.dirname(file_path)
                self.immagini = [{"path": file_path}]
                
                nome_file = os.path.basename(file_path)
                self.barra_stato.config(text=f"Immagine singola caricata: {nome_file}")
                
                self.mostra_griglia()
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile aprire l'immagine:\n{e}")
    
    def carica_immagini_da_cartella(self, directory):
        self.immagini = []
        immagini_trovate = []
        try:
            files_in_dir = sorted(os.listdir(directory), key=str.lower)
            for filename in files_in_dir:
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    name_lower = filename.lower()
                    if any(name_lower.endswith(ext) for ext in self.ALL_SUPPORTED_EXT_FLAT):
                        immagini_trovate.append({"path": file_path})

            self.immagini = immagini_trovate
            
            if self.immagini:
                self.barra_stato.config(text=f"Caricate {len(self.immagini)} immagini dalla cartella: {os.path.basename(directory)}")
                self.mostra_griglia()
            else:
                self.barra_stato.config(text="Nessuna immagine trovata in questa cartella.")
                messagebox.showinfo("Avviso", "La cartella selezionata non contiene immagini supportate.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile leggere la cartella:\n{e}")

    # --- 4. MOTORE DELLA GRIGLIA ---
    def mostra_griglia(self):
        for widget in self.frame_griglia_locale.winfo_children():
            widget.destroy()

        stile_globale = ttk.Style()
        canvas_bg = stile_globale.lookup('TFrame', 'background')
        grid_canvas = tk.Canvas(self.frame_griglia_locale, highlightthickness=0, bg=canvas_bg)
        scrollbar = ttk.Scrollbar(self.frame_griglia_locale, orient=tk.VERTICAL, command=grid_canvas.yview, bootstyle="round")
        
        scrollable_frame = ttk.Frame(grid_canvas)
        scrollable_frame.bind("<Configure>", lambda e: grid_canvas.configure(scrollregion=grid_canvas.bbox("all")))
        
        canvas_window = grid_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        grid_canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas_width = event.width
            grid_canvas.itemconfig(canvas_window, width=canvas_width)
            self._organizza_griglia_items(scrollable_frame, canvas_width)

        grid_canvas.bind("<Configure>", _on_canvas_configure)

        grid_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _organizza_griglia_items(self, container_frame, available_width):
        for widget in container_frame.winfo_children():
            widget.destroy()

        if not self.immagini or available_width <= 1: return

        grid_item_width = self.THUMBNAIL_SIZE[0] + self.THUMBNAIL_PADDING * 2
        cols = max(1, int(available_width // grid_item_width))

        row, col = 0, 0
        for i, img_info in enumerate(self.immagini):
            path = img_info.get("path")
            if not path: continue

            try:
                item_frame = ttk.Frame(container_frame, borderwidth=1, relief=tk.SOLID, padding=self.THUMBNAIL_PADDING // 2, bootstyle="secondary")
                
                img = Image.open(path)
                img.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                img_label = ttk.Label(item_frame, image=photo)
                img_label.image = photo 
                img_label.pack(pady=(0, 5))

                nome_file = os.path.basename(path)
                display_name = (nome_file[:15] + '...') if len(nome_file) > 18 else nome_file
                name_label = ttk.Label(item_frame, text=display_name, justify=tk.CENTER)
                name_label.pack(fill=tk.X)

                # Evento Click che manda alla presentazione
                click_handler = lambda e, idx=i: self.apri_presentazione(idx)
                item_frame.bind("<Button-1>", click_handler)
                img_label.bind("<Button-1>", click_handler)
                name_label.bind("<Button-1>", click_handler)

                item_frame.grid(row=row, column=col, padx=self.THUMBNAIL_PADDING // 2, pady=self.THUMBNAIL_PADDING // 2, sticky="nsew")

                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            except Exception as e:
                print(f"Errore caricamento miniatura {path}: {e}")

        for c in range(cols):
            container_frame.columnconfigure(c, weight=1, uniform="grid_col")

    # --- 5. TRANSIZIONI DI SCENA ---
    def apri_presentazione(self, indice):
        """Nasconde la griglia, mostra l'immagine ingrandita e compila i dettagli."""
        self.indice_corrente = indice
        img_selezionata = self.immagini[indice]["path"]

        # Spegniamo la griglia e accendiamo la presentazione
        self.frame_griglia_locale.pack_forget()
        self.frame_presentazione.pack(fill=tk.BOTH, expand=True)

        # Disegniamo l'immagine ingrandita
        self.canvas_immagine.delete("all")
        img = Image.open(img_selezionata)
        img.thumbnail((800, 400), Image.Resampling.LANCZOS)
        self.foto_ingrandita = ImageTk.PhotoImage(img) 
        
        self.canvas_immagine.update_idletasks() # Assicura che il canvas abbia calcolato la sua larghezza
        self.canvas_immagine.create_image(
            self.canvas_immagine.winfo_width()//2, 
            self.canvas_immagine.winfo_height()//2, 
            anchor=tk.CENTER, image=self.foto_ingrandita
        )

        # Compiliamo l'area dettagli
        nome_file = os.path.basename(img_selezionata)
        dimensione = os.path.getsize(img_selezionata) / 1024
        testo_dettagli = f"Nome File: {nome_file}\nDimensione: {dimensione:.1f} KB\nPercorso: {img_selezionata}"
        
        self.area_testo_dettagli.config(state=tk.NORMAL)
        self.area_testo_dettagli.delete(1.0, tk.END)
        self.area_testo_dettagli.insert(tk.END, testo_dettagli)
        self.area_testo_dettagli.config(state=tk.DISABLED)

    def torna_alla_griglia(self):
        """Nasconde la presentazione e fa riapparire la griglia."""
        self.frame_presentazione.pack_forget()
        self.frame_griglia_locale.pack(fill=tk.BOTH, expand=True)

    # --- 6. FUNZIONI DI SUPPORTO ---
    def _get_base_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def _load_icon(self, filename):
        try:
            full_path = os.path.join(self.icon_path, filename)
            if not os.path.exists(full_path): return None
            img = Image.open(full_path)
            img_resized = img.resize(self.ICON_SIZE, Image.Resampling.LANCZOS)
            photo_image = ImageTk.PhotoImage(img_resized)
            self.icons[filename] = photo_image
            return photo_image
        except Exception as e:
            return None