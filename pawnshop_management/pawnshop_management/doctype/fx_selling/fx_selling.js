frappe.ui.form.on("FX Selling", {
	async onload(frm) {
		frm._fx_initializing = true;
		set_currency_table_locked(frm, true);
		if (frm.is_new()) {
			frm.clear_table("currencies");
			frm.refresh_field("currencies");
		}
		if (frm.is_new() && !frm.doc.branch) {
			const context = await frappe.call({
				method: "pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.get_fx_selling_context",
			});
			if (context.message && context.message.branch) {
				await frm.set_value("branch", context.message.branch);
				await frm.set_value("seller", context.message.seller);
			}
		}
		frm._fx_initializing = false;
		if (frm.doc.docstatus === 0) {
			const rates_loaded = await load_rates(frm);
			if (rates_loaded) {
				await load_available_currencies(frm);
			}
		}
		if (frm.doc.customer) load_customer_ids(frm);
	},

	refresh(frm) {
		const is_system_manager = frappe.user_roles.includes("System Manager") || frappe.session.user === "Administrator";
		frm.set_df_property("branch", "read_only", !is_system_manager);
		frm.set_df_property("customer", "read_only", !frm.is_new());
		set_currency_table_locked(
			frm,
			frm.doc.docstatus === 1 || !frm._fx_rates_loaded || !frm._fx_availability_loaded
		);
		update_compliance_fields(frm);
	},

	async branch(frm) {
		if (frm._fx_initializing || !frm.doc.branch || !frm._fx_rates_loaded) return;
		await load_available_currencies(frm);
	},

	customer(frm) {
		load_customer_ids(frm);
	},

	customer_id_picture(frm) {
		const selected = (frm._customer_id_options || []).find(row => row.value === frm.doc.customer_id_picture);
		if (!selected || !selected.id_pic_name) return;
		const url = `https://firebasestorage.googleapis.com/v0/b/gpcustomersids.appspot.com/o/customerPictures%2F${encodeURIComponent(selected.id_pic_name)}.jpg?alt=media`;
		frm.get_field("customer_id_html").$wrapper.html(`<img src="${url}" style="max-width:400px;height:auto">`);
	},

});

frappe.ui.form.on("FX Selling Currency", {
	async currencies_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (frm._fx_rates_loaded && (!row.currency || row.currency === "USD")) {
			if (!row.currency) {
				await frappe.model.set_value(cdt, cdn, "currency", "USD");
			}
			await apply_usd_rate(frm, cdt, cdn);
		}
		calculate_total(frm);
	},

	currencies_remove(frm) {
		calculate_total(frm);
	},

	async currency(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!frm._fx_rates_loaded) {
			await frappe.model.set_value(cdt, cdn, "currency", null);
			show_rate_error(__("FX rates have not finished loading. Currency entry remains disabled; reload the form and try again."));
			return;
		}
		if (row.currency === "USD") {
			await apply_usd_rate(frm, cdt, cdn);
		} else {
			await select_tracker_request(frm, cdt, cdn, row.currency);
		}
		calculate_row(frm, cdt, cdn);
	},

	amount(frm, cdt, cdn) {
		calculate_row(frm, cdt, cdn);
	},
});

async function apply_usd_rate(frm, cdt, cdn) {
	const rate = (frm._fx_rates || {}).USD;
	if (!rate) {
		frappe.msgprint(__("No current USD rate is available."));
		return false;
	}
	await frappe.model.set_value(cdt, cdn, "base_rate", rate.base_rate);
	await frappe.model.set_value(cdt, cdn, "selling_addition", rate.selling_addition);
	await frappe.model.set_value(cdt, cdn, "selling_rate", rate.selling_rate);
	await frappe.model.set_value(cdt, cdn, "rate_source_row", rate.source_row);
	await clear_request(cdt, cdn);
	return true;
}

async function load_rates(frm) {
	frm._fx_rates_loaded = false;
	set_currency_table_locked(frm, true);
	try {
		const result = await frappe.call({
			method: "pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.get_current_rates",
			freeze: true,
			freeze_message: __("Loading current FX rates..."),
		});
		frm._fx_rates = result.message || {};
		if (!Object.keys(frm._fx_rates).length) {
			throw new Error(__("The All Rates sheet returned no usable rates."));
		}
		frm._fx_rates_loaded = true;
		await apply_rates_to_existing_rows(frm);
		return true;
	} catch (error) {
		console.error("Unable to load FX rates", error);
		frm._fx_rates = {};
		frm._fx_rates_loaded = false;
		set_currency_table_locked(frm, true);
		show_rate_error(get_rate_error_message(error));
		return false;
	}
}

