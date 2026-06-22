import json
import time
import torch

from comfy_api.latest import ComfyExtension, io, ui

class PreviewAnyStorable(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="LLMHelper_PreviewAnyStorable",
            display_name="Preview as Text (storable)",
            category="LLMHelper",
            is_input_list=True,
            is_output_node=True,
            inputs=[
                io.AnyType.Input("source", optional=True, lazy=True),
                io.Boolean.Input("output_value", default=False, label_on="stored", label_off="source"),
                io.String.Input("stored", multiline=True, default='[""]', lazy=True, socketless=True),
            ],
            outputs=[
                io.String.Output(display_name="STRING", is_output_list=True),
            ],
            hidden=[io.Hidden.unique_id, io.Hidden.extra_pnginfo],
            search_aliases=["show output", "inspect", "debug", "print value", "show text"],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs) -> float:
        return str(time.time()) # force run

    @classmethod
    def check_lazy_status(cls, source=None, output_value=False, **kwargs):
        return ["stored"] if output_value[0] else ["source"]

    @staticmethod
    def _truncate_nested_strings(obj, max_len=1000, keep_len=20):
        if isinstance(obj, dict):
            return {k: PreviewAnyStorable._truncate_nested_strings(v, max_len, keep_len) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [PreviewAnyStorable._truncate_nested_strings(item, max_len, keep_len) for item in obj]
        elif isinstance(obj, str):
            if len(obj) >= max_len:
                return f"{obj[:keep_len]}...{obj[-keep_len:]}"
            return obj
        return obj

    @classmethod
    def execute(cls, source=None, output_value=False, stored='[""]') -> io.NodeOutput:
        use_stored = output_value[0]

        results = []
        if use_stored:
            stored_list = stored if isinstance(stored, list) else [stored]
            if stored_list and stored_list[0]:
                try:
                    parsed = json.loads(stored_list[0])
                    results = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    results = [stored_list[0]]
            results = [str(x) for x in results] # just in case
        else:
            source_list = source if isinstance(source, list) else ([source] if source is not None else [])
            torch.set_printoptions(edgeitems=6)
            for source in source_list:
                if source is None:
                    value = "None"
                elif isinstance(source, str):
                    value = cls._truncate_nested_strings(source)
                elif isinstance(source, (int, float, bool)):
                    value = str(source)
                else:
                    try:
                        value = json.dumps(cls._truncate_nested_strings(source), indent=2, ensure_ascii=False)
                    except Exception:
                        try:
                            value = str(source)
                        except Exception:
                            value = "source exists, but could not be serialized."
                results.append(value)
            torch.set_printoptions()

        # store json formatted output
        text = json.dumps(results, ensure_ascii=False)
        if not use_stored:
            extra_pnginfo = cls.hidden.extra_pnginfo
            unique_id = cls.hidden.unique_id
            if extra_pnginfo and "workflow" in extra_pnginfo:
                for node in extra_pnginfo["workflow"].get("nodes", []):
                    if str(node.get("id")) == str(unique_id):
                        if "widgets_values" in node:
                            node["widgets_values"][1] = text
                        break

        return io.NodeOutput(results, ui=ui.PreviewText(text))
