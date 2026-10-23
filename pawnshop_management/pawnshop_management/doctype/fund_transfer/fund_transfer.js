// Copyright (c) 2026, Rabie Santillan and Eric Mendoza and contributors
// For license information, please see license.txt

const TRANSFER_DEFINITION_FIELDS = [
	"branch",
	"currency",
	"transfer_type",
	"amount",
	"legacy_transfer_id",
	"external_party",
];
const ROVER_TRANSFER_TYPES = ["Rover to Vault", "Vault to Cash Manager"];
const UNCOLLECTED_FX_TYPE = "Uncollected FX to Vault";

frappe.ui.form.on("Fund Transfer", {
	setup(frm) {
		$(document).off("ajaxComplete.fund_transfer_confirmation").on("ajaxComplete.fund_transfer_confirmation", (_event, _xhr, settings) => {
			if ((settings.url || "").includes("frappe.model.workflow.apply_workflow") ||
				String(settings.data || "").includes("frappe.model.workflow.apply_workflow")) {
				frm.doc.confirmation_password = null;
				frm.doc.rover_password = null;
			}
		});
		frm.set_query("branch", () => ({ filters: { name: ["in", frm.__entry_branches || []] } }));
		frm.set_query("rover", () => ({
			query: "pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.rover_user_query",
		}));
	},

	refresh(frm) {
		set_transfer_definition_read_only(frm);
		set_transfer_type_options(frm);
		configure_linked_fx_lifecycle_actions(frm);
		if (frm.is_new()) {
			frm.set_value("business_date", frappe.datetime.get_today());
			set_branch_from_request_ip(frm);
		}
		if (frm.doc.transfer_type === UNCOLLECTED_FX_TYPE && frm.doc.branch && !frm.doc.fx_cpr_date) {
			select_uncollected_fx_envelope(frm);
		}
	},

	async before_workflow_action(frm) {
		let context;
		if (frm.selected_workflow_action === "Submit") {
			context = await load_entry_context(frm);
			show_day_closure(frm, context);
			if (context.closed_position) frappe.throw(context.closure_message);
		}
		if (
			frm.selected_workflow_action === "Submit" &&
			ROVER_TRANSFER_TYPES.includes(frm.doc.transfer_type)
		) {
			const values = await prompt_for_rover_confirmation(frm);
			frm.doc.rover = values.rover;
			// Transient values: do not mark the saved draft dirty or save credentials.
			frm.doc.rover_password = values.password;
		}

		if (frm.selected_workflow_action === "Submit" && !ROVER_TRANSFER_TYPES.includes(frm.doc.transfer_type)) {
			const entry = context.transfers.find((item) => item.transfer_type === frm.doc.transfer_type);
			if (!entry) frappe.throw(__("You cannot initiate this transfer type for this branch."));
			if (entry.authorization === "cashier") {
				if (!entry.confirmer) frappe.throw(__("No {0} is assigned to this branch.", [entry.confirmer_label]));
				const values = await prompt_for_confirmation(frm, entry);
				frm.doc.confirmation_password = values.password;
			}
		}
	},

	after_workflow_action(frm) {
		frm.doc.confirmation_password = null;
		frm.doc.rover_password = null;
	},

	currency(frm) {
		set_transfer_type_options(frm);
		if (frm.doc.currency !== "USD") {
			clear_uncollected_fx_envelope(frm);
		}
	},

	transfer_type(frm) {
		set_transfer_definition_read_only(frm);
		if (frm.doc.transfer_type === UNCOLLECTED_FX_TYPE && !frm.doc.fx_cpr_date) {
			select_uncollected_fx_envelope(frm);
		} else if (frm.doc.transfer_type !== UNCOLLECTED_FX_TYPE) {
			clear_uncollected_fx_envelope(frm);
		}
	},

	branch(frm) {
		set_transfer_type_options(frm);
		if (frm.doc.transfer_type === UNCOLLECTED_FX_TYPE && !frm.doc.fx_cpr_date) {
			select_uncollected_fx_envelope(frm);
		}
	},
});

function configure_linked_fx_lifecycle_actions(frm) {
	if (frappe.session.user !== "Administrator" || !frm.doc.fx_selling || frm.is_new()) return;

	if (frm.doc.docstatus === 1) {
		frm.page.set_secondary_action(__("Cancel Linked Transaction"), () => {
			cancel_linked_fx_transaction(frm);
		});
	} else if (frm.doc.docstatus === 2) {
		frm.add_custom_button(__("Delete Linked Transaction"), () => {
			delete_linked_fx_transaction(frm);
		});
	}
}

