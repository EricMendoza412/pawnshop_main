/* eslint-disable */

var default_branch = "";

frappe.call({
	method: "pawnshop_management.pawnshop_management.report.vc_count_consolidated.vc_count_consolidated.get_default_branch",
	callback: function(data) {
		if (data.message) {
			default_branch = data.message;
			if (frappe.query_report && frappe.query_report.get_filter_value("branch") !== default_branch) {
				frappe.query_report.set_filter_value("branch", default_branch);
			}
		}
	}
});

const date = new Date();
let day = String(date.getDate()).padStart(2, "0");
let month = String(date.getMonth() + 1).padStart(2, "0");
let year = date.getFullYear();
let currentDate = `${year}-${month}-${day}`;

let is_allowed = frappe.user_roles.includes("Auditor") || frappe.user_roles.includes("Administrator");

if (is_allowed) {
	frappe.query_reports["VC Count Consolidated"] = {
		filters: [
			{
				fieldname: "date",
				label: __("Date"),
				fieldtype: "Date",
				default: currentDate
			},
			{
				fieldname: "branch",
				label: __("Branch"),
				fieldtype: "Select",
				options: [
					"Garcia's Pawnshop - CC",
					"Garcia's Pawnshop - GTC",
					"Garcia's Pawnshop - MOL",
					"Garcia's Pawnshop - POB",
					"Garcia's Pawnshop - TNZ",
					"Garcia's Pawnshop - BUC",
					"Garcia's Pawnshop - NOV",
					"Garcia's Pawnshop - PSC",
					"TEST"
				],
				default: default_branch
			}
		]
	};
} else {
	frappe.query_reports["VC Count Consolidated"] = {
		filters: [
			{
				fieldname: "date",
				label: __("Date"),
				fieldtype: "Date",
				default: currentDate
			},
			{
				fieldname: "branch",
				label: __("Branch"),
				fieldtype: "Read Only",
				default: default_branch
			}
		]
	};
}
