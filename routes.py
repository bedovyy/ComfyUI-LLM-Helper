import os
import requests
from aiohttp import web
from server import PromptServer
from .env import get_env

routes = PromptServer.instance.routes
@routes.post('/llmhelper/models')
async def post_models(request):
    data = await request.json()
    base_url = data["base_url"]
    api_key = get_env(data["env_var"], "")
    headers = {}
    if api_key != "":
        headers["Authorization"] = f"Bearer {api_key}"
    response = { "models": ["model not found"] }
    try:
        resp = requests.get(f"{base_url}/models", headers=headers, timeout=1)
        resp.raise_for_status()
        json = resp.json()
        if "data" in json:
            ids = [item["id"] for item in json["data"]]
            response["models"] = ids
    except requests.exceptions.RequestException as e:
        r = getattr(e, "response", None)
        response["models"] = [f"{r.status_code}:{r.reason}"]

    return web.json_response(response)
