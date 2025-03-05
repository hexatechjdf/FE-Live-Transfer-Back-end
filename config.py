
import os
from dotenv import load_dotenv

load_dotenv()  

class Config:
    # Default for development
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
