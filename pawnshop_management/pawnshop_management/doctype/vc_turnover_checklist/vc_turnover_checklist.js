/* eslint-disable */

const TOTAL_FIELD_GROUPS = {
	jewelry_display_total: [
		"necklace_count",
		"pendant_count",
		"earrings_count",
		"rings_count",
		"bracelet_count",
		"bangle_count",
		"set_count",
	],
	gadgets_display_total: ["cellphone_count", "tablet_count", "laptop_count", "dslr_count"],
	php_total: [
		"php_1000",
		"php_500",
		"php_200",
		"php_100",
		"php_50",
		"php_20",
		"php_10",
		"php_5",
		"php_1",
		"php_025",
	],
	usd_total: ["usd_100", "usd_50", "usd_20", "usd_10", "usd_5", "usd_2", "usd_1"],
	petty_cash_total: [
		"petty_php_1000",
		"petty_php_500",
		"petty_php_200",
		"petty_php_100",
		"petty_php_50",
		"petty_php_20",
		"petty_php_10",
		"petty_php_5",
		"petty_php_1",
	],
};

const toNumber = value => {
	const number = parseFloat(value);
	return Number.isFinite(number) ? number : 0;
};

const calculateTotals = frm => {
	Object.entries(TOTAL_FIELD_GROUPS).forEach(([target, fields]) => {
		const total = fields.reduce((sum, fieldname) => sum + toNumber(frm.doc[fieldname]), 0);
		frm.set_value(target, total);
	});
};

const CASH_BREAKDOWN_FIELDS = {
	php: TOTAL_FIELD_GROUPS.php_total,
	usd: TOTAL_FIELD_GROUPS.usd_total,
};

const setCashBreakdownReadOnly = frm => {
	Object.entries(CASH_BREAKDOWN_FIELDS).forEach(([currency, fields]) => {
		const isManualFundTransferBreakdown =
			frm.doc.docstatus === 0 && frm.doc[`${currency}_cash_source_type`] === "Fund Transfer";
		fields.forEach(fieldname => {
			frm.set_df_property(fieldname, "read_only", isManualFundTransferBreakdown ? 0 : 1);
		});
	});
};

const applyVaultCashValues = (frm, values) => {
	if (!values) return;

	["php", "usd"].forEach(currency => {
		const totalField = currency === "php" ? "forex_reserved_php" : "forex_reserved_usd";
		const sourceTypeField = `${currency}_cash_source_type`;
		const sourceDocumentField = `${currency}_cash_source_document`;
		const previousSourceType = frm.doc[sourceTypeField];
		const sourceType = values[sourceTypeField] || "";
		const breakdown = values[`${currency}_breakdown`];

		frm.set_value(totalField, values[totalField] || 0);
		if (sourceType === "Vault Cash Position" || !sourceType) {
			CASH_BREAKDOWN_FIELDS[currency].forEach(fieldname => {
				frm.set_value(fieldname, (breakdown && breakdown[fieldname]) || 0);
			});
		} else if (previousSourceType === "Vault Cash Position") {
			CASH_BREAKDOWN_FIELDS[currency].forEach(fieldname => frm.set_value(fieldname, 0));
		}

		frm.set_value(sourceTypeField, sourceType);
		frm.set_value(sourceDocumentField, values[sourceDocumentField] || "");
	});

	setCashBreakdownReadOnly(frm);
	calculateTotals(frm);
};

const applyAutofillValues = (frm, values) => {
	if (!values) return;

	[
		"branch",
		"endorsed_by",
		"sangla_envelopes_cb",
		"sangla_envelopes_ncb",
		"sangla_non_jewelry",
		"sanglang_benta",
		"cellphone_count",
		"tablet_count",
		"laptop_count",
		"dslr_count",
		"gadget_under_installment",
		"branch_mobile_phones",
	].forEach(fieldname => {
		if (Object.prototype.hasOwnProperty.call(values, fieldname)) {
			frm.set_value(fieldname, values[fieldname]);
		}
	});

	applyVaultCashValues(frm, values);
};

const refreshVaultCashFields = frm => {
	if (!frm.doc.branch || frm.doc.docstatus !== 0) return;

	frappe.call({
		method: "pawnshop_management.pawnshop_management.doctype.vc_turnover_checklist.vc_turnover_checklist.get_vault_cash_autofill_values",
		args: {
			branch: frm.doc.branch,
			business_date: frm.doc.date,
		},
		callback(response) {
			applyVaultCashValues(frm, response.message);
		},
	});
};

const refreshSystemFields = frm => {
	if (!frm.doc.branch) return;

	frappe.call({
		method: "pawnshop_management.pawnshop_management.doctype.vc_turnover_checklist.vc_turnover_checklist.get_autofill_values",
		args: {
			branch: frm.doc.branch,
		},
		freeze: true,
		freeze_message: __("Loading data"),
		callback(response) {
			applyAutofillValues(frm, response.message);
		},
	});
};

frappe.ui.form.on("VC Turnover Checklist", {
	setup(frm) {
		frm.set_query("received_by", () => ({
			filters: {
				enabled: 1,
			},
		}));

		frm.set_query("checked_witnessed_by", () => ({
			filters: {
				enabled: 1,
			},
		}));
	},

	refresh(frm) {
		if (frm.is_new() && !frm.doc.branch) {
			frappe.call({
				method: "pawnshop_management.pawnshop_management.doctype.vc_turnover_checklist.vc_turnover_checklist.get_default_branch",
				freeze: true,
				freeze_message: __("Loading data"),
				callback(response) {
					if (response.message && !frm.doc.branch) {
						frm.set_value("branch", response.message);
					}
				},
			});
		}

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Refresh System Counts"), () => refreshSystemFields(frm));
			refreshVaultCashFields(frm);
		}

		setCashBreakdownReadOnly(frm);
		calculateTotals(frm);
	},

	branch(frm) {
		refreshSystemFields(frm);
	},
});

Object.values(TOTAL_FIELD_GROUPS).flat().forEach(fieldname => {
	frappe.ui.form.on("VC Turnover Checklist", fieldname, calculateTotals);
});
