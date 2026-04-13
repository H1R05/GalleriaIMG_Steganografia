import tkinter as tk
import ttkbootstrap as ttk
#Importiamo il mattoncino che abbiamo creato nell'altro file!
from login import PannelloLogin

class ApplicazionePrincipale(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Galleria Immagini")
        self.style = ttk.Style()
        self.style.theme_use("darkly")
        self.geometry("1100x800")
        self.minsize(1100, 800)
        self.token_acquisito = None

        # Passo 'self' come argomento, dicendogli: "Io sono il tuo master (genitore)"
        self.panello_login = PannelloLogin(self)
        self.panello_login.pack(expand=True, fill="both")

    def login_completato(self, token_ricevuto):
        """Viene innescato da login.py quando l'accesso ha successo."""
        # Import differito: evita di caricare subito moduli pesanti all'avvio app.
        from vista_galleria import PannelloGalleria
        
        # 1. Salviamo il token (nota: token_ricevuto NON ha il self davanti!)
        self.token_jwt = token_ricevuto
        
        # Stampiamo in console per fare debug da sistemisti
        print(f"Login effettuato! Token salvato in memoria: {self.token_jwt}")

        # 2. Distruggiamo visivamente il pannello di login
        # (Assicurati che il nome sia corretto. Se nel tuo def __init__ 
        # lo avevi chiamato self.panello_login, usa quello!)
        if hasattr(self, "panello_login"):
            self.panello_login.pack_forget()

        # 3. Creiamo la Galleria e la posizioniamo a schermo
        self.pannello_galleria = PannelloGalleria(self)
        self.pannello_galleria.pack(fill=tk.BOTH, expand=True)
        
        # 4. Ordiniamo alla galleria di leggere la memoria e dipingere il footer
        self.pannello_galleria.aggiorna_stato_auth()

# Il blocco di esecuzione standard
if __name__ == "__main__":
    app = ApplicazionePrincipale()
    app.mainloop()