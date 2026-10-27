const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(`${__dirname}/vault_cash_position.js`, 'utf8');
function harness() {
 const events = {};
 const preview = {token: 'original', is_opening_position: false,
  php_system_civ_balance: 100000, usd_system_civ_balance: 100,
  php_latest_fund_transfer: 'FT-1', usd_latest_fund_transfer: 'FT-2'};
 const context = {__: s => s, flt: (v, p) => p == null ? Number(v || 0) : Number(Number(v || 0).toFixed(p)),
  frappe: {session: {user: "Administrator"}, ui: {form: {on: (name, handlers) => {events[name] = handlers;}}},
   call: async () => ({message: preview}), throw: m => {throw new Error(m);}, msgprint() {},
   confirm: (_message, yes) => yes()}};
 vm.createContext(context); vm.runInContext(source, context);
 const frm = {doc: {docstatus: 0, branch: 'TEST', php_denominations: [{amount: 100000}], usd_denominations: [{amount: 99.75}]},
  set_df_property() {}, disable_save() {this.save_disabled = true;}, enable_save() {this.save_disabled = false;},
  set_value: async function(values, value) {
   if (typeof values === "string") values = {[values]: value};
   for (const [field, value] of Object.entries(values)) {
    if (this.doc[field] !== value) this.doc.__unsaved = 1;
   }
   Object.assign(this.doc, values);
  }, refresh_field() {}, is_new() {return false;},
  dashboard: {set_headline() {throw new Error('Unexpected blue notification');}}};
 return {context, frm, preview, events};
}
test('live PHP and USD variances preserve encoded cash', async () => {
 const {context:c, frm} = harness();
 await c.load_balance_preview(frm);
 assert.equal(frm.doc.php_variance, 0); assert.equal(frm.doc.usd_variance, -0.25);
 frm.doc.php_denominations[0].amount = 100089;
 await c.recalculate_parent(frm); assert.equal(frm.doc.php_variance, 89);
});
test('stale save is blocked until normal form refresh', async () => {
 const {context:c, frm, preview} = harness();
 await c.load_balance_preview(frm);
 preview.token = 'new'; preview.php_system_civ_balance = 200000;
 await assert.rejects(c.check_balance_preview(frm), /Refresh the form/);
 assert.equal(frm.doc.php_system_civ_balance, 100000);
 assert.equal(frm.doc.php_denominations[0].amount, 100000);
 await assert.rejects(c.check_balance_preview(frm), /Refresh the form/);
 await c.load_balance_preview(frm); await c.check_balance_preview(frm);
 assert.equal(frm.doc.php_variance, -100000);
});
test('opening report derives system balance from count', async () => {
 const {context:c, frm, preview} = harness(); preview.is_opening_position = true;
 await c.load_balance_preview(frm);
 assert.equal(frm.doc.php_system_civ_balance, 100000); assert.equal(frm.doc.usd_variance, 0);
});
test('failed preview cannot save', async () => {
 const {context:c, frm} = harness(); c.frappe.call = async () => {throw Error('offline');};
 await c.load_balance_preview(frm);
 await assert.rejects(c.check_balance_preview(frm), /Refresh the form/);
});
test('late response from previous branch is ignored', async () => {
 const {context:c, frm, preview} = harness(); let finish;
 c.frappe.call = () => new Promise(resolve => {finish = resolve;});
 const pending = c.load_balance_preview(frm);
 frm.doc.branch = 'OTHER'; finish({message: preview}); await pending;
 assert.equal(frm.doc._vault_balance_snapshot, undefined);
});
test('shortage confirmation can cancel submission', async () => {
 const {context:c, frm, events} = harness(); await c.load_balance_preview(frm);
 c.frappe.confirm = (message, _yes, no) => {assert.match(message, /Shortage 0.25/); no();};
 await assert.rejects(events['Vault Cash Position'].before_submit(frm), /cancelled/);
 assert.equal(c.frappe.validated, false);
});
test('submitted report is not recalculated', async () => {
 const {context:c, frm} = harness(); frm.doc.docstatus = 1; frm.doc.php_variance = 123;
 await c.load_balance_preview(frm); await c.recalculate_parent(frm);
 assert.equal(frm.doc.php_variance, 123);
});

