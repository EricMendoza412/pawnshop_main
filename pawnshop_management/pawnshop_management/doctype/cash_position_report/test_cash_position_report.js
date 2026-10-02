// Run with: node pawnshop_management/pawnshop_management/doctype/cash_position_report/test_cash_position_report.js
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(`${__dirname}/cash_position_report.js`, 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
	let resolve, reject;
	const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
	return { promise, resolve, reject };
}

function harness(overrides = {}) {
	const requests = [], overlays = [], messages = [], writes = [];
	let events;
	const context = {
		__: text => text,
		flt: value => Number.parseFloat(value) || 0,
		console: { error() {} },
		frappe: {
			ui: { form: { on(doctype, handlers) { events = handlers; } } },
			dom: { freeze(message) { overlays.push(message); }, unfreeze() { overlays.push('unfreeze'); } },
			msgprint(message) { messages.push(message); return {}; },
			user_roles: [], datetime: { now_datetime: () => '2026-10-02 09:00:00' }, show_alert() {},
			throw(message) { throw new Error(message); },
			call(method, args) {
				if (typeof method === 'object') { args = method.args; method = method.method; }
				requests.push({ method, args });
				return Promise.resolve().then(() => overrides.call ? overrides.call(method, args) : defaultCall(method));
			},
			db: { get_list(doctype, options) {
				requests.push({ doctype, options });
				return Promise.resolve().then(() => overrides.list ? overrides.list(doctype, options) : []);
			} }
		}
	};
	function defaultCall(method) {
		if (method.endsWith('get_cash_position_report_create_access')) return { message: { allowed: true, branch: 'TEST' } };
		if (method.endsWith('get_pawnshop_fund_transfer_totals')) return { message: { cash_from_vault: 100, cash_to_vault: 50 } };
		if (method.endsWith('get_latest_cpr')) return { message: 2000 };
		return { message: 1000 };
	}
	vm.createContext(context);
	vm.runInContext(source, context);
	const buttons = new Map();
	const frm = {
		doc: { name: 'new-cpr', docstatus: 0, branch: 'TEST', date: '2026-10-02', one_thousand_php_bills: 2000 },
		is_new: () => overrides.isNew !== false,
		disable_save() { this.saveEnabled = false; }, enable_save() { this.saveEnabled = true; },
		refresh_field() {}, toggle_enable() {},
		add_custom_button(label, action) { buttons.set(label, action); },
		remove_custom_button(label) { buttons.delete(label); },
		async set_value(field, value) {
			const values = typeof field === 'object' ? field : { [field]: value };
			for (const [key, amount] of Object.entries(values)) {
				if (this.doc[key] === amount) continue;
				this.doc[key] = amount;
				writes.push({ key, amount });
				if (events[key]) await events[key](this);
			}
		}
	};
	return { context, frm, events, requests, overlays, messages, buttons, writes, defaultCall };
}

function receipt(mode, total, gcash, bank) {
	return { mode_of_payment: mode, total, gcash_amount_payment: gcash, bank_payment: bank };
}

test('payment modes count only the intended full or split amounts', async () => {
	const h = harness({ list: () => [
		receipt('GCash', '1000', 1000, 900),
		receipt('Bank Transfer', '2000', 800, 2000),
		receipt('Cash & GCash', 1000, 400, 900),
		receipt('Cash & Bank Transfer', 1000, 800, 300),
		receipt('GCash & Bank Transfer', 1000, 600, 400),
		receipt('Cash', 1000, 999, 999), receipt('-Select-', 1000, 999, 999),
		receipt('Cash & GCash', 0, null, null)
	] });
	const totals = await h.context.get_pr_mops({ branch: 'TEST', date: '2026-10-02' });
	assert.equal(totals.gcash, 2000);
	assert.equal(totals.bank_transfer, 2700);
});

