# Voice Assistant for Odoo 19

Press **Ctrl + Space** (or click the microphone in the top bar), speak a command,
and Odoo opens / searches / creates the matching record. Works with English and
Hindi commands.

## Examples you can say

| You say | What happens |
|---|---|
| "open customer Sachin" | Opens the contact named Sachin |
| "search product wireless mouse" | Opens a filtered product list |
| "create lead" | Opens a blank CRM lead form |
| "open invoice INV/2024/0042" | Opens that invoice |
| "ग्राहक सचिन खोलो" | Opens customer Sachin (Hindi) |

## Install

1. Copy the `inom_voice_assistant` folder into your Odoo `addons` path.
2. Restart the Odoo service.
3. Turn on **Developer Mode** (Settings → Developer Tools).
4. Go to **Apps**, click **Update Apps List**, search "Voice Assistant", click **Install**.
5. Reload the browser. Allow microphone access when prompted.

> **Browser:** Use **Chrome** or **Edge**. The Web Speech API has limited support
> in Firefox/Safari. The site must be served over **HTTPS** (or localhost) for the
> microphone to work.

## Add support for a new object

Open `static/src/js/command_config.js` and add one entry to `COMMAND_MAP`:

```js
{
    keywords: ["expense", "व्यय", "खर्च"],  // words people might say
    model: "hr.expense",                    // Odoo technical model
    nameField: "name",                       // field to match the spoken name
    label: "Expense",                        // shown in notifications
},
```

That's it — no other file needs changing. To find a model's technical name,
turn on Developer Mode and hover any menu/field, or check Settings → Technical → Models.

## Change the recognition language

In the same file, set `RECOGNITION_LANG` (e.g. `"hi-IN"` for Hindi-first,
`"en-IN"` for Indian English). The parser understands both English and Hindi
keywords regardless of this setting.

## How it works

1. Browser's Web Speech API converts your speech to text (no server / API key).
2. `command_parser.js` extracts the **verb** (open/search/create) and the **object**.
3. `inom_voice_assistant_service.js` searches the model via the ORM and calls the
   action service to navigate.

## Notes & limits

- Recognition accuracy depends on accent, mic quality, and background noise.
- For higher accuracy you can later swap the Web Speech API for a cloud STT
  service (Google Cloud Speech, OpenAI Whisper) — only the `recognition` part
  of `inom_voice_assistant_service.js` would change.
- The user only sees records they have access rights to.

## Troubleshooting

### "Voice recognition error: network"
The browser Speech API sends audio to the browser vendor's online speech
service. This error means that machine could not reach it. Check:
- The computer running the **browser** has working internet access.
- No corporate proxy / firewall is blocking it (common on locked-down test servers).
- You are on **HTTPS** or **localhost** (required for the microphone).
Try opening a normal website to confirm connectivity, then tap the mic to retry.

### The "Listening…" message used to repeat
Fixed in this version: holding Ctrl+Space no longer re-triggers (the key
auto-repeat is ignored), and there is now a single bottom-center pill that
updates in place instead of stacked notifications.

## Configuring commands in the UI (no code)

A configuration screen lets you add commands without touching any file:

**Settings → Voice Assistant → Voice Commands**

Each command has:
- **Name** — label shown in the listening pill.
- **Keywords** — comma-separated words to listen for (English and/or Hindi).
- **Command type:**
  - *Open / search records of a model* — pick a **Model** (e.g. Contact).
    Saying "open <kw> <name>" opens the record; "search <kw> <name>" lists matches.
  - *Open a specific action / screen* — pick an **Action** (e.g. your dashboard).
    Saying any keyword launches that screen directly.
- **Match field** — usually `name` (kept for reference; matching uses name_search).
- **Sequence / Active** — ordering and on/off.

Commands you add here are merged with the built-in defaults, and DB commands take
priority. New/edited commands take effect immediately (the assistant re-reads them
on each command — no reload needed). Only Settings administrators can edit; all
internal users can use the commands.

### Example: open your dashboard by voice
1. New command, Name = "Dashboard".
2. Keywords = `dashboard, home, डैशबोर्ड`.
3. Command type = *Open a specific action / screen*.
4. Action = your dashboard window action.
5. Save. Now say "open dashboard".

## Auto-generate commands (one click)

On the Voice Commands list there are two header buttons:

- **Generate from Menus** — scans the screens in your menus and creates an
  "open action" command for each (named after the menu). Say the screen name
  to open it, e.g. "open contacts".
- **Generate from Models** — creates an "open model" command for each model
  behind those screens, so you can open records by name, e.g. "open lead Acme".

Both skip anything already configured, so you can click them again safely after
installing new apps. The verbs (open / search / create / खोलो / खोजो / बनाओ)
apply automatically to every generated command — you only get the names.