test('post-save refresh preserves clean saved Draft and Submit eligibility', async () => {
 const {context:c, frm, events} = harness();
 await c.load_balance_preview(frm);
 // Simulate the saved server response: checkbox is numeric, transient token absent.
 frm.doc.is_opening_position = 0;
 frm.doc.__unsaved = 0;
 delete frm.doc._vault_balance_snapshot;
 await events['Vault Cash Position'].refresh(frm);
 assert.equal(frm.doc.__unsaved, 0);
 assert.equal(frm.doc.is_opening_position, 0);
 assert.equal(frm.doc._vault_balance_snapshot, 'original');
 await events['Vault Cash Position'].before_submit(frm);
 assert.equal(frm.doc.__unsaved, 0);
});
test('opening preview does not dirty a saved opening report', async () => {
 const {context:c, frm, preview, events} = harness();
 preview.is_opening_position = true;
 frm.doc.is_opening_position = 1;
 frm.doc.__unsaved = 0;
 await events['Vault Cash Position'].refresh(frm);
 assert.equal(frm.doc.__unsaved, 0);
 assert.equal(frm.doc.php_system_civ_balance, 100000);
 assert.equal(frm.doc.usd_system_civ_balance, 99.75);
 assert.equal(frm.doc.usd_variance, 0);
});
test('computed display updates never clear genuine unsaved edits', async () => {
 const {context:c, frm} = harness();
 frm.doc.__unsaved = 1;
 await c.load_balance_preview(frm);
 frm.doc.php_denominations[0].amount = 100089;
 await c.recalculate_parent(frm);
 assert.equal(frm.doc.__unsaved, 1);
 assert.equal(frm.doc.php_variance, 89);
});

test('unique branch is automatically assigned before loading balances', async () => {
 const {context:c, frm} = harness(); frm.doc.branch = '';
 c.frappe.call = async () => ({message: {allowed: true, administrator: false, branch: 'TEST'}});
 assert.equal(await c.initialize_vcp_branch(frm), true);
 assert.equal(frm.doc.branch, 'TEST'); assert.equal(frm.save_disabled, false);
});
test('invalid assignment aborts creation and routes back after prompt', async () => {
 for (const message of ['No branch assigned', 'Multiple branches assigned']) {
  const {context:c, frm} = harness(); let dialog = {}, route;
  c.frappe.call = async () => ({message: {allowed: false, message}});
  c.frappe.msgprint = () => dialog; c.frappe.set_route = (...args) => {route = args;};
  assert.equal(await c.initialize_vcp_branch(frm), false);
  assert.equal(frm.save_disabled, true); assert.equal(frm.doc.__unsaved, 0);
  dialog.onhide(); assert.equal(route[1], 'Vault Cash Position');
 }
});
test('Administrator may select branch manually without an assignment', async () => {
 const {context:c, frm} = harness(); frm.doc.branch = '';
 c.frappe.call = async () => ({message: {allowed: true, administrator: true, branch: null}});
 assert.equal(await c.initialize_vcp_branch(frm), true);
 assert.equal(frm.doc.branch, ''); assert.equal(frm.save_disabled, false);
});
test('failed assignment lookup leaves saving disabled', async () => {
 const {context:c, frm} = harness(); c.frappe.call = async () => {throw Error('offline');};
 assert.equal(await c.initialize_vcp_branch(frm), false); assert.equal(frm.save_disabled, true);
});
test('amendment with another branch is blocked without reassigning it', async () => {
 const {context:c, frm} = harness(); frm.doc.branch = 'ORIGINAL';
 c.frappe.call = async () => ({message: {allowed: true, administrator: false, branch: 'NEW'}});
 c.frappe.msgprint = () => ({});
 assert.equal(await c.initialize_vcp_branch(frm), false); assert.equal(frm.doc.branch, 'ORIGINAL');
});
test('assignment failure does not block another form opened later', async () => {
 const {context:c, frm} = harness();
 c.frappe.call = async () => ({message: {allowed: false, message: 'No assignment'}});
 c.frappe.msgprint = () => ({});
 await c.initialize_vcp_branch(frm);
 frm.doc = {docstatus: 0, branch: ''};
 c.frappe.call = async () => ({message: {allowed: true, administrator: false, branch: 'TEST'}});
 assert.equal(await c.initialize_vcp_branch(frm), true);
 assert.equal(frm.doc.branch, 'TEST'); assert.equal(frm.save_disabled, false);
});
