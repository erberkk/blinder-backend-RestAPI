from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    verify_jwt_in_request,
    get_jwt_identity,
    create_access_token
)
import config
from restaurants.restaurants import restaurants_bp
from matches.matches_routes import match_bp
from message.message import message_bp
from login.auth_routes import auth_bp
from spotify import spotify_bp
from datetime import datetime

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

app.config["JWT_SECRET_KEY"] = config.JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 604800
jwt = JWTManager(app)

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(spotify_bp, url_prefix="/spotify")
app.register_blueprint(restaurants_bp, url_prefix="/restaurant")
app.register_blueprint(match_bp, url_prefix="/match")
app.register_blueprint(message_bp, url_prefix="/message")


@app.after_request
def refresh_expiring_jwt(response):
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            new_token = create_access_token(identity=identity)
            response.headers["X-Refresh-Token"] = new_token
    except Exception as e:
        pass
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)
