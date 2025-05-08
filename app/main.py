from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, user, email
# from app.middlewares.auth_middleware import AuthMiddleware
from app.database.db_config import create_database  # Import create_database function


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to execute during application startup
    print("Application is starting up...")
    create_database()  # Call the function to create the database and tables

    yield  # Application is running here
    # Code to execute during application shutdown
    print("Application is shutting down...")

app = FastAPI(lifespan=lifespan)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with allowed origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# app.add_middleware(AuthMiddleware)

# Include route modules
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(email.router)


# Health Check Route
@app.get("/", tags=["Health Check"])
def health_check():
    return {"status": "ok", "message": "API is running successfully"}
