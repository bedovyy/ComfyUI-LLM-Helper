import aiohttp

from comfy_api.latest import io

from .env import get_env_keys, get_env
from .logger import logger

NO_API_KEY="/* no api key */"

class GetModels(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        env_vars = get_env_keys()
        env_vars.insert(0, NO_API_KEY)
        return io.Schema(
            node_id="LLMHelper_GetModels",
            display_name="LLM:Client",
            category="LLMHelper",
            description="Get models.",
            inputs=[
                io.String.Input(
                    id="base_url",
                    display_name="Base URL",
                    tooltip="The base URL to use for /models",
                    placeholder="http(s)://host[:port]",
                    default="http://localhost:8000/v1",
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
                    lazy=True,
                    options=["set url and click update"]
                ),
            ],
            outputs=[io.Custom("LLM_CLIENT").Output(id="llm_client", display_name="LLM_CLIENT")]
        )
    
    # necessary to allow the dynamic model_name from js
    @classmethod
    def validate_inputs(cls, base_url, **kwargs) -> bool | str:
        return "base_url must be specified" if base_url == "" else True

    @classmethod
    def execute(cls, base_url, env_var, model_name) -> io.NodeOutput:
        env_var = None if env_var == NO_API_KEY else env_var
        llm_client = {
            "base_url": base_url.rstrip("/"),
            "env_var": env_var,
            "model_name": model_name,
        }
        return io.NodeOutput(llm_client)

class PostModelsUnload(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="LLMHelper_PostModelsUnload",
            display_name="LLM:UnloadModel (llama.cpp)",
            category="LLMHelper",
            description="Unload model.",
            inputs=[
                io.Custom("LLM_CLIENT").Input(id="llm_client", tooltip="LLMClient to unload."),
                io.AnyType.Input(id="input_any", display_name="*", tooltip="connect any to run the node"),
            ],
            outputs=[
                io.AnyType.Output(id="output_any", display_name="OUTPUT", tooltip="connect any to bypass"),
            ],
        )
    
    @classmethod
    def validate_inputs(cls, llm_client, input_any) -> bool | str:
        return "base_url must be specified" if llm_client and not llm_client.get("base_url") else True

#    @classmethod
#    def fingerprint_inputs(cls, **kwargs) -> str:
#        return str(time.time()) # force run

    @classmethod
    async def execute(cls, llm_client, input_any) -> io.NodeOutput:
        base_url = llm_client["base_url"]
        api_key = get_env(llm_client["env_var"])
        model_name = llm_client["model_name"]
        modified_base_url = base_url.rstrip("/").removesuffix("/v1")
        url = f"{modified_base_url}/models/unload"

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        data = { "model": model_name }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                logger.debug(f"UnloadModel Response - Status: {resp.status}")
                resp.raise_for_status()

        return io.NodeOutput(input_any)


class LLMUnpackClient(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="LLMHelper_UnpackClient",
            display_name="LLM:Unpack client",
            category="LLMHelper",
            description="Unpacks the LLMClient. Warning: API keys may be exposed.",
            inputs=[io.Custom("LLM_CLIENT").Input(id="llm_client", tooltip="LLMClient to unload.")],
            outputs=[
                io.String.Output(id="output_base_url", display_name="BASE_URL"),
                io.String.Output(id="output_api_key", display_name="API_KEY"),
                io.String.Output(id="output_model_name", display_name="MODEL_NAME"),
            ]
        )

    @classmethod
    def execute(cls, llm_client) -> io.NodeOutput:
        base_url = llm_client["base_url"].rstrip("/")
        api_key = get_env(llm_client["env_var"], "")
        model_name = llm_client["model_name"]
        return io.NodeOutput(base_url, api_key, model_name)
