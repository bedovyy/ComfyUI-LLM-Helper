import os
from dotenv import dotenv_values
import folder_paths

_ENV_PATH = os.path.join(folder_paths.base_path, ".env")
_ENV = dotenv_values(_ENV_PATH)

def get_env_keys():
    return list(_ENV.keys())

def get_env(key: str, default=None):
    return _ENV.get(key, default)

def get_envs():
    return dict(_ENV)
