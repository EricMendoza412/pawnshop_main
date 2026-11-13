frappe.listview_settings['Models'] = {
    onload(listview) {
        if (frappe.session.user !== 'Administrator' && !frappe.user.has_role('Subastado member NJ')) return;
        const api = 'pawnshop_management.pawnshop_management.doctype.models.models.';
        const escape = value => frappe.utils.escape_html(String(value == null ? '' : value));
        listview.page.add_menu_item(__('Review Pending Price Changes'), () => {
            frappe.call({method: api + 'pending_price_changes', callback(r) {
                const rows = r.message || [];
                const columns = [['name', 'Model'], ['proposed_by', 'Proposer'], ['proposed_on', 'Proposed On'],
                    ['max_sell_price', 'Current Selling Price'], ['new_max_sell_price', 'New Selling Price'],
                    ['max_av_percent', 'Current AV %'], ['new_max_av_percent', 'New AV %'],
                    ['maximum', 'Current Maximum'], ['new_maximum', 'New Maximum'],
                    ['minimum', 'Current Minimum'], ['new_minimum', 'New Minimum'],
                    ['defective', 'Current Defective'], ['new_defective', 'New Defective'], ['maximum_difference', 'Difference']];
                const dialog = new frappe.ui.Dialog({title: __('Pending Price Changes'), size: 'extra-large',
                    fields: [{fieldname: 'review', fieldtype: 'HTML'}], primary_action_label: __('Approve Selected'),
                    primary_action() {
                        const selected = Array.from(dialog.fields_dict.review.$wrapper.find('input:checked')).map(el => rows[Number(el.value)]);
                        if (!selected.length || selected.length > 100) return frappe.msgprint(__('Select between 1 and 100 proposals.'));
                        frappe.confirm(__('Approve these reviewed proposals?') + '<ul>' + selected.map(row =>
                            `<li>${escape(row.name)}: ${escape(row.new_maximum)} / ${escape(row.new_minimum)} / ${escape(row.new_defective)}</li>`).join('') + '</ul>', () => {
                            frappe.call({method: api + 'approve_price_changes', args: {proposals: selected.map(row => ({name: row.name, modified: row.modified}))},
                                freeze: true, callback(result) {
                                    dialog.hide(); listview.refresh();
                                    frappe.msgprint((result.message || []).map(row => `${escape(row.name)}: ${row.approved ? __('Approved') : escape(row.reason)}`).join('<br>'));
                                }});
                        });
                    }});
                dialog.fields_dict.review.$wrapper.html(`<div style="overflow:auto;max-height:65vh"><table class="table table-bordered"><thead><tr><th></th>${columns.map(c => `<th>${__(c[1])}</th>`).join('')}</tr></thead><tbody>${rows.map((row, index) => {
                    const disabled = row.proposed_by === frappe.session.user && frappe.session.user !== 'Administrator';
                    return `<tr><td><input type="checkbox" value="${index}" ${disabled ? 'disabled title="Self-approval is not allowed"' : ''}></td>${columns.map(([key]) => `<td>${key === 'name' ? `<a href="/app/models/${encodeURIComponent(row.name)}" target="_blank" rel="noopener">${escape(row.name)}</a>` : escape(row[key])}</td>`).join('')}</tr>`;
                }).join('')}</tbody></table>${rows.length ? '' : __('No pending proposals.')}</div>`);
                dialog.show();
            }});
        });
    }
};
