// Price approval is independent of the Model Status workflow.
(() => {
    const api = 'pawnshop_management.pawnshop_management.doctype.models.models.';
    const permitted = () => frappe.session.user === 'Administrator' || frappe.user.has_role('Subastado member NJ');
    // Keep workflow transitions intact while allowing the designated pricing role to save proposals.
    if (!frappe.workflow._models_price_access) {
        const original = frappe.workflow.is_read_only;
        frappe.workflow.is_read_only = function(doctype, name) {
            if (doctype === 'Models' && permitted()) return false;
            return original.call(this, doctype, name);
        };
        frappe.workflow._models_price_access = true;
    }
    function highlight_maximum_difference(frm) {
        const difference = Number(frm.doc.maximum_difference);
        const color = difference < 0 ? 'var(--red-600, #c92a2a)'
            : difference > 0 ? 'var(--green-600, #15803d)' : '';
        frm.fields_dict.maximum_difference.$wrapper
            .find('.control-value, .control-value *, input').css('color', color);
    }
    function preview(frm) {
        const price = Number(frm.doc.new_max_sell_price);
        const percent = Number(frm.doc.new_max_av_percent);
        if (!Number.isFinite(price) || price < 0 || !(percent > 0 && percent <= 100)) return;
        ['new_maximum', 'new_minimum', 'new_defective', 'maximum_difference'].forEach(f => frm.toggle_display(f, true));
        const maximum = Math.ceil(price * percent / 10000) * 100;
        frm.set_value({new_maximum: maximum, new_minimum: Math.ceil(maximum * .8 / 100) * 100,
            new_defective: Math.ceil(maximum * .6 / 100) * 100,
            maximum_difference: maximum - (frm.doc.maximum || 0)});
    }
    function actions(frm) {
        if (!permitted() || frm.is_new() || frm.is_dirty() || !frm.doc.pending_price_change_approval) return;
        const own = frm.doc.proposed_by === frappe.session.user;
        if (!own || frappe.session.user === 'Administrator') {
            frm.page.add_action_item(__('Approve Price Change'), () => {
                if (frm.is_dirty()) return frappe.msgprint(__('Save and review your changes first.'));
                frappe.confirm(__('Apply the reviewed proposed prices for this model?'), () =>
                    frappe.call({method: api + 'approve_price_change', args: {name: frm.doc.name, modified: frm.doc.modified},
                        freeze: true, callback: () => frm.reload_doc()}));
            });
        }
        if (own) frm.page.add_action_item(__('Withdraw Price Change'), () => {
            if (frm.is_dirty()) return frappe.msgprint(__('Save or discard your changes first.'));
            frappe.confirm(__('Withdraw this price proposal?'), () =>
                frappe.call({method: api + 'withdraw_price_change', args: {name: frm.doc.name, modified: frm.doc.modified},
                    freeze: true, callback: () => frm.reload_doc()}));
        });
    }
    frappe.ui.form.on('Models', {
        setup(frm) {
            // Frappe rebuilds the Actions menu asynchronously for workflows.
            if (frm.states && !frm.states._price_actions) {
                const original = frm.states.show_actions;
                frm.states.show_actions = function() {
                    original.apply(this, arguments);
                    frappe.after_ajax().then(() => actions(frm));
                };
                frm.states._price_actions = true;
            }
        },
        refresh(frm) {
            const editable = permitted() && (!frm.doc.pending_price_change_approval || frm.doc.proposed_by === frappe.session.user);
            const showing = !!frm.doc.pending_price_change_approval || frm.is_new();
            ['new_max_sell_price', 'new_max_av_percent'].forEach(f => {
                frm.set_df_property(f, 'read_only', !editable);
                frm.toggle_display(f, showing);
            });
            ['new_maximum', 'new_minimum', 'new_defective', 'maximum_difference'].forEach(f => frm.toggle_display(f, showing));
            if (!frm.doc.has_approved_pricing) frm.dashboard.set_headline_alert(__('Initial pricing awaiting approval'), 'orange');
            if (editable && !frm.doc.pending_price_change_approval && !frm.is_new()) {
                frm.add_custom_button(__('Propose Price Change'), () => {
                    ['new_max_sell_price', 'new_max_av_percent'].forEach(f => frm.toggle_display(f, true));
                    frm.set_value({
                        new_max_sell_price: frm.doc.max_sell_price || 0,
                        new_max_av_percent: frm.doc.max_av_percent > 0 ? frm.doc.max_av_percent : 80
                    }).then(() => preview(frm));
                });
            }
            if (!frappe.workflow.get_state_fieldname('Models')) actions(frm);
            highlight_maximum_difference(frm);
        },
        maximum_difference: highlight_maximum_difference,
        new_max_sell_price: preview,
        new_max_av_percent: preview
    });
})();
