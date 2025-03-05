from flask import Blueprint, request, jsonify, current_app
from app.supabase_client import supabase
# from app import emit_status_update

agent_bp = Blueprint("agent", __name__)


@agent_bp.route("/status", methods=["PUT"])
def update_status():
    data = request.json
    # 'ready', 'break', 'offline', 'taking_transfer'
    agent_id, new_status = data["agent_id"], data["status"]

    # Check suspension
    is_suspended = supabase.table("profiles").select("is_suspended").eq(
        "id", agent_id).single().execute().data["is_suspended"]
    if is_suspended:
        return jsonify({"error": "Account suspended"}), 403

    # Check opener availability for 'ready'
    if new_status == "ready":
        openers = supabase.table("opener_statuses").select(
            "status").execute().data
        if not any(opener["status"] == "online" for opener in openers):
            return jsonify({"error": "No openers online"}), 400
        # Update queue position
        queue = supabase.table("agent_queue").select("position").execute().data
        position = max([a["position"] for a in queue], default=0) + 1
        supabase.table("agent_queue").upsert(
            {"agent_id": agent_id, "position": position}).execute()
    elif new_status in ["break", "offline"]:
        supabase.table("agent_queue").delete().eq(
            "agent_id", agent_id).execute()

    # Update status (trigger handles metrics)
    supabase.table("agent_statuses").update(
        {"status": new_status}).eq("agent_id", agent_id).execute()
    # emit_status_update()
    current_app.emit_status_update()
    return jsonify({"message": "Status updated"}), 200


@agent_bp.route("/profile/<agent_id>", methods=["GET"])
def get_profile(agent_id):
    profile = supabase.table("profiles").select(
        "*, agent_details(*), agent_statuses(status), agent_queue(position)").eq("id", agent_id).single().execute().data
    return jsonify(profile), 200