function cancel_linked_fx_transaction(frm) {
	frappe.confirm(
		__("Cancel this Fund Transfer and its linked FX Selling document?"),
		() => frappe.call({
			method: "pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.cancel_linked_transaction",
			args: { reference_doctype: frm.doctype, reference_name: frm.doc.name },
			freeze: true,
			freeze_message: __("Cancelling linked transaction..."),
			callback(response) {
				if (!response.exc) frm.reload_doc();
			},
		})
	);
}

function delete_linked_fx_transaction(frm) {
	frappe.confirm(
		__("Permanently delete this Fund Transfer and its linked FX Selling document?"),
		() => frappe.call({
			method: "pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.delete_linked_transaction",
			args: { reference_doctype: frm.doctype, reference_name: frm.doc.name },
			freeze: true,
			freeze_message: __("Deleting linked transaction..."),
			callback(response) {
				if (!response.exc) frappe.set_route("List", frm.doctype);
			},
		})
	);
}

async function load_entry_context(frm) {
	const response = await frappe.call({
		method: "pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.get_entry_context",
		args: { branch: frm.doc.branch, currency: frm.doc.currency },
	});
	return response.message;
}

async function set_transfer_type_options(frm) {
	// Historical documents must retain their original type and displayed options.
	if (!frm.is_new() && frm.doc.status !== "Draft") return;
	const branch = frm.doc.branch;
	const currency = frm.doc.currency;
	const context = await load_entry_context(frm);
	if (branch !== frm.doc.branch || currency !== frm.doc.currency) return;
	show_day_closure(frm, context);
	frm.__entry_branches = context.branches;
	const options = context.transfers.map((entry) => entry.transfer_type);
	frm.toggle_display("transfer_type", Boolean(currency));
	frm.set_df_property("transfer_type", "options", options.join("\n"));
	if (frm.doc.transfer_type && !options.includes(frm.doc.transfer_type)) {
		frm.set_value("transfer_type", null);
	}
}

function show_day_closure(frm, context) {
	if (context.closed_position) {
		frm.__day_closed = true;
		frm.disable_save();
		frm.dashboard.set_headline_alert(context.closure_message);
	} else if (frm.__day_closed) {
		frm.__day_closed = false;
		frm.enable_save();
		frm.dashboard.clear_headline();
	}
}

function set_transfer_definition_read_only(frm) {
	const read_only = frm.doc.status !== "Draft";
	TRANSFER_DEFINITION_FIELDS.forEach((fieldname) => {
		const field_read_only =
			read_only ||
			(fieldname === "branch" && frappe.session.user !== "Administrator") ||
			(fieldname === "amount" && frm.doc.transfer_type === UNCOLLECTED_FX_TYPE) ||
			(fieldname === "currency" && Boolean(frm.doc.fx_cpr_date));
		frm.set_df_property(fieldname, "read_only", field_read_only ? 1 : 0);
	});
}

async function select_uncollected_fx_envelope(frm) {
	if (!frm.doc.branch || frm.__selecting_uncollected_fx) {
		return;
	}
	frm.__selecting_uncollected_fx = true;
	try {
		const response = await frappe.call({
			method: "pawnshop_management.pawnshop_management.fund_transfer_google.get_uncollected_fx_envelopes",
			args: { branch: frm.doc.branch },
			freeze: true,
			freeze_message: __("Getting uncollected FX envelopes..."),
		});
		const envelopes = response.message || [];
		if (!envelopes.length) {
			frappe.msgprint(__("No uncollected FX envelopes are available for this branch."));
			return;
		}
		const labels = envelopes.map(
			(envelope) => `$${Number(envelope.expected_amount).toLocaleString()} ~ ${envelope.cpr_date}`
		);
		const dialog = new frappe.ui.Dialog({
			title: __("Select Uncollected FX Envelope"),
			fields: [
				{
					fieldname: "envelope",
					fieldtype: "Select",
					label: __("Envelope"),
					options: labels,
					reqd: 1,
				},
				{
					fieldname: "actual_amount",
					fieldtype: "Int",
					label: __("Actual USD Deposited"),
					reqd: 1,
				},
				{
					fieldname: "difference",
					fieldtype: "Int",
					label: __("Difference / Shortage"),
					read_only: 1,
				},
			],
			primary_action_label: __("Use Envelope"),
			async primary_action(values) {
				const index = labels.indexOf(values.envelope);
				const envelope = envelopes[index];
				const actual = cint(values.actual_amount);
				if (actual <= 0 || actual > cint(envelope.expected_amount)) {
					frappe.msgprint(__("Actual USD must be a whole-dollar amount greater than zero and no more than {0}.", [envelope.expected_amount]));
					return;
				}
				await frm.set_value({
					fx_cpr_date: envelope.cpr_date,
					fx_expected_amount: envelope.expected_amount,
					fx_difference_amount: cint(envelope.expected_amount) - actual,
					fx_source_row: envelope.source_row,
					fx_source_rate: envelope.rate,
					amount: actual,
				});
				set_transfer_definition_read_only(frm);
				dialog.hide();
			},
		});
		const update_amounts = () => {
			const index = labels.indexOf(dialog.get_value("envelope"));
			const envelope = envelopes[index];
			if (!envelope) return;
			const actual = cint(dialog.get_value("actual_amount"));
			dialog.set_value("difference", Math.max(cint(envelope.expected_amount) - actual, 0));
		};
		dialog.fields_dict.envelope.df.onchange = () => {
			const envelope = envelopes[labels.indexOf(dialog.get_value("envelope"))];
			if (envelope) dialog.set_value("actual_amount", envelope.expected_amount);
			update_amounts();
		};
		dialog.fields_dict.actual_amount.df.onchange = update_amounts;
		dialog.show();
		dialog.set_value("envelope", labels[0]);
		dialog.set_value("actual_amount", envelopes[0].expected_amount);
		update_amounts();
	} finally {
		frm.__selecting_uncollected_fx = false;
	}
}

