from flask import Blueprint, request, jsonify, current_app
import requests
from app.supabase_client import supabase
# from app import socketio
from dotenv import load_dotenv
import os

load_dotenv()

GHL_API_TOKEN = os.getenv('GH_TOKEN')


opener_bp = Blueprint("opener", __name__)


@opener_bp.route("/status", methods=["PUT"])
def update_opener_status():
    data = request.json
    # 'online', 'offline'
    opener_id, new_status = data["opener_id"], data["status"]

    supabase.table("opener_statuses").update(
        {"status": new_status}).eq("opener_id", opener_id).execute()
    # Trigger `handle_opener_status_change` will handle queue cleanup if needed
    current_app.emit_status_update()
    return jsonify({"message": "Status updated"}), 200


@opener_bp.route("/transfer", methods=["POST"])
def record_transfer():
    data = request.json
    agent_id, opener_id, contact_id = data["agent_id"], data["opener_id"], data["contact_id"]

    # Fetch GHL token for opener (simplified; use refresh logic in production)
    token = supabase.table("ghl_tokens").select("access_token").eq(
        "user_id", opener_id).single().execute().data["access_token"]

    # Fetch and update GHL contact
    ghl_response = requests.get(
        f"https://api.gohighlevel.com/v1/contacts/{contact_id}", headers={"Authorization": f"Bearer {token}"})
    contact = ghl_response.json()
    requests.put(
        f"https://api.gohighlevel.com/v1/contacts/{contact_id}",
        json={"custom_fields": {"agent_name": agent_id, "opener_name": opener_id}},
        headers={"Authorization": f"Bearer {token}"}
    )

    # Record transfer
    transfer = {"agent_id": agent_id,
                "recorded_by": opener_id, "notes": data.get("notes")}
    supabase.table("transfers").insert(transfer).execute()

    # Update agent status and remove from queue
    supabase.table("agent_statuses").update(
        {"status": "taking_transfer"}).eq("agent_id", agent_id).execute()
    supabase.table("agent_queue").delete().eq("agent_id", agent_id).execute()
    # Hardcoded; fetch from config if added
    current_app.socketio.emit("transfer_assigned", {
                             "agent_id": agent_id, "duration": 15})
    current_app.emit_status_update()
    return jsonify({"message": "Transfer recorded"}), 200


@opener_bp.route("/agents", methods=["GET"])
def get_agents():
    agents = supabase.table("profiles").select(
        "*, agent_statuses(status), agent_queue(position), agent_details(*)").eq("role", "agent").execute().data
    return jsonify({"active": [a for a in agents if a["agent_statuses"]["status"] == "ready"], "all": agents}), 200
