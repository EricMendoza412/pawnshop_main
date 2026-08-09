frappe.ui.form.on("Fund Transfer Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Retry Failed UAT Sync"), () => {
			frappe.call({
				method: "pawnshop_management.pawnshop_management.fund_transfer_google.retry_google_uat_sync",
				freeze: true,
				callback() {
					frappe.show_alert({ message: __("Retry jobs queued"), indicator: "green" });
				},
			});
		});
	},
});