test('initial branch/date triggers share one load; repeat loads replace totals', async () => {
	const pending = deferred();
	const h = harness({ list: (doctype) => doctype === 'Provisional Receipt' ? pending.promise : [] });
	const first = h.events.onload(h.frm);
	assert.strictEqual(h.events.branch(h.frm), first);
	assert.strictEqual(h.events.date(h.frm), first);
	await tick();
	assert.deepEqual(h.overlays, ['Loading data']);
	assert.equal(h.frm.saveEnabled, false);
	pending.resolve([receipt('GCash', 1000, 1000, 0)]);
	await first;
	assert.equal(h.frm.doc.gcash, 1000);
	assert.equal(h.frm.doc.total_out, 3050);
	assert.equal(h.frm.doc.total_in, 1100);
	assert.equal(h.frm.doc.ending_balance, 50);
	assert.equal(h.frm.doc.shortage_overage, 1950);
	assert.equal(h.frm.saveEnabled, true);
	assert.deepEqual(h.overlays, ['Loading data', 'unfreeze']);
	await h.events.branch(h.frm);
	assert.equal(h.frm.doc.gcash, 1000);
	assert.equal(h.requests.filter(r => r.doctype === 'Provisional Receipt').length, 2);
});

test('sales contributions, exclusions, and returns retain their behavior', async () => {
	const h = harness({ list: doctype => doctype === 'Subastado Sales Commissions' ? [
		{ mop_1: 'Gcash', payment_1: 200, mop_2: 'BDO', payment_2: 300 },
		{ mop_1: 'Gcash', payment_1: -40, mop_2: 'BPI', payment_2: -60 },
		{ mop_1: 'Cash', payment_1: 100 },
		{ mop_1: 'Gcash', payment_1: 9999, comments: 'Subasta' }
	] : doctype === 'Provisional Receipt' ? [receipt('GCash & Bank Transfer', 1000, 400, 600)] : [] });
	await h.context.load_cash_position_report(h.frm);
	assert.equal(h.frm.doc.gcash, 600);
	assert.equal(h.frm.doc.bank_transfer, 900);
	assert.equal(h.frm.doc.gcash_positive, 40);
	assert.equal(h.frm.doc.bank_transfer_return, 60);
	assert.equal(h.frm.doc.selling, 500);
});

test('branch/date changes discard stale results and remain frozen through the latest load', async () => {
	const old = deferred(), latest = deferred();
	const h = harness({ list: (doctype, options) => {
		if (doctype !== 'Provisional Receipt') return [];
		return options.filters.branch === 'TEST' ? old.promise : latest.promise;
	} });
	const loading = h.context.load_cash_position_report(h.frm);
	await tick();
	h.frm.doc.branch = 'OTHER';
	h.frm.doc.date = '2026-10-03';
	assert.strictEqual(h.events.branch(h.frm), loading);
	assert.strictEqual(h.events.date(h.frm), loading);
	old.resolve([receipt('GCash', 9999, 0, 0)]);
	await tick();
	assert.equal(h.frm.doc.gcash, undefined);
	assert.deepEqual(h.overlays, ['Loading data']);
	const latestQuery = h.requests.find(r => r.doctype === 'Provisional Receipt' && r.options.filters.branch === 'OTHER');
	assert.equal(latestQuery.options.filters.date_issued, '2026-10-03');
	latest.resolve([receipt('GCash', 700, 0, 0)]);
	await loading;
	assert.equal(h.frm.doc.gcash, 700);
	assert.equal(h.writes.some(r => r.key === 'gcash' && r.amount === 9999), false);
	assert.deepEqual(h.overlays, ['Loading data', 'unfreeze']);
});

test('overlay waits for nested pawn lookups and their final calculations', async () => {
	const jewelry = deferred(), nonJewelry = deferred();
	const h = harness({ list: (doctype, options) => {
		if (doctype === 'Pawn Ticket Jewelry') return [{ pawn_ticket: 'J', item_series: 'A', net_proceeds: 500 }];
		if (doctype === 'Pawn Ticket Non Jewelry') return [{ pawn_ticket: 'NJ', net_proceeds: 600 }];
		if (options.filters.pawn_ticket_no === 'J') return jewelry.promise;
		if (options.filters.pawn_ticket_no === 'NJ') return nonJewelry.promise;
		return [];
	} });
	const loading = h.context.load_cash_position_report(h.frm);
	await tick();
	jewelry.resolve([{ principal_amount: 800, interest: 100 }]);
	await tick();
	assert.deepEqual(h.overlays, ['Loading data']);
	assert.equal(h.frm.doc.jewelry_a, undefined);
	nonJewelry.resolve([]);
	await loading;
	assert.equal(h.frm.doc.jewelry_a, 700);
	assert.equal(h.frm.doc.non_jewelry, 600);
	assert.deepEqual(h.overlays, ['Loading data', 'unfreeze']);
});

