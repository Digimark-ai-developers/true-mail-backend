# # app.py - FastAPI version

# import os
# import threading
# import time
# from concurrent.futures import ThreadPoolExecutor, as_completed

# # import jinja2
# import pandas as pd
# from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
# from fastapi.responses import HTMLResponse, StreamingResponse  # RedirectResponse,

# # from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates

# from app.utils.mail_utils import (
#     check_email_reachability,
#     # get_mx_record,
#     # load_disposable_domains,
#     validate_email_syntax,
#     # verify_smtp_server,
# )

# # from pathlib import Path


# app = FastAPI()
# templates = Jinja2Templates(directory="templates")

# UPLOAD_FOLDER = "uploads"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# # Load disposable domains once at startup


# # Progress tracking
# progress = []
# progress_lock = threading.Lock()


# @app.get("/batch", response_class=HTMLResponse)
# async def batch_get(request: Request):
#     return templates.TemplateResponse("batch.html", {"request": request, "columns": [], "selected_column": None})


# @app.post("/batch", response_class=HTMLResponse)
# async def batch_post(
#     request: Request,
#     file: UploadFile = File(...),
#     email_column: str = Form(...),
#     sender_email: str = Form("test@example.com"),
# ):
#     global progress
#     progress = []

#     if not file.filename.endswith(".csv"):
#         # Handle error
#         return templates.TemplateResponse("batch.html", {"request": request, "error": "Invalid file format"})

#     filename = file.filename
#     filepath = os.path.join(UPLOAD_FOLDER, filename)
#     with open(filepath, "wb") as f:
#         f.write(await file.read())

#     df = pd.read_csv(filepath)
#     columns = df.columns.tolist()

#     if email_column not in df.columns:
#         return templates.TemplateResponse(
#             "batch.html",
#             {
#                 "request": request,
#                 "columns": columns,
#                 "selected_column": email_column,
#                 "error": "Selected column not found.",
#             },
#         )

#     emails = df[email_column].dropna().unique()
#     total_emails = len(emails)
#     email_result_map = {}

#     def validate_email(i, email):
#         if not validate_email_syntax(str(email)):
#             result = (email, "Invalid", "Invalid syntax")
#         else:
#             # is_valid, message = check_email_reachability(str(email), sender_email)
#             # result = (email, "Valid" if is_valid else "Invalid", message)

#         with progress_lock:
#             progress.append({"processed": len(progress) + 1, "total": total_emails})
#         return result

#     with ThreadPoolExecutor(max_workers=500) as executor:
#         futures = {executor.submit(validate_email, i, str(email)): email for i, email in enumerate(emails)}
#         for future in as_completed(futures):
#             email, status, message = future.result()
#             email_result_map[email] = {"Status": status, "Validation_Message": message}

#     df["Status"] = df[email_column].map(lambda x: email_result_map.get(str(x), {}).get("Status", "Unknown"))
#     df["Validation_Message"] = df[email_column].map(
#         lambda x: email_result_map.get(str(x), {}).get("Validation_Message", "")
#     )

#     valid_df = df[df["Status"] == "Valid"]
#     invalid_df = df[df["Status"] == "Invalid"]

#     timestamp = time.strftime("%Y%m%d_%H%M%S")
#     valid_path = os.path.join(UPLOAD_FOLDER, f"valid_emails_{timestamp}.csv")
#     invalid_path = os.path.join(UPLOAD_FOLDER, f"invalid_emails_{timestamp}.csv")
#     valid_df.to_csv(valid_path, index=False)
#     invalid_df.to_csv(invalid_path, index=False)

#     return templates.TemplateResponse(
#         "downloads.html",
#         {
#             "request": request,
#             "valid_file": f"valid_emails_{timestamp}.csv",
#             "invalid_file": f"invalid_emails_{timestamp}.csv",
#         },
#     )


# @app.get("/batch-progress")
# async def batch_progress():
#     return {"progress": progress}


# @app.get("/download/{filename}")
# async def download_file(filename: str):
#     file_path = os.path.join(UPLOAD_FOLDER, filename)
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="File not found")
#     return StreamingResponse(
#         open(file_path, "rb"),
#         media_type="text/csv",
#         headers={"Content-Disposition": f"attachment; filename={filename}"},
#     )