async function load_available_currencies(frm) {
	frm._fx_availability_loaded = false;
	set_currency_table_locked(frm, true);
	set_currency_options(frm, ["USD"]);
	const branch = frm.doc.branch;
	const fallback_timer = setTimeout(() => {
		if (frm.doc.branch !== branch || frm._fx_availability_loaded) return;
		frm._fx_availability_loaded = true;
		set_currency_table_locked(frm, frm.doc.docstatus === 1);
		frappe.show_alert({
			indicator: "orange",
			message: __("Transfer Tracker is still loading. USD is available now; other currencies will appear when loading finishes."),
		}, 8);
	}, 8000);
	try {
		const result = await frappe.call({
			method: "pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.get_available_tracker_requests",
			args: { branch: frm.doc.branch },
		});
		clearTimeout(fallback_timer);
		if (frm.doc.branch !== branch) return;
		frm._fx_tracker_requests = result.message || [];
		const rate_currencies = Object.keys(frm._fx_rates || {});
		const available = new Set(["USD"]);
		for (const request of frm._fx_tracker_requests) {
			const currency = rate_currencies.find(
				value => normalize_currency(value) === normalize_currency(request.currency)
			);
			if (currency) available.add(currency);
		}
		set_currency_options(frm, Array.from(available));
		await apply_tracker_rates_to_existing_rows(frm);
		frm._fx_availability_loaded = true;
		set_currency_table_locked(frm, frm.doc.docstatus === 1);
	} catch (error) {
		clearTimeout(fallback_timer);
		if (frm.doc.branch !== branch) return;
		console.error("Unable to load available FX currencies", error);
		frm._fx_tracker_requests = [];
		set_currency_options(frm, ["USD"]);
		frm._fx_availability_loaded = true;
		set_currency_table_locked(frm, frm.doc.docstatus === 1);
		frappe.msgprint({
			title: __("Unable to Load Available Currencies"),
			indicator: "orange",
			message: __("ERPNext could not check the Transfer Tracker. USD remains available, but non-USD currencies cannot be selected until the tracker loads successfully."),
		});
	}
}

function set_currency_options(frm, currencies) {
	frm._fx_available_currencies = currencies;
	frm.fields_dict.currencies.grid.update_docfield_property(
		"currency",
		"options",
		currencies.join("\n")
	);
}

async function apply_rates_to_existing_rows(frm) {
	for (const row of frm.doc.currencies || []) {
		if (row.currency !== "USD") continue;
		const rate = frm._fx_rates[row.currency];
		if (!rate) continue;
		await frappe.model.set_value(row.doctype, row.name, "base_rate", rate.base_rate);
		await frappe.model.set_value(row.doctype, row.name, "selling_addition", rate.selling_addition);
		await frappe.model.set_value(row.doctype, row.name, "selling_rate", rate.selling_rate);
		await frappe.model.set_value(row.doctype, row.name, "rate_source_row", rate.source_row);
		await frappe.model.set_value(row.doctype, row.name, "peso_amount", flt(row.amount) * flt(rate.selling_rate));
	}
	calculate_total(frm);
}

async function apply_tracker_rates_to_existing_rows(frm) {
	for (const row of frm.doc.currencies || []) {
		if (row.currency === "USD" || !row.request_no) continue;
		const request = (frm._fx_tracker_requests || []).find(
			value => String(value.request_no) === String(row.request_no)
				&& normalize_currency(value.currency) === normalize_currency(row.currency)
		);
		if (!request) continue;
		await frappe.model.set_value(row.doctype, row.name, "base_rate", request.request_rate);
		await frappe.model.set_value(row.doctype, row.name, "selling_addition", 0);
		await frappe.model.set_value(row.doctype, row.name, "selling_rate", request.request_rate);
		await frappe.model.set_value(row.doctype, row.name, "rate_source_row", request.source_row);
		await frappe.model.set_value(row.doctype, row.name, "peso_amount", flt(row.amount) * flt(request.request_rate));
	}
	calculate_total(frm);
}

function set_currency_table_locked(frm, locked) {
	frm.set_df_property("currencies", "read_only", Boolean(locked));
	frm.refresh_field("currencies");
}

function show_rate_error(message) {
	frappe.msgprint({
		title: __("Unable to Load FX Rates"),
		indicator: "red",
		message: message || __("ERPNext could not load rates from Google Sheets. Currency entry has been disabled. Verify the FX Selling Settings and Google service-account access, then reload the form."),
	});
}

