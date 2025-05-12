import requests
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import config
import re
from datetime import datetime
from bson import ObjectId

auth_bp = Blueprint("auth", __name__)

# MongoDB bağlantısı
client = MongoClient(config.MONGO_URI)
db = client["blinder"]
users_collection = db["users"]
counters_collection = db["counters"]
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


def get_next_user_id():
    """ Kullanıcı ID'sini otomatik artırarak döndüren fonksiyon """
    counter = counters_collection.find_one_and_update(
        {"_id": "user_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return counter["seq"]


def is_academic_email(email):
    """ Akademik e-posta uzantılarını kontrol eden fonksiyon """
    academic_email_pattern = r".*\.(edu|ac\.[a-z]{2,3}|edu\.[a-z]{2,3})$"
    return re.match(academic_email_pattern, email) is not None


def get_zodiac_sign(birthdate):
    """ Doğum tarihine göre burç hesaplayan fonksiyon """
    zodiac_dates = [
        (1, 20, "Oğlak"), (2, 19, "Kova"), (3, 20, "Balık"), (4, 20, "Koç"),
        (5, 21, "Boğa"), (6, 21, "İkizler"), (7, 23, "Yengeç"), (8, 23, "Aslan"),
        (9, 23, "Başak"), (10, 23, "Terazi"), (11, 22, "Akrep"), (12, 22, "Yay"),
        (12, 31, "Oğlak")
    ]
    for m, d, sign in zodiac_dates:
        if (birthdate.month == m and birthdate.day <= d) or (birthdate.month == m - 1 and birthdate.day > d):
            return sign
    return "Bilinmiyor"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@auth_bp.route("/google-login", methods=["POST"])
def google_login():
    """ Google OAuth ile giriş yapan kullanıcıyı doğrulayan endpoint """
    try:
        print("func called")
        token = request.json.get("idToken")
        if not token:
            return jsonify({"error": "ID Token gerekli!"}), 400

        google_info = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            config.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=5
        )
        email = google_info.get("email")
        if not email or not is_academic_email(email):
            return jsonify({"error": "Sadece akademik e-postalar kabul edilir!"}), 400

        user = users_collection.find_one({"email": email})
        if not user:
            user_id = get_next_user_id()
            user = {
                "_id": user_id,
                "name": google_info.get("name", ""),
                "email": email,
                "google_id": google_info.get("sub", ""),
                "picture": google_info.get("picture", ""),
                "locale": google_info.get("locale", "tr"),
                "created_at": datetime.utcnow(),
                "university": None,
                "university_location": None,
                "birthdate": None,
                "zodiac_sign": None,
                "gender": None,
                "gender_preference": None,
                "height": None,
                "relationship_goal": None,
                "likes": [],
                "values": [],
                "alcohol": None,
                "smoking": None,
                "religion": None,
                "political_view": None,
                "favorite_food": []
            }
            users_collection.insert_one(user)

        access_token = create_access_token(identity=user["email"])
        return jsonify({"access_token": access_token, "user": user})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route("/microsoft-login", methods=["POST"])
def microsoft_login():
    """ Microsoft OAuth ile giriş yapan kullanıcıyı doğrulayan endpoint """
    try:
        code = request.json.get("idToken")
        if not code:
            return jsonify({"error": "Authorization code gerekli!"}), 400

        token_url = f"https://login.microsoftonline.com/{config.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
        data = {
            "client_id": config.MICROSOFT_CLIENT_ID,
            "scope": "openid profile email User.Read",
            "code": code,
            "redirect_uri": config.MICROSOFT_REDIRECT_URI,
            "grant_type": "authorization_code",
            "code_verifier": request.json.get("codeVerifier")
        }

        token_response = requests.post(token_url, data=data)
        if token_response.status_code != 200:
            return jsonify({
                "error": "Token exchange başarısız!",
                "details": token_response.text
            }), 400

        tokens = token_response.json()
        id_token_value = tokens.get("id_token")
        access_token_ms = tokens.get("access_token")
        if not id_token_value or not access_token_ms:
            return jsonify({"error": "Token exchange'den gerekli tokenlar alınamadı!"}), 400

        headers = {"Authorization": f"Bearer {access_token_ms}"}
        userinfo_response = requests.get("https://graph.microsoft.com/oidc/userinfo", headers=headers)
        if userinfo_response.status_code != 200:
            return jsonify({
                "error": "Microsoft doğrulama başarısız!",
                "details": userinfo_response.text
            }), 400

        microsoft_info = userinfo_response.json()
        email = microsoft_info.get("email")
        if not email or not is_academic_email(email):
            return jsonify({"error": "Sadece akademik e-postalar kabul edilir!"}), 400

        user = users_collection.find_one({"email": email})
        if not user:
            user_id = get_next_user_id()
            user = {
                "_id": user_id,
                "name": microsoft_info.get("name", ""),
                "email": email,
                "microsoft_id": microsoft_info.get("sub", ""),
                "picture": microsoft_info.get("picture", ""),
                "locale": microsoft_info.get("locale", "tr"),
                "created_at": datetime.utcnow(),
                "university": None,
                "university_location": None,
                "birthdate": None,
                "zodiac_sign": None,
                "gender": None,
                "gender_preference": None,
                "height": None,
                "relationship_goal": None,
                "likes": [],
                "values": [],
                "alcohol": None,
                "smoking": None,
                "religion": None,
                "political_view": None,
                "favorite_food": []
            }
            users_collection.insert_one(user)

        access_token = create_access_token(identity=user["email"])
        return jsonify({"access_token": access_token, "user": user})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route("/update-profile", methods=["POST"])
@jwt_required()
def update_profile():
    """ Kullanıcı profilini güncelleme """
    try:
        user_email = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({"error": "Geçersiz JSON"}), 400

        required_fields = [
            "birthdate", "university", "university_location",
            "gender", "gender_preference",
            "height", "relationship_goal",
            "likes", "values", "alcohol", "smoking",
            "religion", "political_view", "favorite_food", "about"
        ]

        for field in required_fields:
            field_value = data.get(field)
            if isinstance(field_value, list):
                if len(field_value) == 0:
                    return jsonify({"error": f"{field} eksik veya boş olamaz!"}), 400
            else:
                if not field_value:
                    return jsonify({"error": f"{field} eksik veya boş olamaz!"}), 400

        try:
            birthdate = datetime.strptime(data["birthdate"], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Doğum tarihi formatı hatalı! Format: YYYY-MM-DD"}), 400

        today = datetime.now()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        if age < 18:
            return jsonify({"error": "18 yaşından küçükler kayıt olamaz."}), 400

        zodiac_sign = get_zodiac_sign(birthdate)

        update_data = {
            "university": data["university"],
            "university_location": data["university_location"],
            "birthdate": birthdate.strftime("%Y-%m-%d"),
            "zodiac_sign": zodiac_sign,
            "gender": data["gender"],
            "gender_preference": data["gender_preference"],
            "height": data["height"],
            "relationship_goal": data["relationship_goal"],
            "likes": data["likes"],
            "values": data["values"],
            "alcohol": data["alcohol"],
            "smoking": data["smoking"],
            "religion": data["religion"],
            "political_view": data["political_view"],
            "favorite_food": data["favorite_food"],
            "about": data["about"]
        }

        users_collection.update_one({"email": user_email}, {"$set": update_data})

        return jsonify({"message": "Profil güncellendi", "data": update_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    try:
        user_email = get_jwt_identity()
        user = users_collection.find_one({"email": user_email}, {"password": 0})
        if not user:
            return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

        spotify_doc = db.spotify.find_one(
            {"user_id": user["_id"]},
            {"_id": 0, "user_id": 0, "created_at": 0, "updated_at": 0}
        )
        if spotify_doc:
            user.update(spotify_doc)

        return jsonify({"message": "Profil bilgileri alındı", "user": user})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/universities", methods=["GET"])
def get_universities():
    try:
        universities = list(db.universities.find({}, {"_id": 0, "location_id": 1, "universities": 1}))

        location_ids = {uni["location_id"] for uni in universities}

        locations = db.locations.find({"_id": {"$in": list(location_ids)}}, {"_id": 1, "name": 1})
        location_map = {loc["_id"]: loc["name"] for loc in locations}

        for uni in universities:
            uni["location"] = location_map.get(uni.pop("location_id"), "Unknown")

        return jsonify(universities)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/photos/upload", methods=["POST"])
@jwt_required()
def upload_photos():
    try:
        user_email = get_jwt_identity()
        user = users_collection.find_one({"email": user_email})
        if not user:
            return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

        user_id = user["_id"]
        data = request.get_json()
        photos = data.get("photos")
        if not photos or not isinstance(photos, list):
            return jsonify({"error": "Fotoğraflar eksik!"}), 400

        if len(photos) > 3:
            return jsonify({"error": "Aynı anda en fazla 3 fotoğraf yükleyebilirsiniz!"}), 400

        photos_doc = db.photos.find_one({"user_id": user_id})
        existing_photos = photos_doc["photos"] if photos_doc and "photos" in photos_doc else []
        if len(existing_photos) + len(photos) > 3:
            return jsonify({"error": "Maksimum 3 fotoğraf yükleyebilirsiniz!"}), 400

        new_photos = []
        for photo in photos:
            file_name = photo.get("file_name")
            image_data = photo.get("data")
            if not file_name or not image_data:
                return jsonify({"error": "Fotoğraf verisi eksik!"}), 400
            if not allowed_file(file_name):
                return jsonify({"error": f"{file_name} dosya tipi kabul edilmez!"}), 400

            photo_item = {
                "photo_id": str(ObjectId()),
                "file_name": file_name,
                "data": image_data,
                "uploaded_at": datetime.utcnow()
            }
            new_photos.append(photo_item)

        if photos_doc:
            db.photos.update_one(
                {"user_id": user_id},
                {"$push": {"photos": {"$each": new_photos}}}
            )
        else:
            db.photos.insert_one({
                "user_id": user_id,
                "photos": new_photos
            })

        return jsonify({"message": "Fotoğraflar yüklendi", "photos": new_photos}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/photos", methods=["GET"])
@jwt_required()
def get_photos():
    try:
        user_email = get_jwt_identity()
        user = users_collection.find_one({"email": user_email})
        if not user:
            return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

        user_id = user["_id"]
        photos_doc = db.photos.find_one({"user_id": user_id})
        photos = photos_doc["photos"] if photos_doc and "photos" in photos_doc else []
        return jsonify({"photos": photos}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/photos/<photo_id>", methods=["DELETE"])
@jwt_required()
def delete_photo(photo_id):
    try:
        user_email = get_jwt_identity()
        user = users_collection.find_one({"email": user_email})
        if not user:
            return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

        user_id = user["_id"]
        result = db.photos.update_one(
            {"user_id": user_id},
            {"$pull": {"photos": {"photo_id": photo_id}}}
        )
        if result.modified_count == 0:
            return jsonify({"error": "Fotoğraf bulunamadı veya yetkisiz erişim!"}), 404

        return jsonify({"message": "Fotoğraf silindi"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/user-photos/<int:user_id>", methods=["GET"])
def get_user_photos_by_id(user_id):
    try:
        photos_doc = db.photos.find_one({"user_id": user_id})
        photos = photos_doc["photos"] if photos_doc and "photos" in photos_doc else []
        return jsonify({"photos": photos}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
