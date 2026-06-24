const { app } = window.comfyAPI.app;
const { api } = window.comfyAPI.api;

const TARGET="LLMHelper_GetModels"

app.registerExtension({
    name: TARGET,

    async nodeCreated(node) {
        if (node.comfyClass !== TARGET) return;

        const baseUrlWidget = node.widgets.find(w => w.name === "base_url");
        const envVarWidget = node.widgets.find(w => w.name === "env_var");
        const modelNameWidget = node.widgets.find(w => w.name === "model_name");

        node.addWidget("button", "Update model names", null, async () => {
            const data = {
                base_url: baseUrlWidget.value,
                env_var: envVarWidget.value,
            };
            const originalModelName = modelNameWidget.value
            modelNameWidget.value = "Updating..."
            const resp = await api.fetchApi("/llmhelper/models", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(data)
            });
            const models = (await resp.json()).models;
            if (models) {
                modelNameWidget.options.values = models;
                modelNameWidget.value = models.includes(originalModelName) ? originalModelName : models[0];
            }
        });

        node.inputs = []; // make widgets socketless
    },
})
