// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Models', {


	maximum: function(frm){
		frm.set_value('minimum', frm.doc.maximum * 0.8);
		frm.set_value('defective', frm.doc.maximum * 0.5);
	}

	// refresh: function(frm) {

	// }


});
