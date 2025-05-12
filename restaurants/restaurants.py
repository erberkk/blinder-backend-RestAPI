from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
import config

restaurants_bp = Blueprint("restaurants", __name__)

# MongoDB bağlantısı
client = MongoClient(config.MONGO_URI)
db = client["blinder"]
users_collection = db["users"]
locations_collection = db["locations"]
restaurants_collection = db["restaurants"]


@restaurants_bp.route("/restaurants", methods=["GET"])
@jwt_required()
def get_restaurants():
    """ Kullanıcının üniversite lokasyonuna göre restoranları getirir """
    try:
        user_email = get_jwt_identity()
        user = users_collection.find_one({"email": user_email}, {"_id": 0, "university_location": 1})
        if not user or "university_location" not in user:
            return jsonify({"error": "Kullanıcının üniversite lokasyonu bulunamadı!"}), 404

        university_location = user["university_location"]

        location = locations_collection.find_one({"name": university_location}, {"_id": 1})
        if not location:
            return jsonify({"error": "Lokasyon bulunamadı!"}), 404

        location_id = location["_id"]

        restaurants_data = restaurants_collection.find_one({"location_id": location_id}, {"_id": 0})
        if not restaurants_data:
            return jsonify({"error": "Bu lokasyona ait restoran bulunamadı!"}), 404

        response_data = {
            "message": "Restoranlar başarıyla alındı",
            "location": university_location,
            "data": restaurants_data
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

