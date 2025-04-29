import firebase_admin
from firebase_admin import credentials

import os

# Initialize Firebase Admin SDK#
if not firebase_admin._apps:

    cred = credentials.Certificate("./app/truemail-5a597-firebase-adminsdk-fbsvc-529130fcbb.json")  # downloaded earlier
    firebase_admin.initialize_app(cred)
