from flask import Blueprint, request, jsonify, current_app
from app.supabase_client import supabase
# from app import emit_status_update

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.route("/payment", methods=["POST"])
def payment_webhook():
    data = request.json
    agent_id = data["agent_id"]
    if data["event"] == "payment_success":
        supabase.table("profiles").update(
            {"is_suspended": False}).eq("id", agent_id).execute()
    elif data["event"] == "payment_failed":
        supabase.table("profiles").update(
            {"is_suspended": True}).eq("id", agent_id).execute()
        supabase.table("agent_statuses").update(
            {"status": "offline"}).eq("agent_id", agent_id).execute()
        supabase.table("agent_queue").delete().eq(
            "agent_id", agent_id).execute()
    current_app.emit_status_update()
    return jsonify({"message": "Webhook processed"}), 200


@webhook_bp.route("/agent_update", methods=["POST"])
def agent_update_webhook():
    data = request.json
    supabase.table("agent_details").upsert(
        {"agent_id": data["agent_id"], **data["details"]}).execute()
    current_app.emit_status_update()
    return jsonify({"message": "Agent updated"}), 200
