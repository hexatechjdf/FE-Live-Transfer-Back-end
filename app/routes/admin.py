import uuid
from flask import Blueprint, request, jsonify, current_app
from app.supabase_client import supabase
from .utils import fetch_data_from_table
# from app import emit_status_update

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["POST", "PUT"])
def manage_users():
    data = request.json
    if request.method == "POST":
        user_id = str(uuid.uuid4())
        profile = {"id": user_id, "email": data["email"],
                   "role": data["role"], "full_name": data.get("full_name")}
        supabase.table("profiles").insert(profile).execute()
        if data["role"] == "agent":
            supabase.table("agent_statuses").insert(
                {"agent_id": user_id, "status": "offline"}).execute()
            if "agent_details" in data:
                supabase.table("agent_details").insert(
                    {"agent_id": user_id, **data["agent_details"]}).execute()
        elif data["role"] == "opener":
            supabase.table("opener_statuses").insert(
                {"opener_id": user_id, "status": "offline"}).execute()
    else:
        supabase.table("profiles").update(
            data["profile"]).eq("id", data["id"]).execute()
        if "agent_details" in data:
            supabase.table("agent_details").update(
                data["agent_details"]).eq("agent_id", data["id"]).execute()
    current_app.emit_status_update()
    return jsonify({"message": "User managed"}), 200


@admin_bp.route("/subscription/<agent_id>", methods=["PUT"])
def override_subscription(agent_id):
    data = request.json
    supabase.table("profiles").update(
        {"is_suspended": not data["active"]}).eq("id", agent_id).execute()
    if not data["active"]:
        supabase.table("agent_statuses").update(
            {"status": "offline"}).eq("agent_id", agent_id).execute()
        supabase.table("agent_queue").delete().eq(
            "agent_id", agent_id).execute()
    current_app.emit_status_update()
    return jsonify({"message": "Subscription updated"}), 200


@admin_bp.route("/metrics", methods=["GET"])
def get_metrics():
    # e.g., "2025-01-01:2025-02-01"
    date_filter = request.args.get("date_range")
    if date_filter:
        start, end = date_filter.split(":")
        metrics = supabase.table("agent_metrics").select(
            "*").gte("started_at", start).lte("started_at", end).execute().data
    else:
        metrics = supabase.table("agent_metrics").select("*").execute().data
    transfers = supabase.table("transfers").select("*").execute().data
    return jsonify({"agent_metrics": metrics, "transfers": transfers}), 200


@admin_bp.route("/dashboard-states", methods=["GET"])
def dashboard_states():
    # total_agents = supabase.table("agent_details").select(
    #     "*", count="exact").execute().count
    active_openers = supabase.table("opener_statuses").select(
        "*", count="exact").execute().count

    return jsonify({"message": "OK", "total_agents": total_agents}), 200


# Get agent details
@admin_bp.route('/agent-details', methods=['GET'])
def agent_details():
    try:
        response = (
            supabase.from_('profiles')
            .select(
                "*, agent_details(*), agent_statuses(status)"
            )
            .eq('role', 'agent')
            .execute()
        )

        if not response.data:
            return jsonify({"error": "No agents found"}), 404

        return jsonify(response.data), 200

    except ValueError as ve:
        print(f"Value Error: {str(ve)}")
        return jsonify({
            "error": "Invalid data format",
            "details": str(ve)
        }), 400

    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected Error: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@admin_bp.route('opener-statuses', methods=['GET'])
def opener_statuses():
    response = fetch_data_from_table('opener_statuses')
    response_data = response[0]
    response_status = response[1]
    return jsonify(response_data), response_status
