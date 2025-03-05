
# from flask import Flask
# from flask_socketio import SocketIO

# from .supabase_client import supabase

# from app.routes.views import users_bp
# from app.routes.auth import auth_bp
# from app.routes.agent import agent_bp
# from app.routes.opener import opener_bp
# from app.routes.admin import admin_bp
# from app.routes.webhook import webhook_bp
# from flask_cors import CORS

# from config import Config

# socketio = SocketIO(cors_allowed_origins="*")


# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     CORS(app)
#     socketio.init_app(app)

#     # app.register_blueprint(users_bp, url_prefix='/api')

#     # Register blueprints
#     app.register_blueprint(auth_bp, url_prefix="/auth")
#     app.register_blueprint(agent_bp, url_prefix="/agent")
#     app.register_blueprint(opener_bp, url_prefix="/opener")
#     app.register_blueprint(admin_bp, url_prefix="/admin")
#     app.register_blueprint(webhook_bp, url_prefix="/webhook")

#     def emit_status_update():
#         agents = supabase.table("profiles").select(
#             "*, agent_statuses(status), agent_queue(position)").eq("role", "agent").execute().data
#         openers = supabase.table("profiles").select(
#             "*, opener_statuses(status)").eq("role", "opener").execute().data
#         socketio.emit("status_update", {"agents": agents, "openers": openers})

#     app.emit_status_update = emit_status_update

#     return {
#         "app": app,
#         "socketio": socketio,
#     }
