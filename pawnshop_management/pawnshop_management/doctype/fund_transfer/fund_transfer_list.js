frappe.listview_settings["Fund Transfer"] = {
	filters: [["status", "!=", "Imported Historical"]],
	onload(listview) {
		listview.page.add_inner_button(__("Operational Transfers"), () => {
			listview.filter_area.clear().then(() => {
				listview.filter_area.add([["Fund Transfer", "status", "!=", "Imported Historical"]]);
			});
		}, __("View"));
		listview.page.add_inner_button(__("Imported Historical"), () => {
			listview.filter_area.clear().then(() => {
				listview.filter_area.add([["Fund Transfer", "status", "=", "Imported Historical"]]);
			});
		}, __("View"));
		frappe.call({
			method: "pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.get_current_branch_context",
			callback(response) {
				const context = response.message || {};
				if (!context.unrestricted && !context.branch && !listview.__branch_ip_warning_shown) {
					listview.__branch_ip_warning_shown = true;
					frappe.msgprint({
						title: __("Branch Not Determined"),
						indicator: "orange",
						message: __("Your current IP address is not mapped to a branch. Fund Transfers are hidden until Branch IP Addressing is corrected."),
					});
				}
			},
		});
	},
	get_indicator(doc) {
		if (doc.status === "Imported Historical") {
			return [__("Imported Historical"), "gray", "status,=,Imported Historical"];
		}
		if (doc.status === "Submitted") {
			return [__("Submitted"), "green", "status,=,Submitted"];
		}
		if (["Pending Cashier Approval", "Pending Rover Confirmation"].includes(doc.status)) {
			return [__(doc.status), "orange", `status,=,${doc.status}`];
		}
		if (["Rejected", "Cancelled"].includes(doc.status)) {
			return [__(doc.status), "red", `status,=,${doc.status}`];
		}
		return [__(doc.status || "Draft"), "gray", `status,=,${doc.status || "Draft"}`];
	},
};
