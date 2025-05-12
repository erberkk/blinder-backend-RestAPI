from bson import ObjectId
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from datetime import datetime

import config

match_bp = Blueprint("match", __name__)

# MongoDB connection
client = MongoClient(config.MONGO_URI)
db = client["blinder"]
users_collection = db["users"]
swipes_collection = db["swipes"]
matches_collection = db["matches"]


def get_current_user():
    """Helper function to fetch current user object from DB based on the JWT identity (user email)."""
    user_email = get_jwt_identity()
    return users_collection.find_one({"email": user_email})


@match_bp.route("/potential", methods=["GET"])
@jwt_required()
def get_potential_matches():
    """
    Returns a list of potential matches for the current user.
    Basic logic:
    1) Filter out users already swiped on (liked or disliked).
    2) Filter by gender preference
    3) (Optionally) filter by university_location or other fields
    4) Possibly do more filtering or a scoring system.
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

    current_user_id = current_user["_id"]

    swiped_user_ids = swipes_collection.find(
        {"swiper_id": current_user_id},
        {"_id": 0, "swipee_id": 1}
    )
    swiped_user_ids = {doc["swipee_id"] for doc in swiped_user_ids}

    preferred_gender = current_user.get("gender_preference", "")
    if preferred_gender == "İkisi de":
        gender_filter = {"$in": ["Erkek", "Kadın"]}
    else:
        gender_filter = preferred_gender

    location_filter = current_user.get("university_location")

    query = {
        "_id": {"$ne": current_user_id},
        "_id": {"$nin": list(swiped_user_ids)},
        "gender": gender_filter,
        "university_location": location_filter,
    }

    query = {
        "$and": [
            {"_id": {"$ne": current_user_id}},
            {"_id": {"$nin": list(swiped_user_ids)}},
            {"gender": gender_filter},
            {"university_location": location_filter}
        ]
    }

    potential_users_cursor = users_collection.find(query)
    potential_users = list(potential_users_cursor)

    limited_results = []
    for user in potential_users[:10]:
        user_dict = {
            "user_id": str(user["_id"]),
            "name": user.get("name"),
            "university": user.get("university"),
            "university_location": user.get("university_location"),
            "birthdate": user.get("birthdate"),
            "zodiac_sign": user.get("zodiac_sign"),
            "gender": user.get("gender"),
            "height": user.get("height"),
            "relationship_goal": user.get("relationship_goal"),
            "likes": user.get("likes", []),
            "values": user.get("values", []),
            "alcohol": user.get("alcohol"),
            "smoking": user.get("smoking"),
            "religion": user.get("religion"),
            "political_view": user.get("political_view"),
            "favorite_food": user.get("favorite_food", []),
            "about": user.get("about"),
            "picture": user.get("picture", None)
        }
        limited_results.append(user_dict)

    return jsonify({"potential_matches": limited_results}), 200


@match_bp.route("/swipe", methods=["POST"])
@jwt_required()
def swipe():
    """
    The current user swipes on another user.
    Body: { "target_user_id": <string>, "action": "like" or "dislike" }
    1) Record the swipe in 'swipes' collection
    2) If it's a "like", check if the other user also liked you -> If so, it's a match
       -> Insert into 'matches' collection or handle as needed
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

    current_user_id = current_user["_id"]
    data = request.get_json()
    if not data:
        return jsonify({"error": "Geçersiz JSON"}), 400

    target_user_id_str = data.get("target_user_id")
    action = data.get("action")

    if not target_user_id_str or action not in ["like", "dislike"]:
        return jsonify({"error": "Eksik veya geçersiz parametreler!"}), 400

    try:
        target_user_id = int(target_user_id_str)
    except ValueError:
        return jsonify({"error": "Geçersiz user_id formatı!"}), 400

    if target_user_id == current_user_id:
        return jsonify({"error": "Kullanıcı kendi kendine swipe atamaz!"}), 400

    target_user = users_collection.find_one({"_id": target_user_id})
    if not target_user:
        return jsonify({"error": "Hedef kullanıcı bulunamadı!"}), 404

    swipe_doc = {
        "swiper_id": current_user_id,
        "swipee_id": target_user_id,
        "action": action,
        "timestamp": datetime.utcnow()
    }
    swipes_collection.insert_one(swipe_doc)

    if action == "like":
        mutual_swipe = swipes_collection.find_one({
            "swiper_id": target_user_id,
            "swipee_id": current_user_id,
            "action": "like"
        })
        if mutual_swipe:
            existing_match = matches_collection.find_one({
                "$or": [
                    {"user1_id": current_user_id, "user2_id": target_user_id},
                    {"user1_id": target_user_id, "user2_id": current_user_id}
                ]
            })
            if not existing_match:
                matches_collection.insert_one({
                    "user1_id": current_user_id,
                    "user2_id": target_user_id,
                    "matched_at": datetime.utcnow()
                })
            return jsonify({"message": "Match oluştu!", "match": True}), 200

    return jsonify({"message": "Swipe kaydedildi", "match": False}), 200


