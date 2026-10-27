const PHP_DENOMINATIONS = [1000, 500, 200, 100, 50, 20, 10, 5, 1, 0.25];
const USD_DENOMINATIONS = [100, 50, 20, 10, 5, 2, 1];

frappe.ui.form.on("Vault Cash Position", {
	setup(frm) {
		frm.set_query("branch", () => ({
			filters: frappe.session.user === "Administrator" ? {} : { vault_custodian: frappe.session.user },
		}));
	},

	branch(frm) {
		if (frm.__vcp_assigning_branch || frm.__vcp_creation_blocked ||
			(frm.is_new() && frm.__vcp_creation_doc !== frm.doc)) return;
		return load_balance_preview(frm);
	},

	validate(frm) {
		return check_balance_preview(frm);
	},

	async before_submit(frm) {
		await check_balance_preview(frm);
		await confirm_variances(frm);
	},

	async refresh(frm) {
		reset_creation_context(frm);
		frm.set_df_property("branch", "read_only", !frm.is_new() || Boolean(frm.doc.amended_from) || frappe.session.user !== "Administrator");
		if (frm.is_new()) {
			if (!await initialize_vcp_branch(frm)) return;
			seed_rows(frm, "php_denominations", PHP_DENOMINATIONS, "PHP");
			seed_rows(frm, "usd_denominations", USD_DENOMINATIONS, "USD");
		}
		if (frm.doc.docstatus === 0) return load_balance_preview(frm);
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
	amount(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const quantity = flt(row.denomination) ? flt(row.amount) / flt(row.denomination) : 0;
		frappe.model.set_value(cdt, cdn, "quantity", quantity);
		return recalculate_parent(frm);
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
		row.amount = flt(previous && previous.amount);
		row.quantity = row.amount / denomination;
	});
	frm.refresh_field(fieldname);
}

const VCP_METHOD = "pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position.";
const VCP_STALE_MESSAGE = "Vault transactions have changed or balances have not been loaded. Refresh the form and review your cash count before saving or submitting again.";

function reset_creation_context(frm) {
	if (frm.__vcp_creation_target === frm.doc) return;
	if (frm.__vcp_assignment_disabled) frm.enable_save();
	frm.__vcp_creation_target = frm.doc;
	frm.__vcp_creation_blocked = false;
	frm.__vcp_assignment_disabled = false;
	frm.__vcp_creation_request = null;
}

async function initialize_vcp_branch(frm) {
	reset_creation_context(frm);
	const doc = frm.doc;
	if (frm.__vcp_creation_blocked) return false;
	if (frm.__vcp_creation_doc === doc) return true;
	if (frm.__vcp_creation_request && frm.__vcp_creation_request.doc === doc) {
		return frm.__vcp_creation_request.promise;
	}
	frm.disable_save();
	frm.__vcp_assignment_disabled = true;
	const request = { doc };
	frm.__vcp_creation_request = request;
	request.promise = (async () => {
		try {
			const response = await frappe.call({method: VCP_METHOD + "get_creation_context"});
			if (frm.doc !== doc) return false;
			const access = response.message || {};
			if (!access.allowed || (!access.administrator && doc.branch && doc.branch !== access.branch)) {
				frm.__vcp_creation_blocked = true;
				doc.__unsaved = 0;
				const dialog = frappe.msgprint({title: __("Vault Custodian Assignment"), indicator: "red",
					message: access.message || __("This report's branch does not match your Vault Custodian assignment. Contact your administrator.")});
				dialog.onhide = () => frappe.set_route("List", "Vault Cash Position");
				return false;
			}
			// Existing branch values on amendments must never be silently replaced.
			if (access.branch && !doc.branch) {
				frm.__vcp_assigning_branch = true;
				try { await frm.set_value("branch", access.branch); }
				finally { frm.__vcp_assigning_branch = false; }
			}
			frm.__vcp_creation_doc = doc;
			frm.enable_save();
			frm.__vcp_assignment_disabled = false;
			return true;
		} catch (error) {
			if (frm.doc === doc) frappe.msgprint(__("Unable to verify your branch assignment. Refresh the form before creating a Vault Cash Position."));
			return false;
		} finally {
			if (frm.__vcp_creation_request === request) frm.__vcp_creation_request = null;
		}
	})();
	return request.promise;
}

async function load_balance_preview(frm) {
	if (frm.doc.docstatus !== 0) return;
	const doc = frm.doc, branch = doc.branch;
	const request = {};
	frm.__balance_load = request;
	frm.__balance_stale = false;
	delete doc._vault_balance_snapshot;
	if (!branch) { frm.__balance_load = null; return; }
	try {
		const response = await frappe.call({ method: VCP_METHOD + "get_balance_preview", args: { branch } });
		if (frm.__balance_load !== request || frm.doc !== doc || doc.branch !== branch) return;
		const preview = response.message;
		if (!preview || !preview.token) throw new Error("Missing balance snapshot");
		const values = Object.assign({}, preview);
		delete values.token;
		values.is_opening_position = preview.is_opening_position ? 1 : 0;
		update_computed_fields(frm, values);
		doc._vault_balance_snapshot = preview.token;
		await recalculate_parent(frm);
	} catch (error) {
		if (frm.__balance_load !== request || frm.doc !== doc) return;
		frm.__balance_stale = true;
		frappe.msgprint(__("Unable to load vault balances. Refresh the form before saving or submitting."));
	} finally {
		if (frm.__balance_load === request) frm.__balance_load = null;
	}
}

async function check_balance_preview(frm) {
	if (frm.__vcp_creation_blocked || frm.__vcp_creation_request || frm.__balance_load || frm.__balance_stale || !frm.doc._vault_balance_snapshot) {
		frappe.throw(__(VCP_STALE_MESSAGE));
	}
	const doc = frm.doc, token = doc._vault_balance_snapshot, branch = doc.branch;
	const response = await frappe.call({ method: VCP_METHOD + "get_balance_preview", args: { branch } });
	if (frm.doc !== doc || doc.branch !== branch || !response.message || response.message.token !== token) {
		frm.__balance_stale = true;
		frappe.throw(__(VCP_STALE_MESSAGE));
	}
	await recalculate_parent(frm);
}

async function recalculate_parent(frm) {
	if (frm.doc.docstatus !== 0) return;
	const total = (fieldname) =>
		(frm.doc[fieldname] || []).reduce((sum, row) => sum + flt(row.amount), 0);
	const values = {};
	for (const currency of ["php", "usd"]) {
		const actual = flt(total(currency + "_denominations"), 2);
		values[currency + "_actual_cash"] = actual;
		if (frm.doc.is_opening_position) values[currency + "_system_civ_balance"] = actual;
		const balance = frm.doc.is_opening_position ? actual : flt(frm.doc[currency + "_system_civ_balance"]);
		values[currency + "_variance"] = flt(actual - balance, 2);
	}
	update_computed_fields(frm, values);
}

function update_computed_fields(frm, values) {
	// These read-only values are recalculated by the server on save. Using
	// set_value here would dirty a just-saved Draft and hide its Submit action.
	// Do not clear __unsaved: real denomination edits must remain unsaved.
	Object.assign(frm.doc, values);
	Object.keys(values).forEach(fieldname => frm.refresh_field(fieldname));
}

function confirm_variances(frm) {
	const lines = ["php", "usd"].filter(currency => flt(frm.doc[currency + "_variance"])).map(currency => {
		const variance = flt(frm.doc[currency + "_variance"]);
		return currency.toUpperCase() + ": " + __("Actual Cash") + " " + flt(frm.doc[currency + "_actual_cash"]).toFixed(2) +
			"; " + __("System CIV") + " " + flt(frm.doc[currency + "_system_civ_balance"]).toFixed(2) +
			"; " + (variance < 0 ? __("Shortage") : __("Overage")) + " " + Math.abs(variance).toFixed(2);
	});
	if (!lines.length) return Promise.resolve();
	return new Promise((resolve, reject) => {
		frappe.confirm(lines.join("<br>") + "<br><br>" + __("Submit this discrepancy for Accounting review?"), resolve,
			() => { frappe.validated = false; reject(new Error("Submission cancelled")); });
	});
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
