
from datetime import datetime
import supabase
from .utils import fetch_data_from_table, get_real_time_response, handle_status_change, validate_subscription, calculate_queue_position
from flask import Blueprint, jsonify, request
from flask import Blueprint, jsonify

users_bp = Blueprint('api', __name__)


@users_bp.route('agent-details', methods=['GET'])
def agent_details():
    return jsonify(*fetch_data_from_table('agent_details'))


@users_bp.route('agent-metrics', methods=['GET'])
def agent_metrics():
    return jsonify(*fetch_data_from_table('agent_metrics'))


@users_bp.route('agent-queue', methods=['GET'])
def agent_queue():
    return jsonify(*fetch_data_from_table('agent_queue'))


@users_bp.route('agent-statuses', methods=['GET'])
def agent_statuses():
    return jsonify(*fetch_data_from_table('agent_statuses'))


@users_bp.route('ghl-token', methods=['GET'])
def ghl_token():
    return jsonify(*fetch_data_from_table('ghl_token'))


@users_bp.route('opener_statuses', methods=['GET'])
def opener_statuses():
    return jsonify(*fetch_data_from_table('opener_statuses'))


@users_bp.route('profiles', methods=['GET'])
def profiles():
    return jsonify(*fetch_data_from_table('profiles'))


@users_bp.route('transfers', methods=['GET'])
def transfers():
    return jsonify(*fetch_data_from_table('transfers'))


# Update Agent Status
@users_bp.route('update-agent-status', methods=['POST'])
def update_agent_status():
    agent_id = request.json.get('agent_id')
    status = request.json.get('status')

    # Check if agent is suspended
    suspended = validate_subscription(agent_id)
    if suspended:
        return jsonify({"message": "Agent is suspended. Please contact support."}), 403

    if status not in ['ready', 'break', 'offline', 'taking_transfer']:
        return jsonify({"message": "Invalid status provided."}), 400

    # Real-time response handling
    response = handle_status_change(agent_id, status)
    if response['status'] == 'error':
        return jsonify({"message": response['message']}), 400

    return jsonify({"message": "Agent status updated successfully."}), 200


# Get Real-time Queue Position
@users_bp.route('get-queue-position', methods=['GET'])
def get_queue_position():
    agent_id = request.args.get('agent_id')

    if not agent_id:
        return jsonify({"message": "Agent ID is required."}), 400

    queue_position = calculate_queue_position(agent_id)
    if queue_position is None:
        return jsonify({"message": "Agent not in queue."}), 404

    return jsonify({"message": "OK", "queue_position": queue_position}), 200


# Update Opener Status
@users_bp.route('update-opener-status', methods=['POST'])
def update_opener_status():
    opener_id = request.json.get('opener_id')
    status = request.json.get('status')

    if status not in ['online', 'offline']:
        return jsonify({"message": "Invalid status provided."}), 400

    # Update Opener status in the system
    response = supabase.table('opener_statuses').upsert({
        'opener_id': opener_id,
        'status': status,
        'updated_at': datetime.now()
    }).execute()

    if hasattr(response, 'error') and response.error:
        return jsonify({"message": "Error updating opener status.", "error": str(response.error)}), 500

    # Trigger status change for real-time response
    get_real_time_response(opener_id, status)

    return jsonify({"message": "Opener status updated successfully."}), 200


# Create Transfer Record
@users_bp.route('create-transfer', methods=['POST'])
def create_transfer():
    agent_id = request.json.get('agent_id')
    recorded_by = request.json.get('recorded_by')
    notes = request.json.get('notes')

    # Ensure the agent and opener are active
    agent_status_response = supabase.table('agent_statuses').select(
        'status').eq('agent_id', agent_id).execute()
    if agent_status_response['data'][0]['status'] != 'ready':
        return jsonify({"message": "Agent is not available for transfer."}), 400

    transfer_data = {
        'agent_id': agent_id,
        'recorded_by': recorded_by,
        'notes': notes,
        'created_at': datetime.now()
    }

    response = supabase.table('transfers').insert(transfer_data).execute()

    if hasattr(response, 'error') and response.error:
        return jsonify({"message": "Error creating transfer.", "error": str(response.error)}), 500

    return jsonify({"message": "Transfer created successfully."}), 200


# Subscription Management API
@users_bp.route('suspend-agent', methods=['POST'])
def suspend_agent():
    agent_id = request.json.get('agent_id')

    # Validate if the agent exists and has an active subscription
    suspension_response = supabase.table('profiles').select(
        'is_suspended').eq('id', agent_id).execute()
    if not suspension_response['data']:
        return jsonify({"message": "Agent not found."}), 404

    # Suspend Agent
    response = supabase.table('profiles').update(
        {'is_suspended': True}).eq('id', agent_id).execute()

    if hasattr(response, 'error') and response.error:
        return jsonify({"message": "Error suspending agent.", "error": str(response.error)}), 500

    return jsonify({"message": "Agent suspended successfully."}), 200


# Real-Time Status Updates
@users_bp.route('real-time-status-update', methods=['POST'])
def real_time_status_update():
    agent_id = request.json.get('agent_id')
    new_status = request.json.get('new_status')

    if not agent_id or not new_status:
        return jsonify({"message": "Agent ID and new status are required."}), 400

    # Check if status is valid
    valid_statuses = ['ready', 'break', 'offline', 'taking_transfer']
    if new_status not in valid_statuses:
        return jsonify({"message": "Invalid status provided."}), 400

    # Real-time status change trigger
    response = get_real_time_response(agent_id, new_status)
    if response['status'] == 'error':
        return jsonify({"message": "Error during real-time status update."}), 500

    return jsonify({"message": "Real-time status update successful."}), 200