function get_rate_error_message(error) {
	const server_message = error && (error.message || error.exc);
	return server_message || __("ERPNext could not load rates from Google Sheets. Currency entry has been disabled. Verify the FX Selling Settings and Google service-account access, then reload the form.");
}

async function select_tracker_request(frm, cdt, cdn, currency) {
	const requests = (frm._fx_tracker_requests || []).filter(
		row => normalize_currency(row.currency) === normalize_currency(currency)
	);
	if (!requests.length) {
		await clear_request(cdt, cdn);
		frappe.msgprint(__("No available Transfer Tracker request was found for {0} at this branch.", [currency]));
		return;
	}
	const labels = requests.map(row => `${row.request_no} — ${format_currency_amount(row.available_amount)} ${currency}`);
	const dialog = new frappe.ui.Dialog({
		title: __("Select Transfer Tracker Request"),
		fields: [{ fieldname: "request", fieldtype: "Select", label: __("Request"), options: labels.join("\n"), reqd: 1 }],
		primary_action_label: __("Select"),
		async primary_action(values) {
			const selected = requests[labels.indexOf(values.request)];
			await frappe.model.set_value(cdt, cdn, "request_no", selected.request_no);
			await frappe.model.set_value(cdt, cdn, "request_source_row", selected.source_row);
			await frappe.model.set_value(cdt, cdn, "request_available_amount", selected.available_amount);
			await frappe.model.set_value(cdt, cdn, "base_rate", selected.request_rate);
			await frappe.model.set_value(cdt, cdn, "selling_addition", 0);
			await frappe.model.set_value(cdt, cdn, "selling_rate", selected.request_rate);
			await frappe.model.set_value(cdt, cdn, "rate_source_row", selected.source_row);
			await frappe.model.set_value(cdt, cdn, "amount", selected.available_amount);
			await frappe.model.set_value(cdt, cdn, "remaining_amount", 0);
			calculate_row(frm, cdt, cdn);
			dialog.hide();
		},
	});
	dialog.show();
}

function calculate_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "peso_amount", flt(row.amount) * flt(row.selling_rate));
	if (row.currency !== "USD" && row.request_available_amount) {
		frappe.model.set_value(cdt, cdn, "remaining_amount", Math.max(0, flt(row.request_available_amount) - flt(row.amount)));
	}
	calculate_total(frm);
}

function calculate_total(frm) {
	const total = (frm.doc.currencies || []).reduce((sum, row) => sum + flt(row.peso_amount), 0);
	frm.set_value("total_peso_amount", total);
	update_compliance_fields(frm, total);
}

function update_compliance_fields(frm, total) {
	const requires_compliance = flt(total === undefined ? frm.doc.total_peso_amount : total) >= 100000;
	for (const fieldname of ["source_of_funds", "purpose"]) {
		frm.toggle_display(fieldname, requires_compliance);
		frm.toggle_reqd(fieldname, requires_compliance);
		frm.set_df_property(fieldname, "read_only", frm.doc.docstatus === 1 || !requires_compliance);
		if (!requires_compliance && frm.doc.docstatus === 0 && frm.doc[fieldname]) {
			frm.set_value(fieldname, null);
		}
	}
}

async function clear_request(cdt, cdn) {
	for (const field of ["request_no", "request_source_row", "request_available_amount", "remaining_amount"]) {
		await frappe.model.set_value(cdt, cdn, field, null);
	}
}

function normalize_currency(value) {
	const normalized = String(value || "").replace(/\s/g, "").toUpperCase();
	return normalized === "THAIBAHT" ? "THAIB" : normalized;
}

function format_currency_amount(value) {
	return format_number(flt(value), null, 2);
}

async function load_customer_ids(frm) {
	if (!frm.doc.customer) {
		frm.set_df_property("customer_id_picture", "options", []);
		frm.set_value("customer_id_picture", null);
		frm.get_field("customer_id_html").$wrapper.empty();
		return;
	}
	const result = await frappe.call({
		method: "pawnshop_management.pawnshop_management.utils.get_contact_id_pictures_by_customer",
		args: { customer: frm.doc.customer },
	});
	const data = result.message || {};
	const options = data.options || [];
	frm._customer_id_options = options;
	frm.set_df_property("customer_id_picture", "options", options.map(row => ({ label: row.label, value: row.value })));
	await frm.set_value("customer_id_picture", data.selected || null);
	frm.get_field("customer_id_html").$wrapper.html(data.html || "");
	if (data.all_customer_ids_expired) {
		frappe.msgprint({ title: __("Expired Identification"), indicator: "red", message: __("All customer IDs have expired. This FX Selling transaction cannot be submitted.") });
	}
}
