from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List
import json
import os

router = APIRouter(prefix="/api/emails", tags=["emails"])

# File to store email list
EMAILS_FILE = "data/emails.json"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Initialize emails file if it doesn't exist
if not os.path.exists(EMAILS_FILE):
    with open(EMAILS_FILE, "w") as f:
        json.dump([], f)

class EmailItem(BaseModel):
    id: int
    email: str

class EmailCreate(BaseModel):
    email: EmailStr

def get_emails():
    with open(EMAILS_FILE, "r") as f:
        return json.load(f)

def save_emails(emails):
    with open(EMAILS_FILE, "w") as f:
        json.dump(emails, f)

@router.get("/", response_model=List[EmailItem])
async def get_email_list():
    return get_emails()

@router.post("/", response_model=EmailItem)
async def add_email(email: EmailCreate):
    emails = get_emails()
    new_id = max([e.get("id", 0) for e in emails], default=0) + 1
    new_email = {"id": new_id, "email": email.email}
    emails.append(new_email)
    save_emails(emails)
    return new_email

@router.put("/{email_id}", response_model=EmailItem)
async def update_email(email_id: int, email: EmailCreate):
    emails = get_emails()
    for i, e in enumerate(emails):
        if e["id"] == email_id:
            emails[i] = {"id": email_id, "email": email.email}
            save_emails(emails)
            return emails[i]
    raise HTTPException(status_code=404, detail="Email not found")

@router.delete("/{email_id}")
async def delete_email(email_id: int):
    emails = get_emails()
    emails = [e for e in emails if e["id"] != email_id]
    save_emails(emails)
    return {"message": "Email deleted successfully"} 