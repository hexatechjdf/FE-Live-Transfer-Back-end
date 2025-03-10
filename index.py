# from app import create_app


# app_instance = create_app()
# app = app_instance["app"]
# socketio = app_instance["socketio"]

# if __name__ == '__main__':
#     socketio.run(app, debug=True, host="0.0.0.0", port=5000)

import base64
from postgrest.exceptions import APIError
from flask import request, jsonify
import json
import re
from flask import Flask, request, jsonify
from functools import wraps
from supabase import create_client, Client
import os
from flask_cors import CORS
from flask import redirect
import urllib
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
# Flask app setup
app = Flask(__name__)
CORS(app)

# Supabase client initialization
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_API_KEY')


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Authentication decorator using Supabase


def decode_jwt(token):
    parts = token.split('.')

    if len(parts) != 3:
        raise ValueError("Invalid JWT token")

    # print(parts[1])
    payload = json.loads(base64.b64decode(parts[1]+'==')) or None

    return payload


# Example Usage:
def get_user_by_token(auth_token):
    try:
        response = supabase.auth.get_user(auth_token)
        return response.user  # Returns the user data
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None


def require_auth(allowed_roles=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            token = request.headers.get("Authorization")
            if not token or not token.startswith("Bearer "):
                return jsonify({"error": "Token is missing"}), 403
            token = token.split("Bearer ")[-1]
            user = decode_jwt(token)

            if not user:
                return jsonify({"error": "Forbidden: Invalid token"}), 403

            # user_role = user.get("user_role", None)
            # request.user_role = user_role

            # if allowed_roles and user_role not in allowed_roles:
            #     return jsonify({"error": f"Forbidden: Access restricted to {', '.join(allowed_roles)} only - Relogin if role is correct"}), 403
            authUser = get_user_by_token(token)
            if not authUser:
                return jsonify({"error": "unauthorized"}), 401

            request.auth_user = authUser

            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_authentication(allowed_roles=None):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get(
                'Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'error': 'Unauthorized'}), 401
            try:
                user_response = supabase.auth.api.get_user(token)
                if user_response is None or 'user' not in user_response:
                    return jsonify({'error': 'Invalid token'}), 401
                user = user_response['user']
                request.user_id = user['id']
                request.user_role = user['user_metadata'].get('role')
                if not request.user_role:
                    return jsonify({'error': 'Role not found in user metadata'}), 403
                if allowed_roles and request.user_role not in allowed_roles:
                    return jsonify({'error': 'Forbidden'}), 403
            except Exception as e:
                return jsonify({'error': str(e)}), 401
            return f(*args, **kwargs)
        return decorated
    return decorator

# User Management Endpoints


@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    try:
        credentials = {
            "email": email,
            "password": password,
        }
        response = supabase.auth.sign_in_with_password(credentials)

        dumped_dictionary = response.model_dump()

        profile_response = supabase.table("profiles").select(
            "*").eq("email", email)
        profile = profile_response.single().execute().data

        session = dumped_dictionary["session"]

        keys = {
            'access_token': session["access_token"],
            'refresh_token': session["refresh_token"]
        }

        if response:
            return jsonify({
                'message': 'Sign-in successful',
                'user': dumped_dictionary["user"],
                "profile": profile,
                'session': keys
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/refresh', methods=['POST'])
def refresh():
    data = request.get_json()
    refresh_token = data.get('refresh_token')

    if not refresh_token:
        return jsonify({'error': 'Refresh token is required'}), 400

    try:
        response = supabase.auth.refresh_session(refresh_token)
        dumped_dictionary = response.model_dump()

        session = dumped_dictionary["session"]
        keys = {
            'access_token': session["access_token"],
            'refresh_token': session["refresh_token"]
        }

        return jsonify({
            'message': 'Token refreshed successfully',
            'session': keys
        }), 200
    except Exception as e:
        return jsonify({'error': 'Invalid refresh token'}), 401


@app.route('/users', methods=['GET'])
# @require_auth(['super_admin', 'opener'])
def list_users():
    try:

        role = request.args.get('role')
        # if request.user_role == 'opener':
        #     role = 'agent'
        response = supabase.table('profiles').select(
            "*").neq('role', 'super_admin')
        if role:
            response = response.eq('role', role)
        data = response.execute().data
        return jsonify(data), 200
    except Exception as e:
        print(e)
        return jsonify({'error': "Failed to list users"}), 500


@app.route('/users', methods=['POST'])
# @require_auth(['super_admin'])
def create_user():
    try:
        data = request.get_json()
        email = data.get('email')
        full_name = data.get('full_name')
        phone = data.get('phone')
        role = data.get('role')
        fe_plan = data.get('fe_plan')
        crm_plan = data.get('crm_plan')
        licensed_states = data.get('licensed_states')
        password = data.get('password')

        if not all([email, role]):
            return jsonify({'error': 'Email and role are required'}), 400

        users_response = supabase.auth.admin.list_users()

        existing_user = next(
            (u for u in users_response if u.email == email), None)
        if existing_user:
            return jsonify({'error': 'User already exists'}), 409

        user_response = supabase.auth.admin.create_user({
            'email': email,
            'password': password,
            'user_metadata': {'role': role, 'full_name': full_name, 'phone': phone},
            'email_confirm': True
        })

        user_id = user_response.user.id

        new_profile = {
            # 'id': user_id,
            'email': email,
            'role': role,
            'full_name': full_name,
            'fe_plan': fe_plan if role == 'agent' else None,
            'crm_plan': crm_plan if role == 'agent' else None,
            'licensed_states': licensed_states if role == 'agent' else None,
            'phone': phone,
            'is_suspended': False
        }

        profile_response = supabase.table('profiles').update(
            new_profile).eq('id', user_id).execute()

        return jsonify({'id': user_id, 'message': 'User created'}), 201
    except Exception as e:
        return jsonify({'message': "Failed to create user"}), 500


@app.route('/users/<user_id>', methods=['GET'])
# @require_auth(['super_admin', 'agent', 'opener'])
def get_user(user_id):
    # if request.user_id != user_id and request.user_role != 'super_admin':
    #     return jsonify({'error': 'Forbidden'}), 403
    response = supabase.table('profiles').select(
        'id, email, role, full_name, subscription_status').eq('id', user_id).execute()
    if response.data:
        return jsonify(response.data[0]), 200
    else:
        return jsonify({'error': 'User not found'}), 404


@app.route('/users/<user_id>', methods=['PUT'])
# @require_auth(['super_admin', 'agent', 'opener'])
def update_user(user_id):
    if request.user_id != user_id and request.user_role != 'super_admin':
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    update_data = {}
    if 'email' in data:
        update_data['email'] = data['email']
    if 'full_name' in data:
        update_data['full_name'] = data['full_name']
    if 'plan_id' in data:
        update_data['plan_id'] = data['plan_id']
    if 'role' in data and request.user_role == 'super_admin':
        update_data['role'] = data['role']
        # Update role in auth.users metadata
        supabase.auth.admin.update_user(
            user_id, {'user_metadata': {'role': data['role']}})
    if update_data:
        response = supabase.table('profiles').update(
            update_data).eq('id', user_id).execute()
        if response.data:
            return jsonify({'message': 'User updated'}), 200
        else:
            return jsonify({'error': 'Failed to update user'}), 500
    else:
        return jsonify({'message': 'No updates provided'}), 200


@app.route('/users/<user_id>', methods=['DELETE'])
# @require_auth(['super_admin'])
def delete_user(user_id):
    supabase.table('profiles').delete().eq('id', user_id).execute()
    supabase.auth.admin.delete_user(user_id)
    return jsonify({'message': 'User deleted'}), 204

# Subscription Management


@app.route('/users/<user_id>/subscription', methods=['PUT'])
@require_auth(['super_admin'])
def update_subscription(user_id):
    data = request.get_json()
    status = data.get('subscription_status')
    if status not in ['active', 'paused', 'cancelled', 'suspended']:
        return jsonify({'error': 'Invalid subscription status'}), 400
    response = supabase.table('profiles').update(
        {'subscription_status': status}).eq('id', user_id).execute()
    if response.data:
        return jsonify({'message': 'Subscription updated'}), 200
    else:
        return jsonify({'error': 'Failed to update subscription'}), 500

# Agent Status Updates


@app.route('/me/status', methods=['PUT'])
# @require_auth(['agent'])
def update_agent_status():
    data = request.get_json()
    new_status = data.get('status')
    user_id = request.user_id
    profile = supabase.table('profiles').select(
        'subscription_status').eq('id', user_id).execute().data[0]
    if profile['subscription_status'] in ['suspended', 'cancelled']:
        return jsonify({'error': 'Account suspended or cancelled'}), 403
    if new_status == 'ready':
        opener_count = supabase.table('opener_statuses').select(
            'count').eq('status', 'online').execute().data[0]['count']
        if opener_count == 0:
            return jsonify({'error': 'No openers available'}), 400
        queue_entry = supabase.table('agent_queue').select(
            'id').eq('agent_id', user_id).execute().data
        if not queue_entry:
            max_position = supabase.table('agent_queue').select(
                'position').order('position', desc=True).limit(1).execute().data
            new_position = (
                max_position[0]['position'] + 1) if max_position else 1
            supabase.table('agent_queue').insert(
                {'agent_id': user_id, 'position': new_position}).execute()
    response = supabase.table('agent_statuses').upsert(
        {'agent_id': user_id, 'status': new_status}).execute()
    if response.data:
        return jsonify({'message': 'Status updated'}), 200
    else:
        return jsonify({'error': 'Failed to update status'}), 500


@app.route('/me/queue', methods=['GET'])
# @require_auth(['agent', 'opener'])
def get_queue_position():
    user_id = request.user_id
    queue_entry = supabase.table('agent_queue').select(
        'position').eq('agent_id', user_id).execute().data
    position = queue_entry[0]['position'] if queue_entry else None
    return jsonify({'position': position}), 200

# Opener Status Updates


@app.route('/me/status', methods=['PUT'])
# @require_auth(['opener', 'agent'])
def update_opener_status():
    data = request.get_json()
    new_status = data.get('status')
    if new_status not in ['online', 'offline']:
        return jsonify({'error': 'Invalid status'}), 400
    user_id = request.user_id
    response = supabase.table('opener_statuses').upsert(
        {'opener_id': user_id, 'status': new_status}).execute()
    if response.data:
        return jsonify({'message': 'Status updated'}), 200
    else:
        return jsonify({'error': 'Failed to update status'}), 500

# Transfer Recording


@app.route('/transfers', methods=['POST'])
# @require_auth(['opener'])
def record_transfer():
    data = request.get_json()
    agent_id = data.get('agent_id')
    notes = data.get('notes', '{}')

    # Fetch the most recent status record for the given agent
    agent_status = supabase.table('user_agent_status').select(
        'status'
    ).eq('agent_id', agent_id).order('created_at', desc=True).limit(1).execute().data

    if not agent_status or agent_status[0]['status'] != 'ready':
        return jsonify({'error': 'Agent not ready'}), 400

    transfer_data = {
        'agent_id': agent_id,
        'recorded_by': data.get('user_id', None),
        'notes': notes
    }

    response = supabase.table('transfers').insert(transfer_data).execute()

    if response.data:
        transfer_id = response.data[0]['id']
        supabase.table('user_agent_status').update(
            {'status': 'busy'}).eq('agent_id', agent_id).execute()
        supabase.table('agent_queue').delete().eq(
            'agent_id', agent_id).execute()
        return jsonify({'transfer_id': transfer_id, 'message': 'Transfer recorded'}), 201
    else:
        return jsonify({'error': 'Failed to record transfer'}), 500


# Webhook Integration (Example for GHL subscription updates)


@app.route('/webhooks/ghl/subscription', methods=['POST'])
def handle_ghl_webhook():
    data = request.get_json()
    user_id = data.get('user_id')
    new_status = data.get('subscription_status')
    if new_status not in ['active', 'paused', 'cancelled', 'suspended']:
        return jsonify({'error': 'Invalid status'}), 400
    response = supabase.table('profiles').update(
        {'subscription_status': new_status}).eq('id', user_id).execute()
    if response.data:
        return jsonify({'message': 'Subscription updated'}), 200
    else:
        return jsonify({'error': 'Failed to update subscription'}), 500


CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


@app.route("/connect")
def connect():
    GHL_AUTH_URL = os.getenv('GHL_AUTH_URL')
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    SCOPE = os.getenv('SCOPE')

    auth_url = f"{GHL_AUTH_URL}?client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&response_type=code&scope={urllib.parse.quote(SCOPE)}"
    return jsonify({"auth_url": auth_url})


@app.route("/callback")
def callback():
    auth_code = request.args.get("code")
    url = "https://services.leadconnectorhq.com/oauth/token"

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": auth_code,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    response = requests.post(url, data=payload, headers=headers)
    response_object = response.json()

    access_token = response_object["access_token"]
    refresh_token = response_object["refresh_token"]
    expires_in = response_object["expires_in"]
    if not auth_code:
        return "Authorization failed", 400
    rec_response = supabase.table('ghl_tokens').insert(
        {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        }
    ).execute()

    return redirect("http://localhost:5173")


@app.route('/callback/agent/create', methods=['POST'])
# @require_auth(['super_admin'])
def agent_create_or_update_callback():
    data = request.get_json()

    email = data.get('email').lower()  # Convert email to lowercase
    full_name = data.get('full_name', data.get('name', ''))
    role = "agent"
    customData = data.get('customData', {})
    authKey = customData.get('authKey', None)

    # if authKey != 'vtzlrx4xH0iuwT7sBvYPcgmkvPtTb3jtygxUCWdS7tHY9wPXJSJ7aKbyOjciY8xm':
    #   return jsonify({'error': 'Unauthorized'}), 401

    fe_plan = customData.get('fe_plan', None)
    crm_plan = customData.get('crm_plan', None)
    licensed_states = customData.get('licensed_states', None)
    if isinstance(licensed_states, str):
        licensed_states = [state.strip() for state in re.split(
            r",\s*", licensed_states) if state.strip()]
    elif not isinstance(licensed_states, list):
        licensed_states = []
    contactId = data.get("contact_id", "PaSsW0rd@33")
    password = customData.get('password', contactId+"$2#")
    phone = customData.get('phone', None)

    if not all([email, role]):
        return jsonify({'error': 'Email and role are required'}), 400

    existing_user = None
    try:
        existing_user = supabase.table('profiles').select(
            '*').eq('email', email).single().execute().data
    except APIError as e:
        pass

    isAgent = True
    new_profile = {
        'email': email,
        'role': role,
        'full_name': full_name,
    }
    if fe_plan is not None:
        new_profile['fe_plan'] = fe_plan
    if licensed_states is not None:
        new_profile['licensed_states'] = licensed_states
        if contactId is not None:
            new_profile['contact_id'] = contactId
    if crm_plan is not None:
        new_profile['crm_plan'] = fe_plan
    if phone is not None:
        new_profile['phone'] = phone

    if existing_user:
        user_id = existing_user["id"]

        supabase.table('profiles').update(
            new_profile).eq('id', user_id).execute()

        return jsonify({'id': user_id, 'message': 'User profile updated'}), 200

    user_response = supabase.auth.admin.create_user({
        'email': email,
        'password': password,
        'user_metadata': {'role': role, 'full_name': full_name, 'phone': None, 'fe_plan': None, 'crm_plan': None, 'licensed_states': None},
        'email_confirm': True
    })

    user_id = user_response.user.id

    data = supabase.table('profiles').update(
        new_profile).eq('id', user_id).execute()
    return jsonify({'id': user_id, 'message': 'User created'}), 201


@app.route('/callback/agent/subscription', methods=['POST'])
# @require_auth(['super_admin'])
def agent_subscription_update_callback():
    data = request.get_json()

    email = data.get('email').lower()  # Convert email to lowercase
    role = "agent"
    customData = data.get('customData', {})
    status = customData.get('status', "failed")

    if not all([email, role]):
        return jsonify({'error': 'Email and role are required'}), 400

    existing_user = None
    try:
        existing_user = supabase.table('profiles').select(
            '*').eq('email', email).single().execute().data
    except APIError as e:
        pass

    # If user exists, update their profile
    if existing_user:
        user_id = existing_user["id"]
        new_profile = {
            'email': email,
            'is_suspended': status == "failed"
        }
        profile_response = supabase.table('profiles').update(
            new_profile).eq('id', user_id).execute()

        return jsonify({'id': user_id, 'message': 'Subscription updated'}), 200

    return jsonify({'error': 'Failed to update profile'}), 500


def format_phone_number(phone: str) -> str:
    return phone  # Modify this as needed for proper phone number formatting


settings = supabase.table('settings').select(
    'main_location_id, private_integration_key'
).order('created_at', desc=True).limit(1).execute().data


@app.route('/search_contacts', methods=['GET'])
# @require_auth(['opener'])
def search_ghl_contacts():

    GHL_API_URL = os.environ.get('GHL_API_URL')

    if not settings:
        return jsonify({'error': 'No Credentials Provided'}), 404

    private_integration_key = settings[0]['private_integration_key']
    location_id = settings[0]['main_location_id']
    query = request.args.get('query')

    if not private_integration_key or not location_id or not query:
        return jsonify({'error': 'Private integration key, location ID, and query are required'}), 400

    try:
        headers = {
            'Authorization': f'Bearer {private_integration_key}',
            'Content-Type': 'application/json',
            'Version': '2021-07-28'
        }

        body = {
            'locationId': location_id,
            'query': query,
            'pageLimit': 100,
            'filters': [
                {
                    'field': 'tags',
                    'operator': 'contains',
                    'value': 'final expense veteran lead'
                }
            ]
        }

        response = requests.post(
            f'{GHL_API_URL}/contacts/search', headers=headers, data=json.dumps(body))

        if response.status_code != 200:
            error = response.json()
            return jsonify({'error': error.get('message', 'Failed to search contacts')}), 500

        data = response.json()

        contacts = [
            {
                'id': contact.get('id'),
                'firstName': contact.get('firstNameLowerCase', contact.get('firstName', '').lower()),
                'lastName':  contact.get('lastNameLowerCase', contact.get('lastName', '').lower()),

                'email': contact.get('email'),
                'phone': format_phone_number(contact.get('phone', '')) if contact.get('phone') else None
            }
            for contact in data.get('contacts', [])
        ]

        return jsonify({'contacts': contacts})

    except Exception as error:
        return jsonify({'error': f'Error searching GHL contacts: {str(error)}'}), 500


@app.route('/update_contact_custom_fields', methods=['PUT'])
# @require_auth(['opener'])
def update_contact_custom_fields():
    try:
        GHL_API_URL = os.environ.get('GHL_API_URL')

        data = request.get_json()
        contact = data.get('contact')

        agent_name = data.get('agentName')
        opener_profile = data.get('openerProfile')

        if not contact or not agent_name or not opener_profile:
            return jsonify({'error': 'contactId, agentName, and openerProfile are required'}), 400
        contact_id = contact.get('id')
        custom_fields = [
            {
                'key': 'agent_name',
                'field_value': agent_name
            },
            {
                'key': 'opener',
                'field_value': opener_profile.get('full_name')
            }
        ]

        request_body = {
            'customFields': custom_fields,
        }

        if not settings:
            return jsonify({'error': 'No Credentials Provided'}), 404

        header = {
            'Authorization': f'Bearer {settings[0]["private_integration_key"]}',
            'Content-Type': 'application/json',
            'Version': '2021-07-28'
        }

        response = requests.put(
            f'{GHL_API_URL}/contacts/{contact_id}',
            headers=header,
            data=json.dumps(request_body)
        )

        #  addding tags.
        payload = {"tags": ['COMPLETE_TRANSFER']}
        rsp = requests.post(f'{GHL_API_URL}/contacts/{contact_id}/tags',
                            json=payload, headers=header)

        if response.status_code == 200:

            return jsonify({'message': 'Contact updated successfully'}), 200
        else:
            error = response.json()
            return jsonify({'error': error.get('message', 'Failed to update contact')}), 500

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=30000)
