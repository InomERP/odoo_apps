/** @odoo-module **/

/**
 * Restores the `hour` groupBy granularity, so the History graph buckets by
 * hour here exactly as it does on Odoo 19.
 *
 * Why this is needed
 * ------------------
 * The server already supports it on this release: `READ_GROUP_TIME_GRANULARITY`
 * in odoo/models.py lists `hour`, and `READ_GROUP_DISPLAY_FORMAT` carries its
 * label format ("HH:00 dd MMM"). Only the web client refuses it.
 *
 * `getGroupBy` (web/static/src/search/utils/group_by.js) validates the
 * interval against `INTERVAL_OPTIONS` from web/static/src/search/utils/dates.js,
 * which lists year/quarter/month/week/day. A view arch asking for
 * `interval="hour"` therefore throws "Invalid groupBy description:
 * <field>:hour" inside GraphModel._normalize, before any RPC is made.
 *
 * Odoo 19 fixed this by splitting the constant in two: `INTERVAL_OPTIONS`
 * still drives the Group By dropdown, while a new `BACKEND_INTERVAL_OPTIONS`
 * (INTERVAL_OPTIONS plus `hour`) is what `getGroupBy` validates against. The
 * effect is that `hour` is accepted when a view arch asks for it, but is NOT
 * offered as a menu option for every date field in the database.
 *
 * This file reproduces that same split on a release that has only one
 * constant:
 *
 *   1. `hour` is added to INTERVAL_OPTIONS, which is what getGroupBy reads.
 *      It is appended last, so `rankInterval` orders it after `day` -- the
 *      coarse-to-fine ordering the search model relies on when sorting
 *      several active intervals on one field.
 *   2. SearchModel then drops it from `this.intervalOptions`, the array that
 *      populates the Group By dropdown. Without step 2 this module would add
 *      an "Hour" entry under every date field in every app in the database,
 *      which a monitoring module has no business doing -- and which Odoo 19
 *      does not do either.
 *
 * Net effect: identical to Odoo 19. The only consumer of `hour` is this
 * module's own graph view.
 */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { SearchModel } from "@web/search/search_model";
import { INTERVAL_OPTIONS } from "@web/search/utils/dates";

const HOUR = "hour";

// Step 1. Widen what getGroupBy will accept. Appended, never reordered.
if (!INTERVAL_OPTIONS[HOUR]) {
    INTERVAL_OPTIONS[HOUR] = {
        description: _t("Hour"),
        id: HOUR,
        groupNumber: 1,
    };
}

// Step 2. Keep it out of the Group By dropdown, matching Odoo 19.
patch(SearchModel.prototype, {
    setup() {
        super.setup(...arguments);
        this.intervalOptions = this.intervalOptions.filter(
            (option) => option.id !== HOUR
        );
    },
});
