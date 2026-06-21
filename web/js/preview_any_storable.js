const { app } = window.comfyAPI.app;
const { ComfyWidgets } = window.comfyAPI.widgets;

const TARGET = "LLMHelper_PreviewAnyStorable"

app.registerExtension({
    name: TARGET,

    async nodeCreated(node) {
        if (node.comfyClass !== TARGET) return;

        const storedWidget = node.widgets?.find(w => w.name === "stored");
        const useStoredWidget = node.widgets?.find(w => w.name === "output_value");
        const previewWidget = ComfyWidgets['STRING'](node, 'preview_text', ['STRING', { multiline: true }], app).widget

        storedWidget.hidden = true;
        storedWidget.options.hidden = true
        node.inputs = node.inputs.filter(i => !["stored", "output_value"].includes(i.name));

        previewWidget.label = 'Preview'
        previewWidget.hidden = false
        previewWidget.options.hidden = false
        previewWidget.options.read_only = true
        previewWidget.options.serialize = false
        previewWidget.element.readOnly = true
        previewWidget.element.disabled = true
        previewWidget.element.style.opacity = "0.6";
        previewWidget.element.style.cursor = "default";
        previewWidget.element.style.userSelect = "text";
        previewWidget.serialize = false

        const originalOutline = previewWidget.element.style.outline || "none"
        const enabledOutline = "2px solid var(--success-background)"
        
        node.onConfigure = function(info) {
            try {
                const text = JSON.parse(storedWidget.value || '[""]');
                previewWidget.value = Array.isArray(text) ? (text?.join('\n\n') ?? '') : text;
                previewWidget.element.style.outline = useStoredWidget.value ? enabledOutline : originalOutline;
            } catch {
                console.error("[LLMHelper] preview_any_storable.onConfigure", storedWidget.value)
                previewWidget.value = storedWidget.value ?? "";
            }
        };

        node.onWidgetChanged = function(name, value, old_value, widget) {
            previewWidget.element.style.outline = useStoredWidget.value ? enabledOutline : originalOutline;
        }

        node.onExecuted = function (message) {
            if (message?.text) {
                if (previewWidget) {
                    const text = JSON.parse(message.text);
                    previewWidget.value = Array.isArray(text) ? (text?.join('\n\n') ?? '') : text;
                }
                if (!useStoredWidget.value && storedWidget) {
                    storedWidget.value = Array.isArray(message.text) ? message.text[0] : message.text;
                }
            }
            node.setDirtyCanvas(true, false);
        };
    },
});
