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
const ROVER_TRANSFER_TYPES = ["Rover to Vault", "Vault to Cash Manager", "Cash Manager to Vault"];

frappe.ui.form.on("Fund Transfer", {
	setup(frm) {
		frm.set_query("branch", () => {
			if (frappe.session.user === "Administrator") {
				return {};
			}
			return { filters: { vault_custodian: frappe.session.user } };
		});
		frm.set_query("rover", () => ({
			query: "pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.rover_user_query",
		}));
	},

	refresh(frm) {
		set_transfer_definition_read_only(frm);
		set_transfer_type_options(frm);
		if (frm.is_new()) {
			frm.set_value("business_date", frappe.datetime.get_today());
			set_branch_from_request_ip(frm);
		}
	},

	async before_workflow_action(frm) {
		if (
			frm.selected_workflow_action === "Submit" &&
			ROVER_TRANSFER_TYPES.includes(frm.doc.transfer_type)
		) {
			const values = await prompt_for_rover_confirmation(frm);
			await frm.set_value("rover", values.rover);
			await frm.set_value("rover_password", values.password);
		}

		if (frm.selected_workflow_action === "Reject") {
			const values = await prompt_for_rejection();
			await frm.set_value("comments", append_comment(frm.doc.comments, `Rejected: ${values.reason}`));
		}
	},

	currency(frm) {
		set_transfer_type_options(frm);
	},
});

function set_transfer_type_options(frm) {
	const php = [
		"Vault to Pawnshop (-NCB)",
		"Pawnshop (-NCB) to Vault",
		"Vault to Remittance",
		"Remittance to Vault",
		"Vault to ForEx",
		"ForEx to Vault",
		"Armored Van to Vault",
		"Rover to Vault",
		"Vault to Cash Manager",
		"Cash Manager to Vault",
	];
	const usd = [
		"Vault to Remittance",
		"Remittance to Vault",
		"ForEx to Vault",
		"Armored Van to Vault",
		"Rover to Vault",
		"Vault to Cash Manager",
		"Cash Manager to Vault",
	];
	const options = frm.doc.currency === "USD" ? usd : frm.doc.currency === "PHP" ? php : [];
	frm.toggle_display("transfer_type", Boolean(frm.doc.currency));
	frm.set_df_property("transfer_type", "options", options.join("\n"));
	if (frm.doc.transfer_type && !options.includes(frm.doc.transfer_type)) {
		frm.set_value("transfer_type", null);
	}
}

function set_transfer_definition_read_only(frm) {
	const read_only = frm.doc.status !== "Draft";
	TRANSFER_DEFINITION_FIELDS.forEach((fieldname) => {
		const field_read_only =
			read_only || (fieldname === "branch" && frappe.session.user !== "Administrator");
		frm.set_df_property(fieldname, "read_only", field_read_only ? 1 : 0);
	});
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

function prompt_for_rejection() {
	return new Promise((resolve) => {
		frappe.prompt(
			[{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }],
			resolve,
			__("Reject Fund Transfer"),
			__("Continue")
		);
	});
}

function prompt_for_rover_confirmation(frm) {
	return new Promise((resolve) => {
		const dialog = new frappe.ui.Dialog({
			title: __("Rover Confirmation"),
			fields: [
				{
					fieldname: "confirmation",
					fieldtype: "HTML",
					options: __(
						"<p>Confirm <b>{0} {1}</b> for <b>{2}</b>. The Rover password authorizes this exact transfer.</p>",
						[frm.doc.currency, format_currency(frm.doc.amount, frm.doc.currency), frm.doc.transfer_type]
					),
				},
				{ fieldname: "rover", fieldtype: "Link", options: "User", label: __("Rover"), reqd: 1 },
				{ fieldname: "password", fieldtype: "Password", label: __("Password"), reqd: 1 },
			],
			primary_action_label: __("Continue"),
			primary_action(values) {
				dialog.hide();
				resolve(values);
			},
		});
		dialog.fields_dict.rover.get_query = () => ({
			query: "pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.rover_user_query",
		});
		dialog.show();
	});
}

function append_comment(current, addition) {
	return current ? `${current}\n${addition}` : addition;
}
