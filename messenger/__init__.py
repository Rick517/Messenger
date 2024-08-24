from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from google_auth_oauthlib.flow import Flow
import os
from flask_mailman import Mail
from flask_socketio import SocketIO
from datetime import timedelta
from redis import Redis
from pymongo import MongoClient
from dotenv import load_dotenv


# For using .env variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messenger.sqlite3'
db = SQLAlchemy(app)

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" # to allow Http traffic for local dev (instead of https)
google_client_secrets = os.getenv('GOOGLE_CLIENT_SECRETS', '/etc/secrets/client_secret.json')
print(os.getenv('GOOGLE_CLIENT_SECRETS'))


scopes = ["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"]
flow = Flow.from_client_secrets_file(client_secrets_file=google_client_secrets, scopes=scopes, redirect_uri='https://messenger-s3fg.onrender.com/auth/google/callback')

mail = Mail()
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'sky.above.skyyy@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('GMAIL_SECRET_SKY')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail.init_app(app)

socketio = SocketIO(app)

REFRESH_TOKEN_EXPIRATION = timedelta(days=30)
ACCESS_TOKEN_EXPIRATION = timedelta(minutes=15)

# Prerequisite: initialize redis-server via ubuntu (for development).
redis = Redis(host=os.getenv('REDIS_RENDER_URI'), port=6379, decode_responses=True)

# There is always one chat for all users.
# Every deletion, editing and adding touches every user.
# I set message and author: user_id in group_chats. On get history and check and add a css-class=mine when equaled.
# To implement delete, edit with only by yourself a set with (user_id, message (by author)) should be created and checked every time.
mongo_cluster = MongoClient(os.getenv('MONGO_PRODUCTION_CLUSTER_URI'))
mongo_db = mongo_cluster['messenger']
group_chats = mongo_db['groups_history']
contact_chats = mongo_db['contacts_history']

# NOTE utmost important
from messenger import routes
