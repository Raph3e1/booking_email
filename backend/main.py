import re
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback
from routers.settings import router as settings_router
from routers.emails import router as emails_router
from routers.excel_import import router as excel_router
from services.scheduler import scheduler
from services.email_fetcher import action_fetch_data
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from services.currency_service import update_exchange_rate

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="template/static"), name="static")
templates = Jinja2Templates(directory="template")


class EmailCredentials(BaseModel):
    email: str
    password: str


@app.post("/api/fetch-emails")
async def fetch_emails(credentials: EmailCredentials):
    try:
        action_fetch_data(credentials.email, credentials.password)
        return {"bookings": []}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
def main(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/emails", response_class=HTMLResponse)
def emails(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/excel-import", response_class=HTMLResponse)
def excel_import(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Add routers
app.include_router(settings_router)
app.include_router(emails_router)
app.include_router(excel_router)


@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on startup"""
    update_exchange_rate()

    scheduler.start_all_jobs(action_fetch_data)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler on application shutdown"""
    scheduler.scheduler.shutdown()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