function clear_uncollected_fx_envelope(frm) {
	["fx_cpr_date", "fx_expected_amount", "fx_difference_amount", "fx_source_row", "fx_source_rate"].forEach(
		(fieldname) => {
			if (frm.doc[fieldname]) frm.set_value(fieldname, null);
		}
	);
	if (frm.doc.transfer_type !== UNCOLLECTED_FX_TYPE && frm.doc.amount) frm.set_value("amount", null);
	set_transfer_definition_read_only(frm);
}

function set_branch_from_request_ip(frm) {
	if (frm.doc.branch || frm.__setting_branch_from_ip) {
		return;
	}

	frm.__setting_branch_from_ip = true;
	frappe.call({
		method: "pawnshop_management.pawnshop_management.custom_codes.get_ip.get_ip",
		callback(response) {
			if (!response.message || !frm.is_new() || frm.doc.branch) {
				return;
			}

			frappe.db.get_list("Branch IP Addressing", {
				fields: ["name"],
				filters: { ip_address: response.message },
			}).then((records) => {
				if (records.length && frm.is_new() && !frm.doc.branch) {
					frm.set_value("branch", records[0].name);
				}
			});
		},
		always() {
			frm.__setting_branch_from_ip = false;
		},
	});
}

function prompt_for_confirmation(frm, entry) {
	return confirmation_dialog(frm, [
		{ fieldname: "confirmer", fieldtype: "Data", label: __(entry.confirmer_label), default: entry.confirmer, read_only: 1 },
	]);
}

function prompt_for_rover_confirmation(frm) {
	return confirmation_dialog(frm, [
		{ fieldname: "rover", fieldtype: "Link", options: "User", label: __("Rover"), reqd: 1,
			get_query: () => ({ query: "pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.rover_user_query" }) },
	]);
}

function confirmation_dialog(frm, participant_fields) {
	// A failed request must not leave a reusable password on the browser document.
	frm.doc.confirmation_password = null;
	frm.doc.rover_password = null;
	return new Promise((resolve, reject) => {
		let accepted = false;
		const dialog = new frappe.ui.Dialog({
			title: __("Confirm Fund Transfer"),
			fields: [
				{ fieldname: "branch", fieldtype: "Data", label: __("Branch"), default: frm.doc.branch, read_only: 1 },
				{ fieldname: "transfer_type", fieldtype: "Data", label: __("Transfer Type"), default: frm.doc.transfer_type, read_only: 1 },
				{ fieldname: "currency", fieldtype: "Data", label: __("Currency"), default: frm.doc.currency, read_only: 1 },
				{ fieldname: "amount", fieldtype: "Currency", label: __("Amount"), default: frm.doc.amount, read_only: 1, options: "currency" },
				...participant_fields,
				{ fieldname: "password", fieldtype: "Password", label: __("Confirming Person's Password"), reqd: 1 },
			],
			primary_action_label: __("Confirm and Submit"),
			primary_action(values) {
				accepted = true;
				dialog.set_value("password", "");
				dialog.hide();
				resolve(values);
			},
			onhide() {
				if (!accepted) {
					frappe.dom.unfreeze();
					reject(new Error(__("Transfer confirmation cancelled.")));
				}
			},
		});
		frappe.dom.unfreeze();
		dialog.show();
	});
}
