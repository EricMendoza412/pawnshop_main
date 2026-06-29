frappe.ui.form.on("Branch", {
	refresh(frm) {
		if (frappe.session.user !== "Administrator") {
			return;
		}

		frm.meta.fields.forEach((field) => {
			if (field.fieldname && !["Section Break", "Column Break", "Tab Break"].includes(field.fieldtype)) {
				frm.set_df_property(field.fieldname, "read_only", 0);
			}
		});
	},
});
