/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

/**
 * Siri-style listening pill anchored at the bottom-center of the screen.
 * It is mounted once via the main_components registry and shows/updates in
 * place based on the reactive inom_voice_assistant state -- no stacked toasts.
 */
export class VoiceAssistantOverlay extends Component {
    static template = "inom_voice_assistant.Overlay";
    static props = {};

    setup() {
        this.voice = useService("inom_voice_assistant");
        // useState binds the service's reactive state to THIS component so
        // the pill re-renders whenever status / visible / text change.
        this.state = useState(this.voice.state);
    }

    onClose() {
        this.voice.stop();
        this.voice.hide();
    }
}

registry.category("main_components").add("inom_voice_assistant.Overlay", {
    Component: VoiceAssistantOverlay,
});
