import jwt
import flask
import pymongo


app = flask.Flask(__name__)

app.config['SECRET_KEY'] = "segreto_123"
client = pymongo.MongoClient("mongodb://mongodb:27017/")

db = client["GalleriaImg"]
col = db["utenti"]

def token_required(func):
    def decorated(*args, **kwargs):
        token = flask.request.args.get('token')
        print(token)
        if not token:
            return flask.jsonify({'message': 'Token mcancante, si salvi chi può!!!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return flask.jsonify({'message': 'Token non valido: AIUTO!!!!!!'}), 403
        return func(*args, **kwargs)
    return decorated



@app.route('/login', methods=['POST'])
def login():
    dati_ricevuti = flask.request.get_json()
    print(dati_ricevuti)
    if not dati_ricevuti:
        return flask.jsonify({"messaggio": "Nessun dato fornito"}), 400

    username = dati_ricevuti["username"]
    password = dati_ricevuti["password"]

    utente_trovato = col.find_one({
            "utente.username":username,
            "utente.password":password
    })

    if utente_trovato:
        token = jwt.encode({
            'user': username
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return flask.jsonify({'token': token}), 200
    else:
        return flask.jsonify({"messaggio": "Username o Password errati"}), 401
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)