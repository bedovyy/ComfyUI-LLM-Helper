import asyncio
import base64
import copy
import json
from io import BytesIO

import aiohttp
from PIL import Image

from comfy_api.latest import io
from comfy.model_management import throw_exception_if_processing_interrupted
from comfy.utils import ProgressBar

from .env import get_env
from .logger import logger

class PostChatCompletions(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="LLMHelper_PostChatCompletions",
            display_name="LLM:ChatCompletions",
            category="LLMHelper",
            description="Call OpenAI-compatible /chat/completions",
            inputs=[
                io.Custom("LLM_CLIENT").Input(id="llm_client"),
                io.Custom("LLM_MESSAGES").Input("llm_messages"),
                io.Custom("LLM_OPTIONS").Input(
                    id="llm_options",
                    tooltip="JSON object merged into request body",
                    optional=True
                ),
                io.Int.Input(id="seed", default=0, min=0, max=0xffffffff, control_after_generate=False),
            ],
            outputs=[
                io.String.Output(display_name="STRING"),
            ],
        )
    
    @staticmethod
    def _log_usage(usage_data: dict) -> None:
        if not usage_data: return

        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", 0)
        logger.debug(f"Completions Prompt:{prompt_tokens}, Completion:{completion_tokens}, Total:{total_tokens}")

    @classmethod
    async def execute(cls, llm_client, llm_messages, llm_options=None, seed=0) -> io.NodeOutput:
        base_url = llm_client["base_url"]
        api_key = get_env(llm_client["env_var"])
        model_name = llm_client["model_name"]

        url = base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        body = copy.deepcopy(llm_options) if llm_options is not None else {}
        is_stream = body.get("stream", True)
        body["model"] = model_name
        body["seed"] = seed
        body["messages"] = llm_messages
        body["stream"] = is_stream
        if logger.isEnabledFor(logger.DEBUG) and is_stream:
            body["stream_options"] = {"include_usage": True}

        timeout = aiohttp.ClientTimeout(total=300, sock_read=60)
        current_step = 0
        pbar = ProgressBar(512)
        text_chunks = []
        async with aiohttp.ClientSession() as session, \
                session.post(url, headers=headers, json=body, timeout=timeout) as resp:
            resp.raise_for_status()
            
            if not is_stream:
                result_json = await resp.json()
                cls._log_usage(result_json.get("usage", {}))
                content = result_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                return io.NodeOutput(content)

            async for line in resp.content:
                if not line: continue
                throw_exception_if_processing_interrupted()

                line_str = line.decode("utf-8").strip()
                if not line_str.startswith("data:"): continue

                data_content = line_str[5:].strip()
                if data_content == "[DONE]": break
                
                try:
                    chunk_json = json.loads(data_content)
                    if "usage" in chunk_json and chunk_json["usage"]:
                        cls._log_usage(chunk_json["usage"])
                    
                    choices = chunk_json.get("choices") or []
                    content = choices[0].get("delta", {}).get("content", "") if choices else ""
                    if content:
                        text_chunks.append(content)
                        current_step += 1
                        max_steps = body.get("max_tokens") or 1 << max(9, current_step.bit_length())
                        pbar.update_absolute(current_step, max_steps)
                        await asyncio.sleep(0)
                except json.JSONDecodeError:
                    continue

        text = "".join(text_chunks)
        return io.NodeOutput(text)


class LLMMessages(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        autogrow_template = io.Autogrow.TemplatePrefix(io.Image.Input("image"), prefix="image", min=0, max=20)
        return io.Schema(
            node_id="LLMHelper_LLMMessages",
            display_name="LLM:Message",
            category="LLMHelper",
            search_aliases=["LLM", "ChatCompletions"],
            description="Message for the ChatCompletions",
            inputs=[
                io.Custom("LLM_MESSAGES").Input("llm_messages", optional=True),
                io.Autogrow.Input(
                    id="images",
                    template=autogrow_template,
                    display_name="images",
                    tooltip="Optional image input",
                    optional=True,
                ),
                io.Combo.Input(
                    id="image_format",
                    display_name="Image format",
                    options=["png", "jpeg", "webp"],
                    default="png",
                    tooltip="The image format used when sending images to the LLM API",
                ),
                io.DynamicCombo.Input("role", options=[
                    io.DynamicCombo.Option("user", []),
                    io.DynamicCombo.Option("assistant", []),
                    io.DynamicCombo.Option("system", []),
                    io.DynamicCombo.Option("custom", [
                        io.String.Input("custom_role")
                    ]),
                ]),
                io.String.Input(id="prompt", display_name="Prompt", multiline=True),
            ],
            outputs=[
                io.Custom("LLM_MESSAGES").Output(display_name="LLM_MESSAGES"),
            ],
        )

    @staticmethod
    def comfy_image_to_base64(image, image_format="png") -> str:
        image_format = image_format.lower()
        assert image_format in ("png", "jpeg", "webp"), f"Unsupported format: {image_format}"

        img_np = (image * 255.0).clamp(0, 255).byte().cpu().numpy()
        img = Image.fromarray(img_np)
        if image_format == "jpeg" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format=image_format.upper())
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/{image_format};base64,{b64}"

    @staticmethod
    def _iter_autogrow_images(images: dict):
        def get_index(name):
            suffix = name.removeprefix("image")
            return int(suffix) if suffix.isdigit() else 0

        for name in sorted(images.keys(), key=get_index):
            image = images.get(name)
            if image is not None:
                yield from image if len(image.shape) == 4 else [image]

    @classmethod
    def execute(cls, llm_messages=None, images=None, image_format="png", role={}, prompt="") -> io.NodeOutput:
        messages = list(llm_messages) if llm_messages is not None else []
        final_role = role.get("custom_role", "custom") if role.get("role") == "custom" else role.get("role")
        if not (final_role and str(final_role).strip()):
            raise ValueError("custom_role cannot be empty.")

        if images:
            existing_image_count = 0
            for msg in messages:
                content = msg.get("content")
                if isinstance(content, list):
                    existing_image_count += len([p for p in content if p.get("type") == "image_url"])
            
            image_parts = []
            for frame in cls._iter_autogrow_images(images):
                base64_image = cls.comfy_image_to_base64(frame, image_format)
                image_parts.append({"type": "image_url", "image_url": {"url": base64_image}})
            logger.debug(f"Completions Total image:{len(image_parts)}")

            combined_parts = [] #NOTE: should it be optional?
            for i, img_obj in enumerate(image_parts, start=existing_image_count + 1):
                combined_parts.extend([{"type": "text", "text": f"[Image {i}]"}, img_obj])
            # combined_parts = image_parts

            final_content = combined_parts + ([{"type": "text", "text": prompt}] if prompt else []) 
        else:
            final_content = prompt

        messages.append({ "role": final_role, "content": final_content })
        return io.NodeOutput(messages)


