import jwt
import flask


app = flask.Flask(__name__)

app.config['SECRET_KEY'] = "aperturaFrancese"
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


@app.route('/private')
@token_required
def auth():
    return 'Token JWT verificato correttamente, benvenuto nella pagina privata!!!'

@app.route('/login', methods=['GET'])
def login():
    print("entrato")
    if flask.request.args.get("username") == "samuele" and \
            flask.request.args.get("password") == "123456":
        flask.session['logged_in'] = True
        token = jwt.encode({
            'user': flask.request.args.get('username')
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return flask.jsonify({'token': token})
    else:
        return flask.jsonify({"messaggio": "Errore di autenticazione"}), 401