test('failure waits for outstanding nested requests, prevents saving, and allows a full retry', async () => {
	const slow = deferred();
	let failing = true;
	const h = harness({ list: (doctype, options) => {
		if (doctype === 'Subastado Sales Commissions' && failing) throw new Error('Network failure');
		if (doctype === 'Pawn Ticket Jewelry' && failing) return [{ pawn_ticket: 'J', item_series: 'B' }];
		if (options.filters.pawn_ticket_no === 'J') return slow.promise;
		return [];
	} });
	const loading = h.context.load_cash_position_report(h.frm);
	await tick();
	assert.deepEqual(h.overlays, ['Loading data']);
	slow.resolve([]);
	await loading;
	assert.equal(h.frm.doc.gcash, undefined);
	assert.equal(h.frm.saveEnabled, false);
	assert.equal(h.frm.__cpr_load_failed, true);
	assert.deepEqual(h.overlays, ['Loading data', 'unfreeze']);
	await assert.rejects(h.events.validate(h.frm), /finish loading successfully/);
	assert.ok(h.buttons.has('Retry Loading Data'));
	failing = false;
	await h.context.load_cash_position_report(h.frm, true);
	assert.equal(h.frm.doc.gcash, 0);
	assert.equal(h.frm.saveEnabled, true);
	assert.equal(h.frm.__cpr_load_failed, false);
	assert.equal(h.buttons.has('Retry Loading Data'), false);
});

test('access check and automatic branch assignment remain inside one frozen load', async () => {
	const access = deferred();
	const h = harness({ call: method => method.endsWith('get_cash_position_report_create_access') ? access.promise : h.defaultCall(method) });
	h.frm.doc.branch = '';
	const loading = h.events.onload(h.frm);
	await tick();
	assert.equal(h.requests.length, 1);
	assert.deepEqual(h.overlays, ['Loading data']);
	access.resolve({ message: { allowed: true, branch: 'TEST' } });
	await loading;
	assert.equal(h.frm.doc.branch, 'TEST');
	assert.equal(h.frm.saveEnabled, true);
	assert.deepEqual(h.overlays, ['Loading data', 'unfreeze']);
});

test('access denial releases overlay without loading report or enabling save', async () => {
	const h = harness({ call: () => ({ message: { allowed: false, message: 'Denied' } }) });
	await h.events.onload(h.frm);
	assert.equal(h.requests.length, 1);
	assert.equal(h.frm.saveEnabled, false);
	assert.deepEqual(h.overlays, ['Loading data', 'unfreeze']);
});

test('saved draft refresh preserves historical GCash and submitted refresh makes no requests', async () => {
	const h = harness({ isNew: false });
	h.frm.doc.gcash = 555;
	h.frm.doc.bank_transfer = 666;
	await h.events.refresh(h.frm);
	assert.equal(h.frm.doc.gcash, 555);
	assert.equal(h.frm.doc.bank_transfer, 666);
	assert.equal(h.requests.length, 1);
	h.frm.doc.docstatus = 1;
	await h.events.refresh(h.frm);
	assert.equal(h.requests.length, 1);
});


test('overlay also waits for asynchronous field updates before enabling save', async () => {
	const update = deferred();
	const h = harness();
	const setValue = h.frm.set_value.bind(h.frm);
	h.frm.set_value = async (field, value) => {
		if (field === 'shortage_overage') await update.promise;
		return setValue(field, value);
	};
	const loading = h.context.load_cash_position_report(h.frm);
	await tick();
	assert.deepEqual(h.overlays, ['Loading data']);
	assert.equal(h.frm.saveEnabled, false);
	await assert.rejects(h.events.validate(h.frm), /finish loading successfully/);
	update.resolve();
	await loading;
	assert.equal(h.frm.saveEnabled, true);
	assert.deepEqual(h.overlays, ['Loading data', 'unfreeze']);
});

test('discard results when the form switches to another document', async () => {
	const pending = deferred();
	const h = harness({ list: doctype => doctype === 'Provisional Receipt' ? pending.promise : [] });
	const loading = h.context.load_cash_position_report(h.frm);
	await tick();
	h.frm.doc = { name: 'saved-report', branch: 'OTHER', date: '2026-10-01', docstatus: 1, gcash: 123 };
	pending.resolve([receipt('GCash', 9999, 0, 0)]);
	await loading;
	assert.equal(h.frm.doc.gcash, 123);
	assert.deepEqual(h.overlays, ['Loading data', 'unfreeze']);
});
