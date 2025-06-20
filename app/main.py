from fastapi import FastAPI
from app.routes import auth, email, user, validator
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="True Mail API",
    description="Email verification and management API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to True Mail API"} 

app.include_router(auth.router, prefix="/auth", tags=["Auth Management"])
app.include_router(email.router, tags=["Home Email"])
app.include_router(user.router, prefix="/user", tags=["User Management"])
app.include_router(validator.router, prefix="/validation", tags=["Validator Function"])
