// Run with node test_branch_options.js; no browser or network access required.
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const requests = [];
const handlers = {};
const context = {
	__: value => value,
	frappe: {
		ui: {form: {on: (doctype, events) => { handlers[doctype] = events; }}},
		call: options => requests.push(options)
	}
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, 'text_blast.js'), 'utf8'), context);
function form() {
	return {
		doc: {name: 'first', workflow_state: 'Draft', recipient_options: 'Branch A', recipient_list: [{contact_name: 'Customer'}]},
		metadata: {}, buttons: {}, clears: 0,
		set_df_property(field, property, value) { this.metadata[property] = value; },
		refresh_field() {},
		add_custom_button(label, callback) { this.buttons[label] = callback; },
		remove_custom_button(label) { delete this.buttons[label]; },
		clear_table() { this.clears++; }
	};
}
const frm = form();
context.load_branch_options(frm);
assert(frm.metadata.description.includes('Loading branches...'));
context.load_branch_options(frm);
assert.equal(requests.length, 1, 'Concurrent refreshes reuse the in-flight request');
// Navigation while the request is pending must populate the active document.
frm.doc.name = 'second';
frm.metadata = {};
requests.shift().callback({message: ['Branch A', 'Branch B']});
assert.equal(frm.metadata.options, '\nBranch A\nBranch B');
assert.equal(frm.doc.recipient_options, 'Branch A');
assert.equal(frm.doc.recipient_list.length, 1);
assert.equal(frm.clears, 0);
assert(!frm.metadata.description.includes('Loading branches...'));
frm.metadata = {};
frm.doc.name = 'third';
frm.doc.recipient_options = 'Archived Branch';
context.load_branch_options(frm);
assert.equal(requests.length, 0, 'Navigation reapplies cached options without another request');
assert(frm.metadata.options.includes('Archived Branch'));
assert.equal(frm.doc.recipient_options, 'Archived Branch');
frm.text_blast_applying_branch_options = true;
handlers['Text Blast'].recipient_options(frm);
assert.equal(frm.clears, 0, 'Applying options must not clear recipients');

const retry = form();
context.load_branch_options(retry);
requests.shift().error();
assert.equal(retry.text_blast_branches_loading, false);
assert(retry.metadata.description.includes('Unable to load branches'));
assert(retry.buttons['Retry Loading Branches']);
retry.buttons['Retry Loading Branches']();
assert.equal(requests.length, 1);
requests.shift().callback({message: ['Branch A']});
assert.equal(retry.metadata.options, '\nBranch A');
assert(!retry.buttons['Retry Loading Branches']);

for (const response of [{exc: 'Failure'}, {}, {message: []}, {message: [null]}]) {
	const invalid = form();
	context.load_branch_options(invalid);
	requests.shift().callback(response);
	assert(invalid.buttons['Retry Loading Branches']);
	assert.equal(invalid.text_blast_branch_options, undefined);
	assert.equal(invalid.doc.recipient_options, 'Branch A');
	assert.equal(invalid.doc.recipient_list.length, 1);
}
console.log('Branch loading tests passed: navigation, caching, in-flight reuse, preservation, failure and retry.');
