import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import os
import sys
from PIL import Image, ImageTk

class PannelloGalleria(ttk.Frame):
    ICON_SIZE = (18, 18)
    THUMBNAIL_SIZE = (120, 120) 
    THUMBNAIL_PADDING = 10 

    SUPPORTED_EXT_MAP = {
        "JPEG": ('.jpg', '.jpeg'),
        "PNG": ('.png',),
        "GIF": ('.gif',),
        "BMP": ('.bmp',),
    }
    ALL_SUPPORTED_EXT_FLAT = [ext for group in SUPPORTED_EXT_MAP.values() for ext in group]

    SAVE_FILEDIALOG_TYPES = [
        ("JPEG", "*.jpg"),
        ("PNG", "*.png"),
        ("GIF", "*.gif"),
        ("BMP", "*.bmp"),
        ("Tutti i file", "*.*")
    ]

    def __init__(self, master_app):
        super().__init__(master_app, padding=0) 
        self.app_principale = master_app 
        
        self.base_path = self._get_base_path()
        self.icon_path = os.path.join(self.base_path, "icons")
        self.icons = {}

        self.filtri_ext = {
            "JPEG": tk.BooleanVar(value=True),
            "PNG": tk.BooleanVar(value=True),
            "GIF": tk.BooleanVar(value=True),
            "BMP": tk.BooleanVar(value=True)
        }
        
        self.modalita_visualizzazione = tk.StringVar(value="Griglia")
        self.directory_corrente = ""
        self.immagini = []
        self._search_debounce_job = None
        
        self._crea_interfaccia()

    def _crea_interfaccia(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.toolbar = self._create_toolbar(main_frame)
        self.toolbar.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.notebook = ttk.Notebook(main_frame, bootstyle="info")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tab_locale = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_locale, text=" Immagini Locali ")

        self.tab_server = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_server, text=" Immagini dal Server ")

        self.frame_griglia_locale = ttk.Frame(self.tab_locale)
        self.frame_griglia_locale.pack(fill=tk.BOTH, expand=True)

        self.frame_presentazione = ttk.Frame(self.tab_locale)
        
        stile_globale = ttk.Style()
        colore_sfondo = stile_globale.lookup('TFrame', 'background')
        
        self.canvas_immagine = tk.Canvas(self.frame_presentazione, bg=colore_sfondo, highlightthickness=0)
        self.canvas_immagine.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.frame_dettagli = ttk.Frame(self.frame_presentazione)
        self.frame_dettagli.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        ttk.Label(self.frame_dettagli, text="Dettagli Immagine", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        self.area_testo_dettagli = tk.Text(self.frame_dettagli, height=4, state=tk.DISABLED, relief=tk.FLAT, borderwidth=0, padx=10, pady=10) 
        self.area_testo_dettagli.pack(fill=tk.BOTH, expand=True)

        barra_azioni = ttk.Frame(self.frame_presentazione)
        barra_azioni.pack(fill=tk.X, pady=(0, 20), padx=20)
        
        # --- COLORI PRESENTAZIONE ---
        # "Torna alla Griglia" è un'azione secondaria di navigazione: usiamo un outline discreto
        ttk.Button(barra_azioni, text="← Torna alla Griglia", command=self.torna_alla_griglia, bootstyle="secondary").pack(side=tk.LEFT)
        # "YOLO" è l'azione principale e potenzialmente distruttiva/pesante: usiamo un colore solido di avviso
        self.btn_invia_server = ttk.Button(barra_azioni, text="Esegui Rilevamento YOLO", bootstyle="warning")
        self.btn_invia_server.pack(side=tk.RIGHT)

        ttk.Label(self.tab_server, text="In attesa di collegamento all'API di Flask...", justify=tk.CENTER, font=("Segoe UI", 14)).pack(expand=True)

        self.frame_filtri = ttk.Frame(self)
        self.frame_filtri.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        ttk.Label(self.frame_filtri, text="Filtri formato:", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))

        for formato, var in self.filtri_ext.items():
            cb = ttk.Checkbutton(
                self.frame_filtri,
                text=formato,
                variable=var, 
                command=self.cerca_immagini, 
                bootstyle="round-toggle" 
            )
            cb.pack(side=tk.LEFT, padx=5)

        self.barra_stato = ttk.Label(self, text=" Pronto", bootstyle="inverse-secondary", padding=5)
        self.barra_stato.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_toolbar(self, parent):
        toolbar = ttk.Frame(parent)
        btn_compound = tk.LEFT

        icon_open_menu = self._load_icon("folder-plus.png")
        icon_save = self._load_icon("save.png")
        icon_grid = self._load_icon("grid.png")
        icon_prev = self._load_icon("arrow-left.png")
        icon_next = self._load_icon("arrow-right.png")
        icon_search = self._load_icon("search.png")
        icon_help = self._load_icon("help.png")

        # --- COLORI MARCATI ED ELEGANTI ---
        
        self.btn_apri = ttk.Menubutton(toolbar, text="Apri", image=icon_open_menu, compound=btn_compound, bootstyle="primary")
        self.btn_apri.pack(side=tk.LEFT, padx=(0, 2))

        menu_apri = tk.Menu(self.btn_apri, tearoff=0)
        menu_apri.add_command(label="Apri Singola Immagine...", command=self.apri_immagine)
        menu_apri.add_command(label="Apri Cartella...", command=self.apri_cartella)
        self.btn_apri["menu"] = menu_apri
        
        self.btn_salva = ttk.Button(toolbar, text="Salva Come...", image=icon_save, compound=btn_compound, bootstyle="success", command=self.salva_immagine)
        self.btn_salva.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        self.btn_mostra_griglia = ttk.Button(toolbar, text="Griglia", image=icon_grid, compound=btn_compound, bootstyle="secondary", command=self.torna_alla_griglia)
        self.btn_mostra_griglia.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        self.btn_prev = ttk.Button(toolbar, text="Prec", image=icon_prev, compound=btn_compound, bootstyle="secondary", command=self.mostra_precedente)
        self.btn_prev.pack(side=tk.LEFT, padx=2)
        
        self.btn_next = ttk.Button(toolbar, text="Succ", image=icon_next, compound=btn_compound, bootstyle="secondary", command=self.mostra_successivo)
        self.btn_next.pack(side=tk.LEFT, padx=2)

        self.btn_help = ttk.Button(toolbar, text="Aiuto", image=icon_help, compound=btn_compound, command=self.mostra_info, bootstyle="info")
        self.btn_help.pack(side=tk.RIGHT, padx=(5, 0))

        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT, padx=5)
        
        self.btn_cerca = ttk.Button(search_frame, text="Cerca", image=icon_search, compound=btn_compound, bootstyle="primary", command=self.cerca_immagini)
        self.btn_cerca.pack(side=tk.RIGHT)
        
        self.txt_ricerca = ttk.Entry(search_frame, width=25)
        self.txt_ricerca.pack(side=tk.RIGHT, padx=5)

        self.txt_ricerca.bind("<Return>", lambda e: self.cerca_immagini())
        self.txt_ricerca.bind("<KeyRelease>", self._on_search_change)

        return toolbar
    
    def mostra_precedente(self):
        if not self.immagini or not hasattr(self, 'indice_corrente'): 
            return 
        num_immagini = len(self.immagini)
        nuovo_indice = (self.indice_corrente - 1 + num_immagini) % num_immagini
        self.apri_presentazione(nuovo_indice)

    def mostra_successivo(self):
        if not self.immagini or not hasattr(self, 'indice_corrente'): 
            return 
        num_immagini = len(self.immagini)
        nuovo_indice = (self.indice_corrente + 1) % num_immagini
        self.apri_presentazione(nuovo_indice)

    def salva_immagine(self):
        if not hasattr(self, 'indice_corrente') or self.indice_corrente is None:
            messagebox.showwarning("Attenzione", "Devi prima cliccare su un'immagine per ingrandirla prima di poterla salvare.")
            return

        if not self.immagini or not (0 <= self.indice_corrente < len(self.immagini)):
            return

        img_path_originale = self.immagini[self.indice_corrente].get("path")
        if not img_path_originale:
            messagebox.showerror("Errore", "Percorso del file originale mancante.")
            return

        nome_file_originale = os.path.basename(img_path_originale)
        _, ext_originale = os.path.splitext(nome_file_originale)
        
        file_path_salvataggio = filedialog.asksaveasfilename(
            title="Salva immagine come...",
            initialdir=self.directory_corrente or os.path.expanduser("~"),
            initialfile=nome_file_originale,
            defaultextension=ext_originale,
            filetypes=self.SAVE_FILEDIALOG_TYPES
        )
        
        if not file_path_salvataggio:
            return 

        try:
            with Image.open(img_path_originale) as img:
                save_format_ext = os.path.splitext(file_path_salvataggio)[1].lower()
                img_to_save = img.copy() 

                if save_format_ext in ['.jpg', '.jpeg']:
                    if img_to_save.mode in ('RGBA', 'LA') or (img_to_save.mode == 'P' and 'transparency' in img_to_save.info):
                        sfondo_bianco = Image.new("RGB", img_to_save.size, (255, 255, 255))
                        if img_to_save.mode == 'P':
                            img_to_save = img_to_save.convert('RGBA')
                        sfondo_bianco.paste(img_to_save, mask=img_to_save.split()[3]) 
                        img_to_save = sfondo_bianco
                    elif img_to_save.mode != 'RGB':
                        img_to_save = img_to_save.convert('RGB')
                        
                elif save_format_ext == '.bmp':
                    if img_to_save.mode == 'RGBA' or 'A' in img_to_save.mode:
                        img_to_save = img_to_save.convert('RGB')

                img_to_save.save(file_path_salvataggio)

            self.barra_stato.config(text=f" Salvata in: {os.path.basename(file_path_salvataggio)}")
            messagebox.showinfo("Salvataggio Completato", f"Immagine salvata con successo come:\n{os.path.basename(file_path_salvataggio)}")
        except Exception as e:
            messagebox.showerror("Errore di Salvataggio", f"Si è verificato un problema:\n{e}")
            import traceback
            traceback.print_exc()

    def _on_search_change(self, event=None):
        if self._search_debounce_job:
            self.after_cancel(self._search_debounce_job)
        self._search_debounce_job = self.after(300, self._perform_search)

    def _perform_search(self):
        self._search_debounce_job = None
        self.cerca_immagini()

    def cerca_immagini(self):
        if not self.directory_corrente:
            return 
        termine = self.txt_ricerca.get()
        self.carica_immagini_da_cartella(self.directory_corrente, termine)

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
                self.barra_stato.config(text=f" Immagine singola caricata: {nome_file}")
                self.mostra_griglia()
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile aprire l'immagine:\n{e}")
    
    def carica_immagini_da_cartella(self, directory, termine_ricerca=""):
        self.immagini = []
        immagini_trovate = []
        termine_ricerca = termine_ricerca.strip().lower()
        
        estensioni_permesse = []
        for formato, var in self.filtri_ext.items():
            if var.get(): 
                estensioni_permesse.extend(self.SUPPORTED_EXT_MAP[formato])
        
        try:
            files_in_dir = sorted(os.listdir(directory), key=str.lower)
            for filename in files_in_dir:
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    name_lower = filename.lower()
                    has_valid_ext = any(name_lower.endswith(ext) for ext in estensioni_permesse)
                    matches_search = not termine_ricerca or termine_ricerca in name_lower
                    if has_valid_ext and matches_search:
                        immagini_trovate.append({"path": file_path})

            self.immagini = immagini_trovate
            
            if self.immagini:
                msg = f" Caricate {len(self.immagini)} immagini"
                if termine_ricerca: msg += f" per '{termine_ricerca}'"
                self.barra_stato.config(text=msg)
                self.mostra_griglia()
            else:
                for widget in self.frame_griglia_locale.winfo_children():
                    widget.destroy()
                self.barra_stato.config(text=" Nessuna immagine trovata corrispondente ai filtri attuali.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile leggere la cartella:\n{e}")

    def mostra_griglia(self):
        for widget in self.frame_griglia_locale.winfo_children():
            widget.destroy()

        stile_globale = ttk.Style()
        colore_sfondo = stile_globale.lookup('TFrame', 'background')

        self.grid_canvas = tk.Canvas(self.frame_griglia_locale, highlightthickness=0, borderwidth=0, bg=colore_sfondo)
        self.scrollbar = ttk.Scrollbar(self.frame_griglia_locale, orient=tk.VERTICAL, command=self.grid_canvas.yview, bootstyle="round")
        
        scrollable_frame = ttk.Frame(self.grid_canvas)
        canvas_window = self.grid_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.grid_canvas.configure(yscrollcommand=self.scrollbar.set)

        def _aggiorna_scrollregion(event=None):
            self.grid_canvas.update_idletasks() 
            bbox = self.grid_canvas.bbox("all")
            if bbox:
                self.grid_canvas.configure(scrollregion=bbox)
                if bbox[3] <= self.grid_canvas.winfo_height():
                    self.scrollbar.pack_forget()
                else:
                    self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        scrollable_frame.bind("<Configure>", _aggiorna_scrollregion)

        def _on_canvas_configure(event):
            canvas_width = event.width
            self.grid_canvas.itemconfig(canvas_window, width=canvas_width)
            self._organizza_griglia_items(scrollable_frame, canvas_width)
            _aggiorna_scrollregion() 

        self.grid_canvas.bind("<Configure>", _on_canvas_configure)
        self.grid_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_mousewheel(event):
            if self.scrollbar.winfo_ismapped():
                if sys.platform == "darwin": delta = -1 * event.delta
                elif event.num == 4: delta = -1
                elif event.num == 5: delta = 1
                else: delta = int(-1 * (event.delta / 120))
                self.grid_canvas.yview_scroll(delta, "units")

        def _bind_mousewheel(event):
            self.grid_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            self.grid_canvas.bind_all("<Button-4>", _on_mousewheel) 
            self.grid_canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            self.grid_canvas.unbind_all("<MouseWheel>")
            self.grid_canvas.unbind_all("<Button-4>")
            self.grid_canvas.unbind_all("<Button-5>")

        self.grid_canvas.bind("<Enter>", _bind_mousewheel)
        self.grid_canvas.bind("<Leave>", _unbind_mousewheel)

    def _organizza_griglia_items(self, container_frame, available_width):
        for widget in container_frame.winfo_children():
            widget.destroy()

        colonne_precedenti, _ = container_frame.grid_size()
        for c in range(colonne_precedenti):
            container_frame.columnconfigure(c, weight=0, uniform="")

        if not self.immagini or available_width <= 1: return

        grid_item_width = self.THUMBNAIL_SIZE[0] + self.THUMBNAIL_PADDING * 2
        cols = max(1, int(available_width // grid_item_width))

        row, col = 0, 0
        for i, img_info in enumerate(self.immagini):
            path = img_info.get("path")
            if not path: continue

            try:
                item_frame = ttk.Frame(container_frame, borderwidth=0, relief=tk.FLAT, padding=self.THUMBNAIL_PADDING, bootstyle="dark")
                
                img = Image.open(path)
                img.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                img_label = ttk.Label(item_frame, image=photo, bootstyle="inverse-dark")
                img_label.image = photo 
                img_label.pack(pady=(0, 5))

                nome_file = os.path.basename(path)
                display_name = (nome_file[:15] + '...') if len(nome_file) > 18 else nome_file
                
                name_label = ttk.Label(item_frame, text=display_name, justify=tk.CENTER, bootstyle="inverse-dark")
                name_label.pack(fill=tk.X)

                click_handler = lambda e, idx=i: self.apri_presentazione(idx)
                
                item_frame.bind("<Enter>", lambda e, f=item_frame: f.config(cursor="hand2"))
                img_label.bind("<Enter>", lambda e, l=img_label: l.config(cursor="hand2"))
                
                item_frame.bind("<Button-1>", click_handler)
                img_label.bind("<Button-1>", click_handler)
                name_label.bind("<Button-1>", click_handler)

                item_frame.grid(row=row, column=col, padx=self.THUMBNAIL_PADDING, pady=self.THUMBNAIL_PADDING, sticky="nsew")

                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            except Exception as e:
                print(f"Errore caricamento miniatura {path}: {e}")

        for c in range(cols):
            container_frame.columnconfigure(c, weight=1, uniform="grid_col")

    def apri_presentazione(self, indice):
        self.indice_corrente = indice
        img_selezionata = self.immagini[indice]["path"]

        self.frame_griglia_locale.pack_forget()
        self.frame_presentazione.pack(fill=tk.BOTH, expand=True)

        self.canvas_immagine.delete("all")
        img = Image.open(img_selezionata)
        img.thumbnail((800, 400), Image.Resampling.LANCZOS)
        self.foto_ingrandita = ImageTk.PhotoImage(img) 
        
        self.canvas_immagine.update_idletasks() 
        self.canvas_immagine.create_image(
            self.canvas_immagine.winfo_width()//2, 
            self.canvas_immagine.winfo_height()//2, 
            anchor=tk.CENTER, image=self.foto_ingrandita
        )

        nome_file = os.path.basename(img_selezionata)
        dimensione = os.path.getsize(img_selezionata) / 1024
        testo_dettagli = f"Nome File: {nome_file}\nDimensione: {dimensione:.1f} KB\nPercorso: {img_selezionata}"
        
        self.area_testo_dettagli.config(state=tk.NORMAL)
        self.area_testo_dettagli.delete(1.0, tk.END)
        self.area_testo_dettagli.insert(tk.END, testo_dettagli)
        self.area_testo_dettagli.config(state=tk.DISABLED)

    def torna_alla_griglia(self):
        self.frame_presentazione.pack_forget()
        self.frame_griglia_locale.pack(fill=tk.BOTH, expand=True)

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
        
    def mostra_info(self):
        titolo = f"Informazioni - Galleria Immagini"
        messaggio = f"Galleria Immagini\n\n"
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
        messagebox.showinfo(titolo, messaggio)