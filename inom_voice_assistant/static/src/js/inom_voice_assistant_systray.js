/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

/**
 * Microphone button shown in the Odoo top bar (systray).
 * Click toggles listening; the icon reflects the live state.
 */
export class VoiceAssistantSystray extends Component {
    static template = "inom_voice_assistant.Systray";
    static props = {};

    setup() {
        this.voice = useService("inom_voice_assistant");
        // Bind reactive state so the mic's listening class updates live.
        this.state = useState(this.voice.state);
    }

    onClick() {
        this.voice.toggle();
    }
}

export const systrayItem = {
    Component: VoiceAssistantSystray,
};

// Higher sequence = further left in the systray. 50 keeps it near the others.
registry.category("systray").add("inom_voice_assistant.Systray", systrayItem, {
    sequence: 50,
});
