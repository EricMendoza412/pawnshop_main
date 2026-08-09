const PHP_DENOMINATIONS = [1000, 500, 200, 100, 50, 20, 10, 5, 1, 0.25];
const USD_DENOMINATIONS = [100, 50, 20, 10, 5, 2, 1];

frappe.ui.form.on("Vault Cash Position", {
	setup(frm) {
		frm.set_query("branch", () => ({
			filters: { vault_custodian: frappe.session.user },
		}));
	},

	onload(frm) {
		if (frm.is_new()) {
			seed_rows(frm, "php_denominations", PHP_DENOMINATIONS, "PHP");
			seed_rows(frm, "usd_denominations", USD_DENOMINATIONS, "USD");
		}
	},

	refresh(frm) {
		if (frm.is_new()) {
			seed_rows(frm, "php_denominations", PHP_DENOMINATIONS, "PHP");
			seed_rows(frm, "usd_denominations", USD_DENOMINATIONS, "USD");
			return;
		}
		frappe.call({
			method: "pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position.get_action_context",
			args: { name: frm.doc.name },
			callback(r) {
				if ((r.message || {}).can_reconcile) {
					frm.add_custom_button(__("Approve Reconciliation"), () => approve_reconciliation(frm));
				}
			},
		});
	},
});

frappe.ui.form.on("Vault Cash Denomination", {
	quantity(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "amount", flt(row.denomination) * cint(row.quantity));
		recalculate_parent(frm);
	},
});

function seed_rows(frm, fieldname, denominations, currency) {
	const existing = new Map(
		(frm.doc[fieldname] || [])
			.filter((row) => denominations.includes(flt(row.denomination)))
			.map((row) => [flt(row.denomination), row])
	);
	frm.clear_table(fieldname);
	denominations.forEach((denomination) => {
		const row = frm.add_child(fieldname);
		const previous = existing.get(denomination);
		row.currency = currency;
		row.denomination = denomination;
		row.quantity = cint(previous && previous.quantity);
		row.amount = denomination * row.quantity;
	});
	frm.refresh_field(fieldname);
}

function recalculate_parent(frm) {
	const total = (fieldname) =>
		(frm.doc[fieldname] || []).reduce((sum, row) => sum + flt(row.denomination) * cint(row.quantity), 0);
	frm.set_value("php_actual_cash", total("php_denominations"));
	frm.set_value("usd_actual_cash", total("usd_denominations"));
}

function approve_reconciliation(frm) {
	frappe.prompt(
		[{ fieldname: "comments", fieldtype: "Small Text", label: __("Comments"), reqd: 1 }],
		(values) => {
			frappe.call({
				method: "pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position.approve_reconciliation",
				args: { name: frm.doc.name, comments: values.comments },
				freeze: true,
				callback() {
					frm.reload_doc();
				},
			});
		},
		__("Approve Cash Position Reconciliation"),
		__("Approve")
	);
}
