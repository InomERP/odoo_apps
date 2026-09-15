/** @odoo-module **/
/**
 * Remember the view the user last picked for the DMS document actions.
 *
 * The action service is wrapped (not replaced): every successful view switch
 * inside a tracked action is stored, and opening that same action again
 * without an explicit view type restores it. Anything that already carries a
 * view type - a URL, a breadcrumb restore, a button with an explicit target -
 * keeps winning, so normal navigation is untouched.
 */
// Importing the service module itself (rather than pulling it out of the
// registry) guarantees it is evaluated before this patch is applied.
import { actionService } from "@web/webclient/actions/action_service";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

const STORAGE_KEY = "inom_advance_dms.preferred_view.v2";
const TRACKED_MODELS = new Set(["edm.document", "edm.document.group"]);

function readPreferences() {
    try {
        return JSON.parse(browser.localStorage.getItem(STORAGE_KEY) || "{}");
    } catch {
        // Private mode, cleared storage, quota errors: just forget preferences.
        return {};
    }
}

function writePreferences(preferences) {
    try {
        browser.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
    } catch {
        // Storing a preference must never break the action itself.
    }
}

/** Every key an action may be addressed by: its id and its xml id. */
function actionKeys(action) {
    if (!action) {
        return [];
    }
    return [action.id, action.xml_id].filter(Boolean).map(String);
}

/**
 * Is ``viewType`` actually available on this action?
 *
 * Restoring a view the action does not declare leaves the web client waiting
 * for a controller that can never be built, which shows up as a page stuck on
 * "Loading". A stale preference must never be able to do that.
 */
function actionOffersView(action, viewType) {
    if (!action || !viewType) {
        return false;
    }
    const views = action.views || [];
    if (views.length) {
        return views.some((view) => Array.isArray(view) && view[1] === viewType);
    }
    if (typeof action.view_mode === "string") {
        return action.view_mode.split(",").includes(viewType);
    }
    return false;
}

/** The key a doAction() request is addressed by, when we can tell. */
function requestKey(actionRequest) {
    if (typeof actionRequest === "number" || typeof actionRequest === "string") {
        return String(actionRequest);
    }
    if (actionRequest && typeof actionRequest === "object") {
        return String(actionRequest.xml_id || actionRequest.id || "");
    }
    return "";
}

patch(actionService, {
    start(env, deps) {
        const service = super.start(env, deps);
        const originalDoAction = service.doAction;
        const originalSwitchView = service.switchView;
        const originalLoadState = service.loadState;

        service.doAction = function (actionRequest, options = {}) {
            try {
                const key = requestKey(actionRequest);
                // Never override an explicit target: a view type asked for by
                // the caller, or a request to open one specific record.
                if (key && !options.viewType && !options.props?.resId) {
                    const stored = readPreferences()[key];
                    // When the action object is already resolved we can check
                    // that it offers the view; when it is only an id or xml id
                    // the server decides, and an unusable type is dropped by
                    // the fallback below.
                    const resolved =
                        actionRequest && typeof actionRequest === "object"
                            ? actionRequest
                            : null;
                    if (stored && (!resolved || actionOffersView(resolved, stored))) {
                        options = { ...options, viewType: stored };
                    }
                }
            } catch {
                // A preference must never be able to block an action.
            }
            return originalDoAction.call(service, actionRequest, options);
        };

        // Reloading the page or opening a bookmarked link goes through
        // loadState instead of doAction, so the preference is injected into
        // the restored state as well - unless the URL already names a view
        // or points at one specific record.
        service.loadState = function (state, ...rest) {
            try {
                // Without an explicit state there is nothing to inject a
                // preference into; the service falls back to its own routing.
                const current = state;
                if (current?.action && !current.view_type && !current.resId) {
                    const stored = readPreferences()[String(current.action)];
                    if (stored) {
                        return originalLoadState.call(
                            service,
                            { ...current, view_type: stored },
                            ...rest
                        );
                    }
                }
            } catch {
                // Fall through to the untouched state.
            }
            return originalLoadState.call(service, state, ...rest);
        };

        service.switchView = async function (viewType, ...rest) {
            const result = await originalSwitchView.call(service, viewType, ...rest);
            try {
                // The controller carries the fully loaded action; the
                // service's own ``currentAction`` getter hands back a shielded
                // object whose fields are not readable from here.
                const controller = service.currentController;
                const action = controller?.action;
                // Only multi-record views are worth remembering: switching to
                // a form means "open this record", not "show me this view
                // next time".
                const isMultiRecord = controller?.view?.multiRecord;
                if (
                    action &&
                    isMultiRecord &&
                    viewType !== "form" &&
                    action.type === "ir.actions.act_window" &&
                    TRACKED_MODELS.has(action.res_model) &&
                    actionOffersView(action, viewType)
                ) {
                    const preferences = readPreferences();
                    for (const key of actionKeys(action)) {
                        preferences[key] = viewType;
                    }
                    writePreferences(preferences);
                }
            } catch {
                // Remembering the view is a nicety, never a requirement.
            }
            return result;
        };

        return service;
    },
});
