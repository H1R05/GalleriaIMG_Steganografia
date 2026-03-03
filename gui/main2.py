import tkinter as tk
import ttkbootstrap as ttk
#Importiamo il mattoncino che abbiamo creato nell'altro file!
from login import PannelloLogin
from vista_galleria import PannelloGalleria

class ApplicazionePrincipale(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Galleria Immagini")
        self.geometry("460x350")
        self.token_acquisito = None

        # Passo 'self' come argomento, dicendogli: "Io sono il tuo master (genitore)"
        self.panello_login = PannelloLogin(self)
        self.panello_login.pack(expand=True, fill="both")

    def login_completato(self):
        """Viene innescato quando riceve il token 200"""
        self.panello_login.pack_forget()

        print(f"Login effettuato!token: {self.token_acquisito}")

        self.pannello_galleria = PannelloGalleria(self)
        self.pannello_galleria.pack(fill=tk.BOTH, expand=True)

# Il blocco di esecuzione standard
if __name__ == "__main__":
    app = ApplicazionePrincipale()
    app.mainloop()