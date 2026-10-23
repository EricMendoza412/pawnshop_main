// Run with: node pawnshop_management/pawnshop_management/doctype/fund_transfer/test_fund_transfer.js
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(`${__dirname}/fund_transfer.js`, 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));

function harness() {
	let events, dialog, ajaxComplete;
	const context = {
		__: text => text, document: {},
		$: () => ({ off() { return this; }, on(_name, fn) { ajaxComplete = fn; return this; } }),
		frappe: {
			session: { user: 'cashier@example.com' }, dom: { unfreeze() {} },
			throw(message) { throw new Error(message); },
			ui: { form: { on(_doctype, handlers) { events = handlers; } },
				Dialog: class {
					constructor(options) { Object.assign(this, options); dialog = this; }
					show() {}
					hide() { this.onhide(); }
					set_value() {}
				} },
			call: async () => ({ message: { branches: ['TEST'], transfers: [{
				transfer_type: 'Pawnshop (-NCB) to Vault', authorization: 'cashier',
				confirmer: 'vc@example.com', confirmer_label: 'Vault Custodian',
			}] } }),
		},
	};
	vm.createContext(context); vm.runInContext(source, context);
	const properties = {};
	const frm = {
		doc: { name: 'TEST-000001', branch: 'TEST', currency: 'PHP', amount: 100,
			status: 'Draft', docstatus: 0, transfer_type: 'Pawnshop (-NCB) to Vault' },
		selected_workflow_action: 'Submit', is_new: () => false,
		set_query() {}, toggle_display() {},
		disable_save() { this.saveDisabled = true; }, enable_save() { this.saveDisabled = false; },
		dashboard: { set_headline_alert(message) { this.message = message; }, clear_headline() { this.message = null; } },
		set_df_property(field, property, value) { properties[`${field}.${property}`] = value; },
		set_value(field, value) { this.doc[field] = value; },
	};
	events.setup(frm);
	return { context, events, frm, properties, dialog: () => dialog,
		complete: () => ajaxComplete(null, {}, { url: '/api/method/frappe.model.workflow.apply_workflow' }) };
}

test('cashier receipt prompts for the fixed VC and sends credentials only on submission', async () => {
	const h = harness();
	const pending = h.events.before_workflow_action(h.frm);
	await tick();
	const confirmer = h.dialog().fields.find(f => f.fieldname === 'confirmer');
	assert.equal(confirmer.default, 'vc@example.com');
	assert.equal(confirmer.read_only, 1);
	assert.equal(h.dialog().fields.find(f => f.fieldname === 'amount').default, 100);
	h.dialog().primary_action({ password: 'secret' });
	await pending;
	assert.equal(h.frm.doc.confirmation_password, 'secret');
	assert.equal(h.frm.doc.__unsaved, undefined);
	h.complete(); // Also fired for failed workflow requests.
	assert.equal(h.frm.doc.confirmation_password, null);
});

test('cancelling confirmation rejects submission and leaves no password', async () => {
	const h = harness();
	const pending = h.events.before_workflow_action(h.frm);
	const rejected = assert.rejects(pending, /cancelled/);
	await tick();
	h.dialog().hide();
	await rejected;
	assert.equal(h.frm.doc.confirmation_password, null);
});

test('new entry options come from assignments and exclude the retired type', async () => {
	const h = harness();
	await h.context.set_transfer_type_options(h.frm);
	assert.equal(h.properties['transfer_type.options'], 'Pawnshop (-NCB) to Vault');
});

test('historical Cash Manager to Vault retains its displayed type', async () => {
	const h = harness();
	h.frm.doc.status = 'Submitted'; h.frm.doc.docstatus = 1;
	h.frm.doc.transfer_type = 'Cash Manager to Vault';
	await h.context.set_transfer_type_options(h.frm);
	assert.equal(h.frm.doc.transfer_type, 'Cash Manager to Vault');
	assert.equal(h.properties['transfer_type.options'], undefined);
});

test('Rover transfers still request a Rover selection and password', async () => {
	const h = harness(); h.frm.doc.transfer_type = 'Rover to Vault';
	const pending = h.events.before_workflow_action(h.frm);
	await tick();
	assert.equal(h.dialog().fields.find(f => f.fieldname === 'rover').reqd, 1);
	h.dialog().primary_action({ rover: 'rover@example.com', password: 'secret' });
	await pending;
	assert.equal(h.frm.doc.rover, 'rover@example.com');
	assert.equal(h.frm.doc.rover_password, 'secret');
	h.complete();
	assert.equal(h.frm.doc.rover_password, null);
});


test('closed day blocks cashier and Rover submission before any password dialog', async () => {
	for (const type of ['Pawnshop (-NCB) to Vault', 'Rover to Vault']) {
		const h = harness();
		h.frm.doc.transfer_type = type;
		h.context.frappe.call = async () => ({ message: { branches: ['TEST'], transfers: [],
			closed_position: 'VCP-TEST', closure_message: 'Fund transfers are closed for TEST' } });
		await assert.rejects(h.events.before_workflow_action(h.frm), /Fund transfers are closed/);
		assert.equal(h.dialog(), undefined);
		assert.equal(h.frm.saveDisabled, true);
	}
});

test('refreshing after VCP cancellation re-enables the form', async () => {
	const h = harness();
	h.context.show_day_closure(h.frm, { closed_position: 'VCP-TEST', closure_message: 'Closed' });
	assert.equal(h.frm.saveDisabled, true);
	h.context.show_day_closure(h.frm, { closed_position: null });
	assert.equal(h.frm.saveDisabled, false);
	assert.equal(h.frm.dashboard.message, null);
});