@match_bp.route("/unmatch", methods=["POST"])
@jwt_required()
def unmatch_user():
    """
    Allows the current user to unmatch another user.
    Removes the match record and adds dislike swipes to prevent re-matching.
    Body: { "match_id": "<string>" }
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

    current_user_id = current_user["_id"]

    data = request.get_json()
    if not data:
        return jsonify({"error": "Geçersiz JSON"}), 400

    match_id_str = data.get("match_id")
    if not match_id_str:
        return jsonify({"error": "match_id gerekli!"}), 400

    try:
        match_oid = ObjectId(match_id_str)
    except Exception:
        return jsonify({"error": "Geçersiz match_id formatı!"}), 400

    match_doc = matches_collection.find_one({"_id": match_oid})
    if not match_doc:
        return jsonify({"error": "Eşleşme bulunamadı!"}), 404

    user1_id = match_doc["user1_id"]
    user2_id = match_doc["user2_id"]

    if current_user_id != user1_id and current_user_id != user2_id:
        return jsonify({"error": "Bu eşleşmeyi kaldırma yetkiniz yok!"}), 403

    other_user_id = user1_id if current_user_id == user2_id else user2_id

    delete_result = matches_collection.delete_one({"_id": match_oid})

    if delete_result.deleted_count == 0:
        return jsonify({"error": "Eşleşme kaldırılamadı (belki zaten kaldırılmış)."}), 404

    now = datetime.utcnow()
    swipes_to_add = [
        {
            "swiper_id": current_user_id,
            "swipee_id": other_user_id,
            "action": "dislike",
            "timestamp": now,
            "reason": "unmatch"
        },
        {
            "swiper_id": other_user_id,
            "swipee_id": current_user_id,
            "action": "dislike",
            "timestamp": now,
            "reason": "unmatch"
        }
    ]

    try:
        swipes_collection.update_one(
            {"swiper_id": swipes_to_add[0]["swiper_id"], "swipee_id": swipes_to_add[0]["swipee_id"]},
            {"$set": swipes_to_add[0]},
            upsert=True
        )
        swipes_collection.update_one(
            {"swiper_id": swipes_to_add[1]["swiper_id"], "swipee_id": swipes_to_add[1]["swipee_id"]},
            {"$set": swipes_to_add[1]},
            upsert=True
        )
    except Exception as e:
        print(f"Error adding dislike swipes after unmatch {match_id_str}: {e}")
        return jsonify({"message": "Eşleşme kaldırıldı, ancak tekrar görünmelerini engellemede bir sorun oluştu."}), 200

    return jsonify({"message": "Eşleşme başarıyla kaldırıldı."}), 200


@match_bp.route("/my-matches", methods=["GET"])
@jwt_required()
def get_my_matches():
    """
    Returns a list of all matches for the current user,
    including basic info about the matched user (name, picture, etc.).
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

    current_user_id = current_user["_id"]

    my_matches_cursor = matches_collection.find({
        "$or": [
            {"user1_id": current_user_id},
            {"user2_id": current_user_id}
        ]
    })

    results = []
    for match_doc in my_matches_cursor:
        match_id = str(match_doc["_id"])
        user1_id = match_doc["user1_id"]
        user2_id = match_doc["user2_id"]

        if user1_id == current_user_id:
            other_user_id = user2_id
        else:
            other_user_id = user1_id

        other_user = users_collection.find_one({"_id": other_user_id})
        if not other_user:
            continue

        results.append({
            "match_id": match_id,
            "user_id": str(other_user["_id"]),
            "name": other_user.get("name"),
            "picture": other_user.get("picture"),
            "university": other_user.get("university"),
            "university_location": other_user.get("university_location"),
            "birthdate": other_user.get("birthdate"),
            "matched_at": match_doc.get("matched_at").isoformat() if match_doc.get("matched_at") else None
        })

    return jsonify({"matches": results}), 200

