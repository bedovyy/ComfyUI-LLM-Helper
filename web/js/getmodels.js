const { app } = window.comfyAPI.app;
const { api } = window.comfyAPI.api;

app.registerExtension({
  name: "LLMHelper.getmodels",
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (!nodeData?.category?.startsWith("LLMHelper")) { return; }

    if (nodeData.name == "LLMHelper_GetModels") {
      nodeType.prototype.onConnectInput = function () {
	app.extensionManager.toast.add({
	  severity: "info",
	  summary: nodeData.display_name,
	  detail: "This node cannot have input connections.",
	  life: 5000,
	});
	return false;
      }    //prevent input connection
      nodeType.prototype.onNodeCreated = function () {
        this.addWidget("button", "Update model names", null, async () => {
	  const data = {
	    base_url: this.widgets.find(w => w.name === "base_url")["value"],
	    env_var: this.widgets.find(w => w.name === "env_var")["value"],
	  };
	  const resp = await api.fetchApi("/llmhelper/models", { method: "POST", body: JSON.stringify(data) });
	  const models = (await resp.json()).models;
	  if (models) {
	    const model_name_widget = this.widgets.find(w => w.name === "model_name");
	    model_name_widget["options"]["values"] = models;
	    if (!models.includes(model_name_widget["value"])) {
	      model_name_widget["value"] = models[0];
            }
          }
        })
      }
    }
  },
})