class LLMOptions(io.ComfyNode):
    ORDER = ["temperature", "top_p", "top_k", "min_p", "presence_penalty", "repetition_penalty", "max_tokens"]

    @staticmethod
    def _param_input(param_name: str, level: int):
        params = {
            "temperature": (io.Float.Input, {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
            "top_p": (io.Float.Input, {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            "top_k": (io.Int.Input, {"default": -1, "min": -1, "max": 1000}),
            "min_p": (io.Float.Input, {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            "presence_penalty": (io.Float.Input, {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.01}),
            "repetition_penalty": (io.Float.Input, {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
            "max_tokens": (io.Int.Input, {"default": 512, "min": 1, "max": 262144}),
        }
        assert param_name in params, f"Unknown parameter: {param_name}"

        input_class, config = params[param_name]
        return input_class(f"{param_name}", **config)

    @staticmethod
    def _build_sampling_combo(remaining: list[str], level: int = 0):
        options = [io.DynamicCombo.Option("none", [])]

        for param_name in remaining:
            next_remaining = [x for x in remaining if x != param_name]
            children = [LLMOptions._param_input(param_name, level)]
            if next_remaining:
                children.append(LLMOptions._build_sampling_combo(next_remaining, level + 1))
            options.append(io.DynamicCombo.Option(param_name, children))

        return io.DynamicCombo.Input(f"option_{level}", options=options)

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="LLMHelper_LLMOptions",
            display_name="LLM:Options",
            category="LLMHelper",
            inputs=[
                io.Custom("LLM_OPTIONS").Input(
                    id="llm_options",
                    display_name="llm_options",
                    tooltip="JSON object merged into request body",
                    optional=True,
                ),
                cls._build_sampling_combo(cls.ORDER, 0)
            ],
            outputs=[io.Custom("LLM_OPTIONS").Output(display_name="LLM_OPTIONS")],
        )

    @classmethod
    def execute(cls, llm_options=None, **kwargs) -> io.NodeOutput:
        def walk(data_dict: dict, level: int = 0, accumulated: dict = None) -> dict:
            if accumulated is None:
                accumulated = {}

            selected = data_dict.get(f"option_{level}")
            if selected and selected != "none":
                if selected in data_dict:
                    accumulated[selected] = data_dict[selected]

                for v in data_dict.values():
                    if isinstance(v, dict):
                        walk(v, level + 1, accumulated)
                        break
            return accumulated

        result = copy.deepcopy(llm_options) if llm_options is not None else {}
        for value in kwargs.values():
            walk(value, 0, result)

        return io.NodeOutput(result)


class LLMCustomJsonOptions(io.ComfyNode):
    DEFAULT_CUSTOM_JSON='{\n  "thinking_budget_tokens": 0\n}'

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="LLMHelper_LLMCustomJsonOptions",
            display_name="LLM:CustomJsonOptions",
            category="LLMHelper",
            inputs=[
                io.MultiType.Input(
                    id="llm_options",
                    types=[io.String, io.Custom("LLM_OPTIONS")],
                    display_name="llm_options",
                    tooltip="JSON object merged into request body",
                    optional=True,
                ),
                io.String.Input(
                    id="custom_options",
                    display_name="custom_options",
                    default=cls.DEFAULT_CUSTOM_JSON,
                    multiline=True
                ),
            ],
            outputs=[io.Custom("LLM_OPTIONS").Output(display_name="LLM_OPTIONS")],
        )

    @classmethod
    def execute(cls, llm_options=None, custom_options="{}") -> io.NodeOutput:
        if isinstance(llm_options, str):
            try:
                result = json.loads(llm_options or "{}")
            except json.JSONDecodeError:
                raise ValueError("llm_options must be a valid JSON string")
        else:
            result = copy.deepcopy(llm_options) if llm_options is not None else {}

        try:
            result.update(json.loads(custom_options))
        except json.JSONDecodeError:
            raise ValueError("custom_options must be a valid JSON string")

        return io.NodeOutput(result)
