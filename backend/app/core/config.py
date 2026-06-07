from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    app_timezone: str = "Asia/Kuala_Lumpur"
    jwt_secret: str = ""
    admin_username: str = "safiah"
    admin_password_hash: str = ""
    google_service_account_json: str = ""
    google_drive_root_folder_id: str = ""
    google_sheets_spreadsheet_id: str = ""
    owner_whatsapp_number: str = ""
    owner_notification_email: str = ""
    bank_name: str = ""
    bank_account_number: str = ""
    bank_account_name: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_template_order_confirm: str = ""
    whatsapp_template_payment_received: str = ""
    whatsapp_template_receipt: str = ""
    resend_api_key: str = ""
    from_email: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    sentry_dsn: str = ""
    telegram_bot_token: str = ""
    telegram_dev_chat_id: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
