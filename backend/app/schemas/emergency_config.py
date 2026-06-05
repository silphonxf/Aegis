from typing import List, Literal, Optional

from pydantic import BaseModel, Field


AuthType = Literal["password", "private_key"]
ScriptType = Literal["shell", "sql"]
DbType = Literal["oracle", "dameng", "mysql", "shell_proxy"]
ProcessIdSource = Literal["fixed", "runtime_detect"]
ActionCategory = Literal["reboot_host", "restart_process", "custom_command"]


class EmergencySshHostItem(BaseModel):
    host_code: str = Field(min_length=1, max_length=64)
    host_name: str = Field(min_length=1, max_length=120)
    host_ip: str = Field(min_length=1, max_length=120)
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(min_length=1, max_length=64)
    auth_type: AuthType = "password"
    password_ciphertext: Optional[str] = Field(default=None, max_length=5000)
    private_key_ciphertext: Optional[str] = Field(default=None, max_length=20000)
    private_key_passphrase_ciphertext: Optional[str] = Field(default=None, max_length=5000)
    connect_timeout_ms: int = Field(default=5000, ge=100, le=60000)
    system_id: Optional[int] = None
    enabled: bool = True
    remark: Optional[str] = Field(default=None, max_length=500)
    has_password: bool = False
    has_private_key: bool = False


class EmergencyServerActionItem(BaseModel):
    action_code: str = Field(min_length=1, max_length=64)
    action_name: str = Field(min_length=1, max_length=120)
    target_host_code: str = Field(min_length=1, max_length=64)
    module_type: Literal["server"] = "server"
    action_category: ActionCategory = "reboot_host"
    system_id: Optional[int] = None
    admin_user_id: Optional[int] = None
    script_type: Literal["shell"] = "shell"
    script_body: str = Field(min_length=1, max_length=20000)
    confirm_text: Optional[str] = Field(default=None, max_length=500)
    enabled: bool = True
    remark: Optional[str] = Field(default=None, max_length=500)


class EmergencyDbActionItem(BaseModel):
    action_code: str = Field(min_length=1, max_length=64)
    action_name: str = Field(min_length=1, max_length=120)
    module_type: Literal["database"] = "database"
    db_type: DbType = "oracle"
    system_id: Optional[int] = None
    admin_user_id: Optional[int] = None
    target_host_code: Optional[str] = Field(default=None, max_length=64)
    script_type: ScriptType = "sql"
    script_body: str = Field(min_length=1, max_length=30000)
    param_schema: List[str] = Field(default_factory=list)
    result_mode: Literal["text"] = "text"
    enabled: bool = True
    remark: Optional[str] = Field(default=None, max_length=500)


class EmergencyProcessActionItem(BaseModel):
    action_code: str = Field(min_length=1, max_length=64)
    action_name: str = Field(min_length=1, max_length=120)
    module_type: Literal["process"] = "process"
    action_category: Literal["restart_process", "custom_command"] = "restart_process"
    system_id: Optional[int] = None
    admin_user_id: Optional[int] = None
    target_host_code: str = Field(min_length=1, max_length=64)
    process_name: str = Field(min_length=1, max_length=120)
    process_id_source: ProcessIdSource = "runtime_detect"
    default_process_id: Optional[str] = Field(default=None, max_length=64)
    script_type: Literal["shell"] = "shell"
    script_body: str = Field(min_length=1, max_length=20000)
    enabled: bool = True
    remark: Optional[str] = Field(default=None, max_length=500)


class EmergencyOpsConfig(BaseModel):
    ssh_hosts: List[EmergencySshHostItem] = Field(default_factory=list)
    server_actions: List[EmergencyServerActionItem] = Field(default_factory=list)
    database_actions: List[EmergencyDbActionItem] = Field(default_factory=list)
    process_actions: List[EmergencyProcessActionItem] = Field(default_factory=list)


class EmergencySshHostSaveRequest(EmergencySshHostItem):
    password_plaintext: Optional[str] = Field(default=None, max_length=5000)
    private_key_plaintext: Optional[str] = Field(default=None, max_length=20000)
    private_key_passphrase_plaintext: Optional[str] = Field(default=None, max_length=5000)


class EmergencyServerActionSaveRequest(EmergencyServerActionItem):
    pass


class EmergencyDbActionSaveRequest(EmergencyDbActionItem):
    pass


class EmergencyProcessActionSaveRequest(EmergencyProcessActionItem):
    pass


class EmergencyActionExecuteRequest(BaseModel):
    action_code: str = Field(min_length=1, max_length=64)
    confirm_text: Optional[str] = Field(default=None, max_length=500)
