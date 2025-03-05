from flask import Blueprint, request, jsonify
from app.supabase_client import supabase
import uuid
import hashlib
import time

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email, password = data["email"], hashlib.sha256(
        data["password"].encode()).hexdigest()
    user = supabase.table("profiles").select(
        "*").eq("email", email).single().execute().data
    # Assume auth.users handles password; adjust for your auth setup
    if user:
        return jsonify({"user": user, "message": "Login successful"}), 200
    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route("/register", methods=["GET"])  # Super Admin only
def register():

    # data = request.json
    # emai = data["email"]
    # password = data["password"]
    # role = data["role"]
    # full_name = data["full_name"]
    # phone = data["phone"]
    # license_states = data["license_states"]
    # crm_plan = data["crm_plan"]
    # fe_plan = data["fe_plan"]
    # is_suspended = False

    # if data["created_by_role"] != "super_admin":
    #     return jsonify({"error": "Unauthorized"}), 403
    # user_id = str(uuid.uuid4())
    # profile = {
    #     "id": user_id,
    #     "email": data["email"],
    #     "role": data["role"],
    #     "full_name": data.get("full_name"),
    #     "is_suspended": False
    # }
    # supabase.table("profiles").insert(profile).execute()
    # if data["role"] == "agent":
    #     supabase.table("agent_statuses").insert(
    #         {"agent_id": user_id, "status": "offline"}).execute()
    # elif data["role"] == "opener":
    #     supabase.table("opener_statuses").insert(
    #         {"opener_id": user_id, "status": "offline"}).execute()
    try:
        auth_record_response = supabase.auth.sign_up(
            {"email": "jksadfjk@example.com", "password": "password"})

        record_id = auth_record_response.model_dump()["user"]["id"]
        if not record_id:
            return jsonify({"error": "User creation failed"}), 500

        while True:
            profile_record_response = supabase.table(
                "profiles").update({"full_name": "Test Full Name"}).eq("id", record_id).execute()
            if profile_record_response.data:
                supabase.table(
                    "profiles").update({"full_name": "Test Full Name"}).eq("id", record_id).execute()
                break
            else:
                print('###############( Test Block )#################')
                print()
                print(profile_record_response)
                print()
                print('#############( End Test Block )###############')
                time.sleep(5)
                continue

        print('###############( Test Block )#################')
        print()
        print(profile_record_response)
        print()
        print('#############( End Test Block )###############')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "User created", "user": "OK"}), 201
