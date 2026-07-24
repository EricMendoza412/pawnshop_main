// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt


function calculate_maximum(frm) {
    const sellingPrice = Number(frm.doc.max_sell_price) || 0;
    const enteredPercentage = Number(frm.doc.max_av_percent);
    const percentage = enteredPercentage > 0 ? enteredPercentage : 80;

    return Math.ceil((sellingPrice * percentage) / 10000) * 100;
}

frappe.ui.form.on('Models', {

    maximum: function(frm) {

        if (frm.doc.maximum > 0) {
            frm.set_value('minimum', Math.ceil(frm.doc.maximum * 0.8 / 100) * 100);
            frm.set_value('defective', Math.ceil(frm.doc.maximum * 0.6 / 100) * 100);
        }
    },

    max_sell_price: function(frm) {

        frm.set_value('last_srp_update', frappe.datetime.get_today());

        frm.set_value('maximum', calculate_maximum(frm));
    },

	max_av_percent: function(frm) {

        frm.set_value('maximum', calculate_maximum(frm));
	},

	defective_value: function(frm) {
		const rawValue = Number(frm.doc.defective_value);
		if (Number.isNaN(rawValue)) {
			return;
		}

		const rounded = Math.round(rawValue / 100) * 100;
		if (rounded !== rawValue) {
			frm.set_value('defective_value', rounded);
		}
	}

    // refresh: function(frm) {

    // }

});
