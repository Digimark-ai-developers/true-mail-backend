from contextlib import asynccontextmanager
from fastapi import FastAPI, Request,Form
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, subscription_stripe, user, email
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from app.utils import validator
import jinja2
from app.utils.mail_utils import check_email_reachability, validate_email_syntax, get_mx_record, verify_smtp_server, load_disposable_domains

# from app.middlewares.auth_middleware import AuthMiddleware
from app.database.db_config import create_database  # Import create_database function
from app.routes import auth, credit, email, user
from app.routes.email_verification import router


app = FastAPI()

disposable_domains = load_disposable_domains()


email_syntax = validate_email_syntax



templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})



@app.post("/realtime-validator", response_class=HTMLResponse)
async def indexs_post(
    request: Request,
    email: str = Form(...),
    sender_email: str = Form('test@example.com')
):
    result = None
    if email:
        is_valid, message, dm_info = check_email_reachability(email, sender_email, disposable_domains)
        result = {
            'email': email,
            #'syntax': email_syntax,
            'status': 'Valid' if is_valid else 'Invalid',
            'message': message,
            'dm_info': dm_info  # Pass WHOIS info to template
        }
        print("WHOIS INFO:", dm_info)

    else:
        # Flash-like behavior would require session middleware or client-side handling
        pass
    return templates.TemplateResponse("index.html", {"request": request, "result": result})


@app.post("/realtime-validator-email")
async def index_post(
    email: str = Form(...),
    sender_email: str = Form('test@example.com')
):
    if not email:
        return JSONResponse(status_code=400, content={"error": "Email is required"})

    try:
        is_valid, message, dm_info = check_email_reachability(email, sender_email, disposable_domains)

        result = {
            'email': email,
            'is_valid': is_valid,
            'status': 'valid' if is_valid else 'invalid',
            'message': message,
            'whois': dm_info  # May contain datetime objects
        }

        # Automatically convert datetime and other non-serializable types
        serialized_result = jsonable_encoder(result)

        return JSONResponse(content=serialized_result)

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to execute during application startup
    print("Application is starting up...")
    create_database()  # Call the function to create the database and tables

    yield  # Application is running here
    # Code to execute during application shutdown
    print("Application is shutting down...")




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
app.include_router(subscription_stripe.router)
app.include_router(email.router)
app.include_router(credit.router)


# Health Check Route
@app.get("/", tags=["Health Check"])
def health_check():
    return {"status": "ok", "message": "API is running successfully"}


