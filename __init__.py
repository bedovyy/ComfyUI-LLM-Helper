import os
from typing import override

from comfy_api.latest import ComfyExtension, io
from dotenv import load_dotenv
import folder_paths

from .nodes_client import *
from .nodes_completions import *
from .nodes_utils import *
from .routes import *


env_path = os.path.join(folder_paths.base_path, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

class LLMHelperExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            GetModels,
            PostModelsUnload,
            LLMUnpackClient,
            PostChatCompletions,
            LLMMessages,
            LLMOptions,
            LLMCustomJsonOptions,
            PreviewAnyStorable,
        ]

async def comfy_entrypoint() -> LLMHelperExtension:
    return LLMHelperExtension()

WEB_DIRECTORY = "./web"
