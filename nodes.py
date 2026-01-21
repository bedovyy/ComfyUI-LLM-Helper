import os
import requests
import folder_paths
from comfy_api.latest import io

from .env import get_env_keys, get_env

class AlwaysEqual(str):
    def __new__(cls, *args):
        return super().__new__(cls, "*")
    def __eq__(self, other):
        return True
    def __hash__(self):
        return 0

class GetModels(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        env_vars = get_env_keys()
        env_vars.insert(0, "/* no api key */")
        return io.Schema(
            node_id="LLMHelper_GetModels",
            display_name="LLMHelper GET /models",
            category="LLMHelper",
            description="Get models.",
            inputs=[
                io.String.Input(
                    id="base_url",
                    display_name="Base URL",
                    tooltip="The base URL to use for /models",
                    placeholder="http(s)://host[:port]",
                    default="http://localhost:8000",
                ),
                io.Combo.Input(
                    id="env_var",
                    display_name=".env API key",
                    tooltip="The environment variable for API key to use.",
                    options=env_vars,
                ),
                io.Combo.Input(
                    id="model_name",
                    display_name="Model name",
                    tooltip="Select model.",
                    options=["set url and click update", AlwaysEqual()]
                ),
            ],
            outputs=[
                io.String.Output(id="output_base_url", display_name="BASE_URL"),
                io.String.Output(id="output_api_key", display_name="API_KEY"),
                io.String.Output(id="output_model_name", display_name="MODEL_NAME"),
            ]
        )

    @classmethod
    def validate_inputs(cls, base_url) -> bool | str:
        if base_url == "":
            return "base_url must be specified"
        return True

    @classmethod
    def execute(cls, base_url, env_var, model_name) -> io.NodeOutput:
        api_key = get_env(env_var, "")
        return io.NodeOutput(base_url.rstrip("/"), api_key, model_name)

class PostModelsUnload(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="LLMHelper_PostModelsUnload",
            display_name="LLMHelper POST /models/unload",
            category="LLMHelper",
            description="Unload model.",
            inputs=[
                io.AnyType.Input(
                    id="input_any",
                    display_name="*",
                    tooltip="connect any to run the node"
                ),
                io.String.Input(
                    id="base_url",
                    display_name="Base URL",
                    tooltip="The base URL to use for /models/unload",
                    placeholder="http(s)://host[:port]",
                    default="http://localhost:8000",
                ),
                io.String.Input(
                    id="api_key",
                    display_name="API Key",
                    tooltip="The API key to use.",
                ),
                io.String.Input(
                    id="model_name",
                    display_name="Model name",
                    tooltip="The model nae to unload. leave empty if you use it for llama-swap",
                ),
            ],
            outputs=[
                io.AnyType.Output(
                    id="output_any",
                    tooltip="connect any to bypass",
                ),
            ],
        )
    @classmethod
    def validate_inputs(cls, base_url) -> bool | str:
        if base_url == "":
            return "base_url must be specified"
        return True

    @classmethod
#    def fingerprint_inputs(cls, **kwargs) -> str:
#        return str(time.time()) # force run

    @classmethod
    def execute(cls, input_any, base_url, api_key, model_name) -> io.NodeOutput:
        modified_base_url = base_url.rstrip("/").removesuffix("/v1")
        url = f"{modified_base_url}/models/unload"
        headers = {}
        if api_key != "":
            headers["Authorization"] = f"Bearer {api_key}"
        data = { "model": model_name, "model_name": model_name }
        resp = requests.post(url, headers=headers, json=data, timeout=1)
        return io.NodeOutput(input_any)

