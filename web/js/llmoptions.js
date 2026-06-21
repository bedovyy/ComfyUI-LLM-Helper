const { app } = window.comfyAPI.app;

const TARGET = "LLMHelper_LLMOptions";
const MIN_WIDTH = 250;

app.registerExtension({
    name: TARGET,

    async nodeCreated(node) {
        if (node.comfyClass !== TARGET) return;

        // TODO: DynamicCombo has width issue at the moment, so fix min size.
        const computeSize = node.computeSize;
        node.computeSize = function(out) {
            const size = computeSize.apply(this, arguments);
            size[0] = Math.min(MIN_WIDTH, size[0]);
            return size;
        };
    },
});
