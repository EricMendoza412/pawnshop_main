const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');

function harness({ reject = false, newDocument = true } = {}) {
	const handlers = {};
	let calls = 0;
	const context = {
		__: value => value,
		frappe: {
			ui: { form: { on: (doctype, events) => { handlers[doctype] = events; } } },
			user: { has_role: () => true },
			session: { user: 'custodian@example.com' },
			datetime: { nowdate: () => '2026-11-09' },
			call: () => {
				calls++;
				// Match the legacy jqXHR contract: thenable, but no catch method.
				const deferred = { then(resolve, fail) {
					queueMicrotask(() => {
						if (reject) fail(new Error('Multiple custodian assignments'));
						else resolve({ message: { origin: 'Bulk NJ', transfer_no: 'BN-1' } });
					});
					return deferred;
				} };
				return deferred;
			}
		}
	};
	vm.runInNewContext(fs.readFileSync(`${__dirname}/transfer_tracker.js`, 'utf8'), context);
	const frm = {
		doc: { docstatus: 0 },
		is_new: () => newDocument,
		set_df_property() {}, refresh_field() {},
		set_value(field, value) {
			if (typeof field === 'object') Object.assign(this.doc, field);
			else this.doc[field] = value;
			return Promise.resolve();
		},
		disable_save() { this.save_disabled = true; },
		enable_save() { this.save_disabled = false; },
		set_intro(message) { this.intro = message; }
	};
	return { frm, load: () => handlers['Transfer Tracker'].onload(frm), calls: () => calls };
}

test('new transfer initializes using a legacy Deferred without catch', async () => {
	const h = harness();
	assert.doesNotThrow(h.load);
	assert.equal(h.frm.save_disabled, true);
	await new Promise(setImmediate);
	assert.equal(h.frm.doc.origin, 'Bulk NJ');
	assert.equal(h.frm.doc.transfer_no, 'BN-1');
	assert.equal(h.frm.doc.item_type, 'Non Jewelry Items');
	assert.equal(h.frm.doc.transfer_type, 'Transfer of Display Items');
	assert.equal(h.frm.doc.released_by, 'custodian@example.com');
	assert.equal(h.frm.save_disabled, false);
});

test('assignment rejection keeps saving disabled and displays an explanation', async () => {
	const h = harness({ reject: true });
	assert.doesNotThrow(h.load);
	await new Promise(setImmediate);
	assert.equal(h.frm.doc.origin, undefined);
	assert.equal(h.frm.save_disabled, true);
	assert.match(h.frm.intro, /Transfer stopped/);
});

test('existing transfers do not request new defaults', () => {
	const h = harness({ newDocument: false });
	h.frm.doc.origin = 'Subastado NJ';
	h.load();
	assert.equal(h.calls(), 0);
	assert.equal(h.frm.doc.origin, 'Subastado NJ');
});
