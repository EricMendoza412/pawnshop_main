// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt


frappe.ui.form.on('Models', {

    maximum: function(frm) {

        if (frm.doc.maximum > 0) {
            frm.set_value('minimum', Math.ceil(frm.doc.maximum * 0.8 / 100) * 100);
            frm.set_value('defective', Math.ceil(frm.doc.maximum * 0.6 / 100) * 100);
        }
    },

    max_sell_price: function(frm) {

		frm.set_value('last_srp_update', frappe.datetime.get_today());

        if (frm.doc.max_sell_price > 0 && frm.doc.max_av_percent > 0) {
            frm.set_value('maximum', Math.ceil(frm.doc.max_sell_price * (frm.doc.max_av_percent * 0.01) / 100) * 100);
        }else{
			frm.set_value('maximum', Math.ceil(frm.doc.max_sell_price * (80 * 0.01) / 100) * 100);
		}
    },

	max_av_percent: function(frm) {

        if (frm.doc.max_sell_price > 0 && frm.doc.max_av_percent > 0) {
            frm.set_value('maximum', Math.ceil(frm.doc.max_sell_price * (frm.doc.max_av_percent * 0.01) / 100) * 100);
        }else{
			frm.set_value('maximum', Math.ceil(frm.doc.max_sell_price * (80 * 0.01) / 100) * 100);
		}
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
