import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate("app/credentials.json")
firebase_app = firebase_admin.initialize_app(cred)
