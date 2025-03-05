from app.supabase_client import supabase
from datetime import datetime


def fetch_data_from_table(table_name):
    try:
        response = supabase.table(table_name).select('*').execute()
        if hasattr(response, 'error') and response.error:
            return {"message": "Error fetching data", "error": str(response.error)}, 500
        if hasattr(response, 'data') and response.data:
            return {"message": "OK", "data": response.data}, 200
        return {"message": "No data found", "error": "Data is empty"}, 404
    except Exception as e:
        return {"message": "Internal server error", "error": str(e)}, 500


def get_real_time_response(agent_id, status):
    try:
        # This would handle the logic to send a real-time response to the system or frontend.
        # For instance, pushing updates via a websocket or through a notification system.

        # Example implementation with a mock response
        return {"status": "success", "message": f"Agent {agent_id} status updated to {status}"}

    except Exception as e:
        return {"status": "error", "message": f"Error in real-time update: {str(e)}"}


def handle_status_change(agent_id, status):
    try:
        response = supabase.table('agent_statuses').upsert({
            'agent_id': agent_id,
            'status': status,
            'updated_at': datetime.now()
        }).execute()

        if hasattr(response, 'error') and response.error:
            return {"status": "error", "message": str(response.error)}

        if status == 'taking_transfer':
            pass

        real_time_response = get_real_time_response(agent_id, status)
        return {"status": "success", "message": "Status updated successfully", "real_time_response": real_time_response}

    except Exception as e:
        return {"status": "error", "message": f"Error updating status: {str(e)}"}


def validate_subscription(agent_id):
    try:
        response = supabase.table('profiles').select(
            'is_suspended').eq('id', agent_id).execute()

        if response and response['data']:
            return response['data'][0]['is_suspended']
        return False
    except Exception as e:
        return True


def calculate_queue_position(agent_id):
    try:
        response = supabase.table('agent_queue').select(
            'agent_id', 'position').order('position').execute()

        if response and response['data']:
            for item in response['data']:
                if item['agent_id'] == agent_id:
                    return item['position']
        return None
    except Exception as e:
        return None


