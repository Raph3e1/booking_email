from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict
import json
import os
from datetime import datetime


class EmailConfig(BaseModel):
    id: int
    email: EmailStr
    password: str = Field(..., min_length=1)  # Ensure password is not empty
    fetchInterval: int = Field(..., ge=1, le=60)  # Ensure interval is between 1 and 60 minutes
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class SettingsManager:
    def __init__(self, file_path: str = "data/settings.json"):
        self.file_path = file_path
        self._ensure_data_directory()
        self._ensure_settings_file()

    def _ensure_data_directory(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def _ensure_settings_file(self):
        if not os.path.exists(self.file_path):
            default_settings = {
                "global_settings": {
                    "googleSheetUrl": "",
                    "sheetName": ""
                },
                "email_configs": [],
                "exchangeRate": 0
            }
            with open(self.file_path, 'w') as f:
                json.dump(default_settings, f, indent=2)
        else:
            # Ensure file has the correct structure
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    if "global_settings" not in data:
                        data["global_settings"] = {
                            "googleSheetUrl": "",
                            "sheetName": ""
                        }
                    if "email_configs" not in data:
                        data["email_configs"] = []
                    if "exchangeRate" not in data:
                        data["exchangeRate"] = 0
                    with open(self.file_path, 'w') as f:
                        json.dump(data, f, indent=2)
            except json.JSONDecodeError:
                # If file is corrupted, reset it
                default_settings = {
                    "global_settings": {
                        "googleSheetUrl": "",
                        "sheetName": ""
                    },
                    "email_configs": [],
                    "exchangeRate": 0
                }
                with open(self.file_path, 'w') as f:
                    json.dump(default_settings, f, indent=2)

    def _read_settings(self):
        with open(self.file_path, 'r') as f:
            return json.load(f)

    def _write_settings(self, data):
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def get_global_settings(self) -> Dict:
        """Get global settings"""
        data = self._read_settings()
        return data.get("global_settings", {"googleSheetUrl": "", "sheetName": ""})

    def update_global_settings(self, new_settings: Dict) -> Dict:
        """Update global settings"""
        data = self._read_settings()
        data["global_settings"] = new_settings
        self._write_settings(data)
        return new_settings

    def get_all_configs(self):
        data = self._read_settings()
        return data.get("email_configs", [])

    def get_config(self, config_id: int):
        configs = self.get_all_configs()
        return next((config for config in configs if config["id"] == config_id), None)

    def create_config(self, config: EmailConfig):
        data = self._read_settings()
        configs = data.get("email_configs", [])

        # Generate new ID
        new_id = max([c.get("id", 0) for c in configs], default=0) + 1
        config.id = new_id

        config_dict = config.model_dump()
        configs.append(config_dict)
        data["email_configs"] = configs
        self._write_settings(data)
        return config_dict

    def update_config(self, config_id: int, config_data: dict):
        data = self._read_settings()
        configs = data.get("email_configs", [])

        for i, config in enumerate(configs):
            if config["id"] == config_id:
                config_data["id"] = config_id
                config_data["updated_at"] = datetime.now()
                configs[i] = config_data
                data["email_configs"] = configs
                self._write_settings(data)
                return config_data
        return None

    def delete_config(self, config_id: int):
        data = self._read_settings()
        configs = data.get("email_configs", [])

        configs = [config for config in configs if config["id"] != config_id]
        data["email_configs"] = configs
        self._write_settings(data)
        return True
