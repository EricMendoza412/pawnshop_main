// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Models', {


	maximum: function(frm){
		frm.set_value('minimum', Math.ceil(frm.doc.maximum * 0.8 / 100) * 100);
		frm.set_value('defective', Math.ceil(frm.doc.maximum * 0.5 / 100) * 100);
	}

	// refresh: function(frm) {

	// }


});
