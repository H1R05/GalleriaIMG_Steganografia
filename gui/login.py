import ttkbootstrap as ttk
import requests as req
import tkinter as tk
from tkinter import messagebox
from ttkbootstrap.constants import *


class PannelloLogin(ttk.Frame):
    def __init__(self, master_app):
        super().__init__(master_app, padding=20)
        
        self.app_principale = master_app

        # Chiamiamo la funzione che "arreda" la stanza
        self._crea_widget_login()

    def chiusura_forzata(self):
        """Utente preme x termina programma"""
        self.master.destroy()

    def _crea_widget_login(self):
        """Crea fisicamente le etichette, le caselle di testo e il bottone."""
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Inserisci le credenziali", font=("Arial", 12, "bold")).pack(pady=(0, 15))

        ttk.Label(frame, text="Username:").pack(anchor=tk.W)
        self.entry_username = ttk.Entry(frame)
        self.entry_username.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Password:").pack(anchor=tk.W)
        self.entry_password = ttk.Entry(frame, show="*")
        self.entry_password.pack(fill=tk.X, pady=(0, 20))

        self.btn_accedi = ttk.Button(frame, text="Accedi", command=self._tenta_connessione, bootstyle=PRIMARY)
        self.btn_accedi.pack(fill=tk.X)

    def _tenta_connessione(self):
        """La funzione che scatta quando l'utente preme 'Accedi'."""
        user = self.entry_username.get()
        pwd = self.entry_password.get()

        if not user or not pwd:
            messagebox.showwarning("Attenzione", "Devi inserire sia username che password.")
            return

        url_server = "http://localhost:5000/login"
        dati_da_inviare = {"username": user, "password": pwd}

        self.btn_accedi.config(text="Connessione in corso...", state=tk.DISABLED)
        self.update()

        try:
            # Il parametro 'timeout=3' è : se il server non risponde in 3 secondi, annulla tutto.
            risposta = req.post(url_server, json=dati_da_inviare, timeout=3)

            if risposta.status_code == 200:
                dati_json = risposta.json()
                self.master.token_acquisito = dati_json.get("token")
                self.app_principale.login_completato()
            else:
                messagebox.showerror("Accesso Negato", "Username o password errati.")
                
        except req.exceptions.ConnectionError:
             messagebox.showerror("Errore di Rete", "Impossibile contattare il server.\nHai acceso il container Docker?")
        finally:
            # Qualsiasi cosa succeda (successo o errore), se la finestra esiste ancora, riattivo il bottone)
            if self.winfo_exists():
                self.btn_accedi.config(text="Accedi", state=tk.NORMAL)