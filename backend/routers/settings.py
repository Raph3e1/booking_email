import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime
from models.settings import SettingsManager, EmailConfig
from services.scheduler import scheduler
from services.email_fetcher import action_fetch_data

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"]
)

settings_manager = SettingsManager()


class EmailConfigCreate(BaseModel):
    email: EmailStr
    password: str
    fetchInterval: int


class EmailConfigUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    fetchInterval: Optional[int] = None


class EmailConfigResponse(BaseModel):
    id: int
    email: str
    password: str
    fetchInterval: int
    created_at: datetime
    updated_at: datetime


class NextRunInfo(BaseModel):
    next_run: str
    time_until: str


class EmailConfigStatus(BaseModel):
    id: int
    email: str
    fetch_interval: int
    next_run: Optional[NextRunInfo] = None

    class Config:
        from_attributes = True


class GlobalSettings(BaseModel):
    googleSheetUrl: str
    sheetName: str



class GlobalSettingsResponse(BaseModel):
    googleSheetUrl: str
    sheetName: str


@router.get("/email-configs", response_model=List[EmailConfigResponse])
async def get_email_configs():
    """Get all email configurations"""
    return settings_manager.get_all_configs()


@router.get("/email-configs/{config_id}", response_model=EmailConfigResponse)
async def get_email_config(config_id: int):
    """Get a specific email configuration by ID"""
    config = settings_manager.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Email configuration not found")
    return config


@router.post("/email-configs", response_model=EmailConfigResponse)
async def create_email_config(config: EmailConfigCreate):
    """Create a new email configuration"""
    try:
        # Get all existing configs to determine the next ID
        existing_configs = settings_manager.get_all_configs()
        next_id = max([c.get("id", 0) for c in existing_configs], default=0) + 1

        new_config = EmailConfig(
            id=next_id,  # Set the ID before creating the config
            email=config.email,
            password=config.password,
            fetchInterval=config.fetchInterval
        )
        return settings_manager.create_config(new_config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/email-configs/{config_id}", response_model=EmailConfigResponse)
async def update_email_config(config_id: int, config: EmailConfigUpdate):
    """Update an existing email configuration"""
    existing_config = settings_manager.get_config(config_id)
    if not existing_config:
        raise HTTPException(status_code=404, detail="Email configuration not found")

    # Update only provided fields
    update_data = config.model_dump(exclude_unset=True)
    updated_config = settings_manager.update_config(config_id, {**existing_config, **update_data})

    if not updated_config:
        raise HTTPException(status_code=400, detail="Failed to update configuration")
    return updated_config


@router.delete("/email-configs/{config_id}")
async def delete_email_config(config_id: int):
    """Delete an email configuration"""
    if not settings_manager.get_config(config_id):
        raise HTTPException(status_code=404, detail="Email configuration not found")

    if settings_manager.delete_config(config_id):
        return {"message": "Email configuration deleted successfully"}
    raise HTTPException(status_code=400, detail="Failed to delete configuration")


@router.get("/email-configss/status", response_model=List[EmailConfigStatus])
async def get_email_configs_status():
    """Get status of all email configurations including next run time"""
    try:
        statuses = scheduler.get_all_jobs_status()
        # Convert the statuses to match the response model
        formatted_statuses = []
        for status in statuses:
            formatted_status = {
                "id": status.get("id"),
                "email": status.get("email"),
                "fetch_interval": status.get("fetch_interval"),
                "next_run": status.get("next_run")
            }
            formatted_statuses.append(formatted_status)
        return formatted_statuses
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email-configs/{config_id}/start")
async def start_email_fetch(config_id: int, action_fetch_data_func):
    """Start fetching emails for a specific configuration"""
    config = settings_manager.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Email configuration not found")
    
    scheduler.add_job(config, action_fetch_data_func)
    return {"message": f"Started fetching emails for {config['email']}"}


@router.post("/email-configs/{config_id}/stop")
async def stop_email_fetch(config_id: int):
    """Stop fetching emails for a specific configuration"""
    if not settings_manager.get_config(config_id):
        raise HTTPException(status_code=404, detail="Email configuration not found")
    
    scheduler.remove_job(config_id)
    return {"message": f"Stopped fetching emails for configuration {config_id}"}


@router.post("/email-configs/{config_id}/run")
async def run_email_fetch(config_id: int):
    """Run email fetching manually for a specific configuration"""
    config = settings_manager.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Email configuration not found")
    
    try:
        action_fetch_data(config['email'], config['password'])
        return {"message": f"Successfully fetched emails for {config['email']}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/global-settings", response_model=GlobalSettingsResponse)
async def get_global_settings():
    """Get global settings"""
    settings = settings_manager.get_global_settings()
    if not settings:
        return {"googleSheetUrl": ""}
    return settings


@router.put("/global-settings", response_model=GlobalSettingsResponse)
async def update_global_settings(settings: GlobalSettings):
    """Update global settings"""
    try:
        updated_settings = settings_manager.update_global_settings(settings.model_dump())
        if not updated_settings:
            raise HTTPException(status_code=400, detail="Failed to update global settings")
        return updated_settings
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

