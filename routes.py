import requests
import aiohttp
from server import PromptServer

from .env import get_env

routes = PromptServer.instance.routes
@routes.post('/api/llmhelper/models')
async def post_model_list(request):
    data = await request.json()
    base_url = data["base_url"]
    api_key = get_env(data["env_var"])

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = { "models": ["model not found"] }

    try:
        timeout = aiohttp.ClientTimeout(total=1)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{base_url}/models", headers=headers) as resp:
                resp.raise_for_status() 
                
                json_data = await resp.json()
                source = json_data.get("data") or json_data.get("models") or []
                response["models"] = [item.get("id") or item.get("name") for item in source]

    except aiohttp.ClientResponseError as e:
        response["models"] = [f"{e.status}:{e.message}"]
    except Exception as e:
        response["models"] = [f"Error: {str(e)}"]

    return aiohttp.web.json_response(response)
