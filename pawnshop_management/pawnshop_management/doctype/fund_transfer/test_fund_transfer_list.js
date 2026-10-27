const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
function harness(selected = '') {
 const context = {frappe: {listview_settings: {}}, __: value => value};
 vm.createContext(context);
 vm.runInContext(fs.readFileSync(`${__dirname}/fund_transfer_list.js`, 'utf8'), context);
 const metadata = {options: '\nDraft\nPending Cashier Approval\nPending Rover Confirmation\nSubmitted\nRejected\nCancelled\nImported Historical'};
 const originalOptions = metadata.options;
 let forwarded;
 const advanced = [];
 const field = {df: metadata, get_value: () => selected, set_options() {},
  async set_value(value) {selected = value;}};
 const area = {set_standard_filter(filters) {
  forwarded = filters;
  return {non_standard_filters: filters.filter(f => f[2] !== '='), promise: Promise.resolve()};
 }, async add(filters) {advanced.push(...this.set_standard_filter(filters).non_standard_filters);}};
 const list = {page: {fields_dict: {status: field}}, filter_area: area};
 return {context, list, field, metadata, originalOptions, advanced, forwarded: () => forwarded};
}
test('standard dropdown excludes legacy statuses without changing metadata', () => {
 const h = harness(); h.context.configure_fund_transfer_status_filter(h.list);
 assert.equal(h.field.df.options, '\nDraft\nSubmitted\nCancelled\nImported Historical');
 assert.equal(h.metadata.options, h.originalOptions);
});
test('legacy equality filters remain available as advanced filters', async () => {
 const h = harness(); h.context.configure_fund_transfer_status_filter(h.list);
 for (const status of ['Rejected', 'Pending Cashier Approval', 'Pending Rover Confirmation']) {
  const filter = ['Fund Transfer', 'status', '=', status];
  const result = h.list.filter_area.set_standard_filter([filter]); await result.promise;
  assert.equal(result.non_standard_filters[0], filter);
  assert.equal(h.forwarded().length, 0);
 }
});
test('current status filters and non-equality filters retain their behavior', () => {
 const h = harness(); h.context.configure_fund_transfer_status_filter(h.list);
 const filters = [['Fund Transfer', 'status', '=', 'Submitted'], ['Fund Transfer', 'status', '!=', 'Imported Historical']];
 const result = h.list.filter_area.set_standard_filter(filters);
 assert.equal(h.forwarded().length, 2);
 assert.equal(result.non_standard_filters[0], filters[1]);
});
test('existing legacy selection is preserved as an advanced filter', async () => {
 const h = harness('Rejected'); await h.context.configure_fund_transfer_status_filter(h.list);
 assert.equal(h.field.get_value(), '');
 assert.equal(h.advanced.length, 1);
 assert.equal(h.advanced[0][3], 'Rejected');
 const original = h.list.filter_area.set_standard_filter;
 h.context.configure_fund_transfer_status_filter(h.list);
 assert.equal(h.list.filter_area.set_standard_filter, original);
});
