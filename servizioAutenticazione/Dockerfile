#Usiamo la versione slim per otimizzare le risorse
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
#--host=0.0.0.0 se non lo mettiamo blocca le richieste che arrivano dal pc fisico
CMD ["flask", "run", "--host=0.0.0.0"]

#docker build -t autenticazioneimg .
#docker run --name container_auth -p 5000:5000 -d autenticazioneimg
#-d significa detached e dice a docker di far girare il server in background, se non lo metti il terminale rimarebbe bloccato con i log del server.