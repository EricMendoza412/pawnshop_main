frappe.listview_settings["Fund Transfer"] = {
	filters: [["status", "!=", "Imported Historical"]],
	onload(listview) {
		configure_fund_transfer_status_filter(listview);
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

function configure_fund_transfer_status_filter(listview) {
	const field = listview.page.fields_dict.status;
	const area = listview.filter_area;
	if (!field || area.__fund_transfer_status_configured) return;
	area.__fund_transfer_status_configured = true;
	const legacy = new Set(["Pending Cashier Approval", "Pending Rover Confirmation", "Rejected"]);
	const selected = field.get_value();
	// Change only this list control, never the DocType metadata used by advanced filters.
	field.df = Object.assign({}, field.df, {
		options: "\nDraft\nSubmitted\nCancelled\nImported Historical",
	});
	field.set_options();
	// Frappe normally moves equality filters into the standard dropdown. Keep
	// legacy values in advanced filters instead, including saved/route filters.
	const original = area.set_standard_filter;
	area.set_standard_filter = function(filters) {
		const historical = [], standard = [];
		filters.forEach(filter => {
			const [doctype, fieldname, operator, value] = filter;
			const target = doctype === "Fund Transfer" && fieldname === "status" &&
				["=", "like"].includes(operator) && legacy.has(value) ? historical : standard;
			target.push(filter);
		});
		const result = original.call(this, standard);
		result.non_standard_filters = (result.non_standard_filters || []).concat(historical);
		return result;
	};
	if (legacy.has(selected)) {
		return field.set_value("").then(() => area.add([["Fund Transfer", "status", "=", selected]]));
	}
}
