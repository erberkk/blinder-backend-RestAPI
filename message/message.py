from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId  # Import ObjectId
import config

message_bp = Blueprint("message", __name__)

client = MongoClient(config.MONGO_URI)
db = client["blinder"]
messages_collection = db["messages"]
matches_collection = db["matches"]
users_collection = db["users"]


def get_current_user():
    user_email = get_jwt_identity()
    return users_collection.find_one({"email": user_email})


@message_bp.route("/conversation", methods=["GET"])
@jwt_required()
def get_conversation():
    """
    Retrieve all messages for a given match_id.
    URL param: ?match_id=123
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

    match_id = request.args.get("match_id")
    if not match_id:
        return jsonify({"error": "match_id parametresi gerekli!"}), 400

    try:
        match_oid = ObjectId(match_id)
    except Exception:
        return jsonify({"error": "Geçersiz match_id!"}), 400

    match_doc = matches_collection.find_one({"_id": match_oid})
    if not match_doc:
        return jsonify({"error": "Eşleşme bulunamadı!"}), 404

    if (match_doc["user1_id"] != current_user["_id"]) and (match_doc["user2_id"] != current_user["_id"]):
        return jsonify({"error": "Bu eşleşmede yetkiniz yok!"}), 403

    msgs_cursor = messages_collection.find({"match_id": match_oid}).sort("timestamp", 1)
    messages = []
    for msg in msgs_cursor:
        messages.append({
            "message_id": str(msg["_id"]),
            "match_id": match_id,
            "sender_id": msg["sender_id"],
            "message_text": msg["message_text"],
            "timestamp": msg["timestamp"].isoformat()
        })

    return jsonify({"messages": messages}), 200


@message_bp.route("/send", methods=["POST"])
@jwt_required()
def send_message():
    """
    Body: {
      "match_id": "123",
      "message_text": "Hello!"
    }
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Kullanıcı bulunamadı!"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Geçersiz JSON"}), 400

    match_id_str = data.get("match_id")
    message_text = data.get("message_text", "").strip()
    if not match_id_str or not message_text:
        return jsonify({"error": "match_id ve message_text gerekli!"}), 400

    try:
        match_oid = ObjectId(match_id_str)
    except Exception:
        return jsonify({"error": "Geçersiz match_id!"}), 400

    match_doc = matches_collection.find_one({"_id": match_oid})
    if not match_doc:
        return jsonify({"error": "Eşleşme (match) bulunamadı!"}), 404

    if (match_doc["user1_id"] != current_user["_id"]) and (match_doc["user2_id"] != current_user["_id"]):
        return jsonify({"error": "Bu eşleşmede mesaj gönderemezsiniz!"}), 403

    # Insert the new message
    msg_doc = {
        "match_id": match_oid,
        "sender_id": current_user["_id"],
        "message_text": message_text,
        "timestamp": datetime.utcnow()
    }
    result = messages_collection.insert_one(msg_doc)

    return jsonify({
        "message": "Mesaj gönderildi!",
        "message_id": str(result.inserted_id),
        "timestamp": msg_doc["timestamp"].isoformat()
    }), 200
