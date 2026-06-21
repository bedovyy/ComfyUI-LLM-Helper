const { app } = window.comfyAPI.app;
const { api } = window.comfyAPI.api;

const TARGET="LLMHelper_GetModels"

app.registerExtension({
    name: TARGET,

    async nodeCreated(node) {
        if (node.comfyClass !== TARGET) return;

        const base_url_widget = node.widgets.find(w => w.name === "base_url");
        const env_var_widget = node.widgets.find(w => w.name === "env_var");
        const model_name_widget = node.widgets.find(w => w.name === "model_name");

        node.addWidget("button", "Update model names", null, async () => {
            const data = {
                base_url: base_url_widget.value,
                env_var: env_var_widget.value,
            };
            const resp = await api.fetchApi("/llmhelper/models", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(data)
            });
            const models = (await resp.json()).models;
            if (models) {
                model_name_widget.options.values = models;
                if (!models.includes(model_name_widget.value)) {
                    model_name_widget.value = models[0];
                }
            }
        });

        node.inputs = []; // make widgets socketless
    },
})
