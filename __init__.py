from typing_extensions import override
from comfy_api.latest import ComfyExtension, io
from .nodes import *
from .routes import *

from dotenv import load_dotenv
import folder_paths

env_path = os.path.join(folder_paths.base_path, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

class LLMHelperExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            GetModels,
            PostModelsUnload,
        ]

async def comfy_entrypoint() -> LLMHelperExtension:
    return LLMHelperExtension()

WEB_DIRECTORY = "./web"
