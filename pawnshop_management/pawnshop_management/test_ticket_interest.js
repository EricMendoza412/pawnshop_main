// Run with node. Uses actual form code and controlled response ordering.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');

function harness(kind) {
    const requests = [];
    const handlers = {};
    const context = {
        console, __: s => s,
        flt: (v, p) => p == null ? Number(v || 0) : Number(Number(v || 0).toFixed(p)),
        precision: () => 2,
        frappe: {
            session: {user: 'staff'},
            ui: {form: {on(doctype, events) { Object.assign(handlers, events); }}},
            throw(message) { throw new Error(message); },
            call() { return new Promise((resolve, reject) => requests.push({resolve, reject})); }
        }
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(path.join(__dirname, 'doctype', kind, kind + '.js'), 'utf8'), context);
    const frm = {
        doc: {docstatus: 0, desired_principal: 1000, interest: 0, net_proceeds: 0},
        is_new() { return !this.doc.name; },
        set_df_property() {}, toggle_display() {}, set_intro() {},
        async set_value(field, value) {
            if (typeof field === 'object') Object.assign(this.doc, field);
            else this.doc[field] = value;
        }
    };
    const reply = kind === 'pawn_ticket_jewelry'
        ? {message: {eligible: false, regular_rate: 10, promo_rate: 1}}
        : {message: 10};
    return {context, requests, handlers, frm, reply};
}

(async () => {
    for (const kind of ['pawn_ticket_non_jewelry', 'pawn_ticket_jewelry']) {
        const {context, requests, frm, reply, handlers} = harness(kind);
        // Old zero-principal response cannot overwrite the new principal's amounts.
        frm.doc.desired_principal = 0;
        const old = context.set_item_interest(frm);
        frm.doc.desired_principal = 5000;
        const latest = context.set_item_interest(frm);
        requests[1].resolve(reply); await latest;
        requests[0].resolve(reply); await old;
        assert.equal(frm.doc.interest, 500);
        assert.equal(frm.doc.net_proceeds, 4500);
        // Validation waits even if a later edit supersedes its request.
        let saved = false;
        const validation = handlers.validate(frm).then(() => { saved = true; });
        frm.doc.desired_principal = 7000;
        const changed = context.set_item_interest(frm);
        requests[2].resolve(reply);
        await new Promise(r => setImmediate(r));
        assert.equal(saved, false);
        requests[3].resolve(reply); await changed; await validation;
        assert.equal(frm.doc.interest, 700);
        assert.equal(frm.doc.net_proceeds, 6300);
        // Failure prevents save and does not replace amounts with zero.
        const failed = handlers.validate(frm);
        const rejected = assert.rejects(failed, /could not be calculated/);
        requests[4].reject(new Error('offline')); await rejected;
        assert.equal(frm.doc.interest, 700);
        // Invalid numeric input blocks calculation, rather than silently coercing to zero.
        frm.doc.desired_principal = 'invalid';
        const invalid = context.set_item_interest(frm);
        const invalidCheck = assert.rejects(invalid, /positive Desired Principal/);
        requests[5].resolve(reply); await invalidCheck;
        // Submitted financial history is not changed.
        frm.doc.docstatus = 1;
        const history = context.set_item_interest(frm);
        if (kind === 'pawn_ticket_jewelry') requests[6].resolve(reply);
        await history;
        assert.equal(frm.doc.interest, 700);
    }
    for (const kind of ['pawn_ticket_non_jewelry', 'pawn_ticket_jewelry']) {
        const {context, frm, requests, reply} = harness(kind);
        const field = kind === 'pawn_ticket_jewelry' ? 'jewelry_items' : 'non_jewelry_items';
        frm.doc[field] = [{suggested_appraisal_value: 2000}, {suggested_appraisal_value: 3000}];
        context.$ = {each: (rows, fn) => rows.forEach((row, index) => fn(index, row))};
        assert.equal(context.set_total_appraised_amount(frm), 5000);
        const pending = context.set_item_interest(frm);
        requests[0].resolve(reply); await pending;
        assert.equal(frm.doc.net_proceeds, 4500);
        frm.doc[field][0].suggested_appraisal_value = 'invalid';
        assert.throws(() => context.set_total_appraised_amount(frm), /appraisal values/);
        assert.equal(frm.doc.desired_principal, 5000);
    }
    const {context, frm, requests, reply} = harness('pawn_ticket_jewelry');
    frm.doc.desired_principal = 5000;
    const calculation = context.set_item_interest(frm);
    const refresh = context.update_jewelry_interest(frm);
    requests[0].resolve(reply); await calculation;
    requests[1].resolve(reply); await refresh;
    assert.equal(frm.doc.interest, 500);
    assert.equal(frm.doc.net_proceeds, 4500);
    console.log('Passed ticket calculation races, save waiting, failures, numeric validation, history, and refresh tests.');
})().catch(error => { console.error(error); process.exitCode = 1; });
