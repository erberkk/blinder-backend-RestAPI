from flask import Blueprint, request, jsonify, redirect
import requests
import config
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, decode_token
from pymongo import MongoClient
from datetime import datetime

spotify_bp = Blueprint("spotify", __name__)

# MongoDB Bağlantısı
client = MongoClient(config.MONGO_URI)
db = client["blinder"]
users_collection = db["users"]
spotify_collection = db["spotify"]

# Spotify API Bilgileri
SPOTIFY_CLIENT_ID = config.SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = config.SPOTIFY_CLIENT_SECRET
SPOTIFY_REDIRECT_URI = config.SPOTIFY_REDIRECT_URI


def get_spotify_token(code):
    """ Spotify'dan Access Token almak için istek yapar """
    url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }
    response = requests.post(url, data=data)
    return response.json()


def refresh_spotify_token(refresh_token):
    """ Spotify Refresh Token kullanarak yeni Access Token alır """
    token_url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": config.SPOTIFY_CLIENT_ID,
        "client_secret": config.SPOTIFY_CLIENT_SECRET
    }

    response = requests.post(token_url, data=data)
    new_token_data = response.json()

    if "access_token" in new_token_data:
        return new_token_data["access_token"]
    else:
        return None


@spotify_bp.route("/login", methods=["GET"])
def spotify_login():
    """ Kullanıcıyı Spotify OAuth'a yönlendirir """
    auth_url = (
        "https://accounts.spotify.com/authorize"
        f"?client_id={SPOTIFY_CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}"
        "&scope=user-top-read"
    )
    return redirect(auth_url)


@spotify_bp.route("/callback", methods=["GET"])
def spotify_callback():
    """Spotify'dan dönen kod ile Access Token al ve kullanıcıya ait spotify verilerini spotify koleksiyonuna kaydeder"""
    code = request.args.get("code")
    user_token = request.args.get("state")  # Frontend’den gelen JWT Token

    if not code:
        return jsonify({"error": "Spotify doğrulaması başarısız!"}), 400
    if not user_token:
        return jsonify({"error": "Eksik kullanıcı tokenı!"}), 400

    # Spotify’dan token al
    token_data = get_spotify_token(code)
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        return jsonify({"error": "Spotify erişim hatası!"}), 400

    # Kullanıcının Spotify ID'sini al
    user_info = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    spotify_id = user_info.get("id")

    # Kullanıcıyı JWT'den çöz
    try:
        decoded_data = decode_token(user_token)
        user_email = decoded_data["sub"]
    except Exception as e:
        return jsonify({"error": f"JWT Çözümleme Hatası: {str(e)}"}), 400

    if not user_email:
        return jsonify({"error": "Geçersiz JWT veya kullanıcı bulunamadı!"}), 400

    user = users_collection.find_one({"email": user_email})
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı!"}), 400

    existing_record = spotify_collection.find_one({"user_id": user["_id"]})
    if existing_record:
        if existing_record.get("spotify_id") and existing_record["spotify_id"] != spotify_id:
            return jsonify({"error": "Bu kullanıcı zaten başka bir Spotify hesabı ile bağlı!"}), 400

        spotify_collection.update_one(
            {"user_id": user["_id"]},
            {"$set": {
                "spotify_id": spotify_id,
                "spotify_access_token": access_token,
                "spotify_refresh_token": refresh_token,
                "spotify_connected": True,
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        new_record = {
            "user_id": user["_id"],
            "spotify_id": spotify_id,
            "spotify_access_token": access_token,
            "spotify_refresh_token": refresh_token,
            "spotify_connected": True,
            "created_at": datetime.utcnow()
        }
        spotify_collection.insert_one(new_record)

    return redirect("http://localhost:8081/profile/profile")


@spotify_bp.route("/top-tracks", methods=["GET"])
@jwt_required()
def get_top_tracks():
    """ Kullanıcının en çok dinlediği şarkıları getirir """
    user_email = get_jwt_identity()
    user = users_collection.find_one({"email": user_email})

    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı!"}), 400

    spotify_record = spotify_collection.find_one({"user_id": user["_id"]})
    if not spotify_record or not spotify_record.get("spotify_access_token"):
        return jsonify({"error": "Spotify hesabı bağlı değil!"}), 400

    access_token = spotify_record["spotify_access_token"]
    refresh_token = spotify_record["spotify_refresh_token"]

    url = "https://api.spotify.com/v1/me/top/tracks?time_range=short_term&limit=10"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 401:
        new_access_token = refresh_spotify_token(refresh_token)
        if new_access_token:
            spotify_collection.update_one(
                {"user_id": user["_id"]},
                {"$set": {"spotify_access_token": new_access_token}}
            )
            headers["Authorization"] = f"Bearer {new_access_token}"
            response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "Spotify verisi alınamadı!", "details": response.json()}), 400

    tracks_data = response.json().get("items", [])

    tracks = []
    for track in tracks_data:
        tracks.append({
            "name": track["name"],
            "artists": [artist["name"] for artist in track["artists"]],
            "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "spotify_url": track["external_urls"]["spotify"]
        })

    return jsonify({"tracks": tracks})


@spotify_bp.route("/top-artists", methods=["GET"])
@jwt_required()
def get_top_artists():
    """ Kullanıcının en çok dinlediği sanatçıları getirir """
    user_email = get_jwt_identity()
    user = users_collection.find_one({"email": user_email})

    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı!"}), 400

    spotify_record = spotify_collection.find_one({"user_id": user["_id"]})
    if not spotify_record or not spotify_record.get("spotify_access_token"):
        return jsonify({"error": "Spotify hesabı bağlı değil!"}), 400

    access_token = spotify_record["spotify_access_token"]
    refresh_token = spotify_record["spotify_refresh_token"]

    url = "https://api.spotify.com/v1/me/top/artists?time_range=short_term&limit=10"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 401:
        new_access_token = refresh_spotify_token(refresh_token)
        if new_access_token:
            spotify_collection.update_one(
                {"user_id": user["_id"]},
                {"$set": {"spotify_access_token": new_access_token}}
            )
            headers["Authorization"] = f"Bearer {new_access_token}"
            response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "Spotify verisi alınamadı!", "details": response.json()}), 400

    artists_data = response.json().get("items", [])

    artists = []
    for artist in artists_data:
        artists.append({
            "name": artist["name"],
            "image": artist["images"][0]["url"] if artist["images"] else None,
            "spotify_url": artist["external_urls"]["spotify"]
        })

    return jsonify({"artists": artists})
