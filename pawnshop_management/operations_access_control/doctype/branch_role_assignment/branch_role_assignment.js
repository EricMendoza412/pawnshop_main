frappe.ui.form.on("Branch Role Assignment", {
	setup(frm) {
		frm.set_query("assigned_user", () => ({
			filters: {
				enabled: 1,
			},
		}));
	},

	refresh(frm) {
		if (frm.is_new() && !frm.doc.branch) {
			frappe.call({
				method: "pawnshop_management.pawnshop_management.custom_codes.get_ip.get_ip",
				callback(data) {
					frappe.db.get_list("Branch IP Addressing", {
						filters: {
							ip_address: data.message,
						},
						fields: ["name"],
						limit: 1,
					}).then((records) => {
						if (records && records.length && !frm.doc.branch) {
							frm.set_value("branch", records[0].name);
						}
					});
				},
			});
		}

		set_date_editability(frm);
	},
});

function set_date_editability(frm) {
	frm.set_df_property("date", "read_only", frm.is_new() ? 0 : 1);
}
