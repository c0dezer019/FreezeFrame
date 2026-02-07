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

                // --- THE CSS HACK ---
                // Since LiteGraph draws on Canvas, CSS margins don't exist.
                // We hack it by injecting a 'Ghost Widget' that forces the layout engine to push elements down.
                const createMargin = (height) => {
                    const w = this.addWidget("label", "", ""); // Invisible label
                    w.computeSize = () => [0, height]; // Override size calculator to force vertical spacing
                    return w;
                };

                // 1. Inject Margin (20px) ABOVE the Resume Button
                createMargin(20); 

                // 2. Control Deck
                this.addWidget("button", "▶️ RESUME", null, () => sendSignal("PROCEED"));
                this.addWidget("button", "⏸️ PAUSE", null, () => sendSignal("PAUSE"));

                // 3. Precision CFG Fix
                const cfgWidget = this.widgets.find(w => w.name === "cfg");
                if (cfgWidget) {
                    cfgWidget.step = 0.1;
                    if (!cfgWidget.options) cfgWidget.options = {};
                    cfgWidget.options.step = 0.1;
                    cfgWidget.options.precision = 1;
                }

                // Adjust size: Add extra height to account for the new margins
                const isAdvanced = nodeData.name.includes("Advanced");
                this.setSize([300, isAdvanced ? 480 : 320]);
                
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
