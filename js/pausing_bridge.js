import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "Comfy.Pause.Control",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Target Standard, Advanced, and Custom nodes
        const validNodes = ["PSampler", "PSamplerAdvanced", "PSamplerCustom", "PSamplerCustomAdvanced"];
        
        if (validNodes.includes(nodeData.name)) {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                // 1. Control Deck
                this.addWidget("button", "▶️ RESUME", null, () => sendSignal("PROCEED"));
                this.addWidget("button", "⏸️ PAUSE", null, () => sendSignal("PAUSE"));

                // 2. Precision CFG Fix
                const cfgWidget = this.widgets.find(w => w.name === "cfg");
                if (cfgWidget) {
                    cfgWidget.step = 0.1;
                    if (!cfgWidget.options) cfgWidget.options = {};
                    cfgWidget.options.step = 0.1;
                    cfgWidget.options.precision = 1;
                }

                // Adjust size slightly based on node type
                const isAdvanced = nodeData.name.includes("Advanced");
                this.setSize([300, isAdvanced ? 440 : 280]);
                
                return r;
            };
        }
    }
});

async function sendSignal(command) {
    try {
        await api.fetchApi("/comfy/pause_signal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command: command }),
        });
    } catch (error) {
        console.error("[P-Sampler] API Error:", error);
    }
}
