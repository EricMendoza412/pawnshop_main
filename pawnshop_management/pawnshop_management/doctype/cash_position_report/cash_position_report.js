// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cash Position Report', {
	onload(frm) {
		// store a per-session timestamp (not saved to DB)
		frm._loaded_at = frappe.datetime.now_datetime(); // "YYYY-MM-DD HH:mm:ss"
		// Optional: show user when the check will anchor from
		frappe.show_alert({message: `Loaded at: ${frm._loaded_at}`, indicator: 'blue'});

		if (frm.is_new()) {
			return load_cash_position_report(frm);
		}
  	},

	refresh: function(frm) {
		let is_allowed = frappe.user_roles.includes('Administrator');
		frm.toggle_enable(
			[
				'date', 
				'branch', 
				'beginning_balance', 
				'provisional_receipts', 
				'jewelry_a', 
				'jewelry_b', 
				'non_jewelry',
				'selling',
				'gcash',
				'bank_transfer'
			],
			 is_allowed);
		if (frm.doc.docstatus === 0 && frm.doc.branch && frm.doc.date) {
			if (!frm.__cpr_load) {
				return load_cash_position_report(frm, !frm.is_new());
			}
		}

	},

	branch: function(frm) {
		if (!frm.__cpr_assigning_branch) return load_cash_position_report(frm);
	},

	date: function(frm) {
		if (!frm.__cpr_assigning_branch) return load_cash_position_report(frm);
	},

	validate: async function(frm){
		if (frm.__cpr_load || frm.__cpr_load_failed) {
			frappe.throw(__('Wait for the report to finish loading successfully before saving.'));
		}
		if (frm.doc.total_cash == 0){
			frappe.throw("Cash on hand should not be zero")
		}


		const loaded_at = frm._loaded_at || frappe.datetime.now_datetime();
		// (Optional) pass branch/company if you want to scope the check
    	const args = { loaded_at , branch: frm.doc.branch };

    	const r = await frappe.call({
			method: 'pawnshop_management.pawnshop_management.doctype.cash_position_report.cash_position_report.check_new_submissions',
			args
		});

    	if (r.message && r.message.has_new) {
			const { details } = r.message;
			// You can customize this message
			// change title from Error to Warning

			frappe.throw({
				title: __('Warning'),
				message: __(
				`There are submitted/modified documents after this report was loaded:<br><br>
				${details.map(d => `${d.doctype}: <b>${d.name}</b> at ${d.modified}`).join('<br>')}
				<br><br>Please reload the report and try again.`
				)
			});
		}

	},

	after_save: function(frm) {
		if (frm.doc.docstatus === 1) { // Check if the document is submitted
			frappe.msgprint({
				message: __('Please do not forget to refresh and print the Pawnshop Transaction Log. <br><br> Thank you'),
				indicator: 'green',
				title: __('CPR Saved!'),
				primary_action: {
					action: function() {
						frappe.msg_dialog.hide();
					},
					label: __('OKAY')
				}
			});
		}
	},

	beginning_balance: function(frm){
		return frm.set_value('ending_balance', calculate_ending_balance(frm));
	},

	provisional_receipts: function(frm){
		return frm.set_value('total_in', calculate_total_in(frm));
	},

	selling: function(frm){
		return frm.set_value('total_in', calculate_total_in(frm));
	},

	cash_from_vault: function(frm){
		return frm.set_value('total_in', calculate_total_in(frm));
	},

	gcash_positive: function(frm){
		return frm.set_value('total_in', calculate_total_in(frm));
	},

	bank_transfer_return: function(frm){
		return frm.set_value('total_in', calculate_total_in(frm));
	},

	jewelry_a: function(frm){
		return frm.set_value('total_out', calculate_total_out(frm));
	},

	jewelry_b: function(frm){
		return frm.set_value('total_out', calculate_total_out(frm));
	},

	non_jewelry: function(frm){
		return frm.set_value('total_out', calculate_total_out(frm));
	},

	agreement_to_sell: function(frm){
		return frm.set_value('total_out', calculate_total_out(frm));
	},

	acknowledgement_receipts: function(frm){
		return frm.set_value('total_out', calculate_total_out(frm));
	},

	gcash: function(frm){
		return frm.set_value('total_out', calculate_total_out(frm));
	},

	bank_transfer: function(frm){
		return frm.set_value('total_out', calculate_total_out(frm));
	},

	cash_to_vault: function(frm){
		return frm.set_value('total_out', calculate_total_out(frm));
	},

	total_in: function(frm){
		return frm.set_value('net_cash', calculate_net_cash(frm));
	},
	
	total_out: function(frm){
		return frm.set_value('net_cash', calculate_net_cash(frm));
	},

	net_cash: function(frm){
		return frm.set_value('ending_balance', calculate_ending_balance(frm));
	},

	one_thousand_php_bills: function(frm){
		return total_cash_breakdown(frm);
	},

	five_hundred_php_bills: function(frm){
		return total_cash_breakdown(frm);
	},

	two_hundred_php_bills: function(frm){
		return total_cash_breakdown(frm);
	},

	one_hundred_php_bills: function(frm){
		return total_cash_breakdown(frm);
	},

	fifty_php_bills: function(frm){
		return total_cash_breakdown(frm);
	},

	twenty_php_bills: function(frm){
		return total_cash_breakdown(frm);
	},

	ten_php_coin: function(frm){
		return total_cash_breakdown(frm);
	},

	five_php_coin: function(frm){
		return total_cash_breakdown(frm);
	},

	peso_php_coin: function(frm){
		return total_cash_breakdown(frm);
	},

	twenty_five_cent_php_coin: function(frm){
		return total_cash_breakdown(frm);
	},

	shortage_overage: function(frm){
		//total_cash_breakdown(frm);
	}
});

async function check_cash_position_report_create_access(frm) {
	if (!frm.is_new() || frm.__cpr_create_access_checked) return true;
	const response = await frappe.call({
		method: 'pawnshop_management.pawnshop_management.doctype.cash_position_report.cash_position_report.get_cash_position_report_create_access',
		args: { branch: frm.doc.branch }
	});
	const access = response.message || {};
	if (!access.allowed) {
		block_cash_position_report_creation(frm, access.message);
		return false;
	}
	frm.__cpr_create_access_checked = true;
	if (access.branch && access.branch !== frm.doc.branch) {
		frm.__cpr_assigning_branch = true;
		try {
			await frm.set_value('branch', access.branch);
		} finally {
			frm.__cpr_assigning_branch = false;
		}
	}
	return true;
}

// Wait for every request (including failures) before releasing the overlay.
async function settle_cpr_requests(requests) {
	const results = await Promise.allSettled(requests);
	const failed = results.find(result => result.status === 'rejected');
	if (failed) throw failed.reason;
	return results.map(result => result.value);
}

function cpr_load_key(frm, fundOnly) {
	return JSON.stringify([frm.doc.name, frm.doc.branch, frm.doc.date, fundOnly]);
}

function load_cash_position_report(frm, fundOnly = false) {
	if (frm.doc.docstatus !== 0 || frm.__cpr_create_access_blocked) return Promise.resolve();
	if (frm.__cpr_load_failed || frm.is_new()) fundOnly = false;
	if (frm.__cpr_load) {
		// A full reload takes precedence over a fund-transfer-only refresh.
		frm.__cpr_load.fundOnly = frm.__cpr_load.fundOnly && fundOnly;
		return frm.__cpr_load.promise;
	}
	const state = { fundOnly, doc: frm.doc };
	frm.__cpr_load = state;
	frm.disable_save();
	frappe.dom.freeze(__('Loading data'));
	// Defer execution so repeated initial triggers can join this load.
	state.promise = Promise.resolve().then(async () => {
		try {
			if (!await check_cash_position_report_create_access(frm)) return;
			while (true) {
				if (frm.doc !== state.doc || frm.doc.docstatus !== 0) return;
				const key = cpr_load_key(frm, state.fundOnly);
				const snapshot = { branch: frm.doc.branch, date: frm.doc.date };
				if (!snapshot.branch || !snapshot.date) {
					throw new Error('Missing branch or date');
				}
				const requests = state.fundOnly ? [get_ps_fund_transfers(snapshot)] : [
					get_beginning_balance(snapshot),
					get_provisional_receipts_of_the_day(snapshot),
					get_jewelry_ab_of_the_day(snapshot),
					get_non_jewelry_of_the_day(snapshot),
					get_ats_of_the_day(snapshot),
					get_ar_of_the_day(snapshot),
					get_ps_fund_transfers(snapshot),
					get_subastado_sales(snapshot),
					get_pr_mops(snapshot)
				];
				let results;
				try {
					results = await settle_cpr_requests(requests);
				} catch (error) {
					if (key !== cpr_load_key(frm, state.fundOnly)) continue;
					throw error;
				}
				if (frm.doc !== state.doc || frm.doc.docstatus !== 0) return;
				if (key !== cpr_load_key(frm, state.fundOnly)) continue;
				const values = Object.assign({}, ...results);
				if (!state.fundOnly) {
					const sales = results[7], receipts = results[8];
					values.gcash = sales.gcash + receipts.gcash;
					values.bank_transfer = sales.bank_transfer + receipts.bank_transfer;
					await select_naming_series(frm);
				}
				if (key !== cpr_load_key(frm, state.fundOnly)) continue;
				await frm.set_value(values);
				await frm.set_value('total_in', calculate_total_in(frm));
				await frm.set_value('total_out', calculate_total_out(frm));
				await frm.set_value('net_cash', calculate_net_cash(frm));
				await frm.set_value('ending_balance', calculate_ending_balance(frm));
				await total_cash_breakdown(frm);
				if (key !== cpr_load_key(frm, state.fundOnly)) continue;
				frm.__cpr_load_failed = false;
				frm.remove_custom_button(__('Retry Loading Data'));
				frm.enable_save();
				break;
			}
		} catch (error) {
			console.error('Cash Position Report loading failed', error);
			frm.__cpr_load_failed = true;
			frm.disable_save();
			frm.add_custom_button(__('Retry Loading Data'), () => load_cash_position_report(frm));
			frappe.msgprint({
				title: __('Unable to load Cash Position Report'),
				message: __('Some report data could not be loaded. Click Retry Loading Data before saving.'),
				indicator: 'red'
			});
		} finally {
			frm.__cpr_load = null;
			frappe.dom.unfreeze();
		}
	});
	return state.promise;
}

function block_cash_position_report_creation(frm, message) {
	if (frm.__cpr_create_access_blocked) {
		return;
	}

	frm.__cpr_create_access_blocked = true;
	frm.disable_save();
	frm.doc.__unsaved = 0;

	const dialog = frappe.msgprint({
		title: __('CPR creation restricted'),
		message: __(message || 'Only the assigned Pawnshop Cashier can create a Cash Position Report.'),
		indicator: 'red'
	});

	dialog.onhide = function() {
		frm.doc.__unsaved = 0;
		const previous_route = frappe.get_prev_route();
		if (previous_route && previous_route.length) {
			frappe.set_route(previous_route);
			return;
		}

		frappe.set_route('List', 'Cash Position Report');
	};
}


function get_beginning_balance(snapshot) {
	return frappe.call('pawnshop_management.pawnshop_management.custom_codes.get_latest_cpr.get_latest_cpr', {
		branch: snapshot.branch
	}).then(record => ({ beginning_balance: flt(record.message) }));
}

function calculate_total_in(frm) {
	var total_in = flt(frm.doc.provisional_receipts) + flt(frm.doc.selling) + flt(frm.doc.cash_from_vault) + flt(frm.doc.gcash_positive) + flt(frm.doc.bank_transfer_return);
	return total_in;
}

function calculate_total_out(frm){
	var total_out = flt(frm.doc.jewelry_a) + flt(frm.doc.jewelry_b) + flt(frm.doc.cash_to_vault) + flt(frm.doc.non_jewelry) + flt(frm.doc.agreement_to_sell) + flt(frm.doc.acknowledgement_receipts) + flt(frm.doc.gcash) + flt(frm.doc.bank_transfer);
	return total_out;
}

function calculate_net_cash(frm) {
	var net_cash = calculate_total_in(frm) - calculate_total_out(frm);
	return net_cash;
}

function calculate_ending_balance(frm) {
	var ending_balance = flt(frm.doc.beginning_balance) + calculate_net_cash(frm);
	return ending_balance;
}
function get_daily_cpr_total(snapshot, method, field) {
	return frappe.call('pawnshop_management.pawnshop_management.custom_codes.daily_balance.' + method, {
		date: snapshot.date, branch: snapshot.branch
	}).then(response => ({ [field]: flt(response.message) }));
}

function get_provisional_receipts_of_the_day(snapshot) {
	return get_daily_cpr_total(snapshot, 'get_all_PR_total', 'provisional_receipts');
}
function get_ats_of_the_day(snapshot) {
	return get_daily_cpr_total(snapshot, 'get_all_ATS_total', 'agreement_to_sell');
}
function get_ar_of_the_day(snapshot) {
	return get_daily_cpr_total(snapshot, 'get_all_AR_total', 'acknowledgement_receipts');
}

async function get_cpr_pawn_amounts(snapshot, doctype) {
	const records = await frappe.db.get_list(doctype, {
		fields: doctype === 'Pawn Ticket Jewelry' ? ['net_proceeds', 'pawn_ticket', 'item_series'] : ['net_proceeds', 'pawn_ticket'],
		filters: { date_loan_granted: snapshot.date, branch: snapshot.branch, old_pawn_ticket: '', docstatus: 1 },
		limit: 500
	});
	return settle_cpr_requests(records.map(async record => {
		const receipts = await frappe.db.get_list('Provisional Receipt', {
			fields: ['pawn_ticket_no', 'principal_amount', 'interest'],
			filters: { transaction_type: 'Amortization', pawn_ticket_no: record.pawn_ticket, docstatus: 1 }
		});
		const amount = receipts.length ? flt(receipts[0].principal_amount) - flt(receipts[0].interest) : flt(record.net_proceeds);
		return { series: record.item_series, amount };
	}));
}

async function get_jewelry_ab_of_the_day(snapshot) {
	const rows = await get_cpr_pawn_amounts(snapshot, 'Pawn Ticket Jewelry');
	return {
		jewelry_a: rows.filter(row => row.series === 'A').reduce((sum, row) => sum + row.amount, 0),
		jewelry_b: rows.filter(row => row.series === 'B').reduce((sum, row) => sum + row.amount, 0)
	};
}

async function get_non_jewelry_of_the_day(snapshot) {
	const rows = await get_cpr_pawn_amounts(snapshot, 'Pawn Ticket Non Jewelry');
	return { non_jewelry: rows.reduce((sum, row) => sum + row.amount, 0) };
}

function get_ps_fund_transfers(snapshot) {
	return frappe.call({
		method: 'pawnshop_management.pawnshop_management.doctype.cash_position_report.cash_position_report.get_pawnshop_fund_transfer_totals',
		args: { branch: snapshot.branch, report_date: snapshot.date }
	}).then(response => ({
		cash_from_vault: flt((response.message || {}).cash_from_vault),
		cash_to_vault: flt((response.message || {}).cash_to_vault)
	}));
}

function get_subastado_sales(snapshot) {
	return frappe.db.get_list('Subastado Sales Commissions', {
		fields: ['mop_1','payment_1','mop_2','payment_2','comments'],
		filters: { date_bought_or_returned: snapshot.date, branch: snapshot.branch},
		limit: 500
	}).then(records => {
		let cash = 0;
		let gcashRet = 0;
		let gcash = 0;
		let bankTransRet = 0;
		let bankTrans = 0;
		for (let index = 0; index < records.length; index++) {

			//Do not include Subastado Sales with comments "Subasta"
			if(records[index].mop_1 == "Cash" && records[index].comments != "Subasta"){
				cash += parseFloat(records[index].payment_1) || 0;	
			}
			if(records[index].mop_2 == "Cash" && records[index].comments != "Subasta"){
				cash += parseFloat(records[index].payment_2) || 0;	
			}
			if(records[index].mop_1 == "Gcash" && records[index].comments != "Subasta"){
				if(records[index].payment_1 > 0){
					gcash += parseFloat(records[index].payment_1) || 0;		
				}else{
					gcashRet += parseFloat(records[index].payment_1 * -1) || 0;
					cash += parseFloat(records[index].payment_1) || 0;
				}
			}
			if(records[index].mop_2 == "Gcash" && records[index].comments != "Subasta"){
				if(records[index].payment_2 > 0){
					gcash += parseFloat(records[index].payment_2) || 0;		
				}else{
					gcashRet += parseFloat(records[index].payment_2 * -1) || 0;
					cash += parseFloat(records[index].payment_2) || 0;
				}
			}
			if((records[index].mop_1 == "BPI" || records[index].mop_1 == "BDO" || records[index].mop_1 == "EASTWEST") && records[index].comments != "Subasta"){
				if(records[index].payment_1 > 0){
					bankTrans += parseFloat(records[index].payment_1) || 0;
				}else{
					bankTransRet += parseFloat(records[index].payment_1 * -1) || 0;
					cash += parseFloat(records[index].payment_1) || 0;
				}
			}
			if((records[index].mop_2 == "BPI" || records[index].mop_2 == "BDO" || records[index].mop_2 == "EASTWEST") && records[index].comments != "Subasta"){
				if(records[index].payment_2 > 0){
					bankTrans += parseFloat(records[index].payment_2) || 0;
				}else{
					bankTransRet += parseFloat(records[index].payment_2 * -1) || 0;
					cash += parseFloat(records[index].payment_2) || 0;
				}
			}
		}
		return {
			selling: cash + gcash + bankTrans,
			gcash, gcash_positive: gcashRet,
			bank_transfer: bankTrans, bank_transfer_return: bankTransRet
		};
	});
}

function get_pr_mops(snapshot) {
	return frappe.db.get_list('Provisional Receipt', {
		fields: ['gcash_amount_payment', 'bank_payment', 'total', 'mode_of_payment'],
		filters: { date_issued: snapshot.date, branch: snapshot.branch, docstatus: 1 },
		limit: 500
	}).then(records => {
		let gcash = 0, bank_transfer = 0;
		for (const record of records) {
			if (record.mode_of_payment === 'GCash') {
				gcash += flt(record.total);
			} else if (['Cash & GCash', 'GCash & Bank Transfer'].includes(record.mode_of_payment)) {
				gcash += flt(record.gcash_amount_payment);
			}
			if (record.mode_of_payment === 'Bank Transfer') {
				bank_transfer += flt(record.total);
			} else if (['Cash & Bank Transfer', 'GCash & Bank Transfer'].includes(record.mode_of_payment)) {
				bank_transfer += flt(record.bank_payment);
			}
		}
		return { gcash, bank_transfer };
	});
}

async function total_cash_breakdown(frm) {
	const fields = [
		'one_thousand_php_bills', 'five_hundred_php_bills', 'two_hundred_php_bills',
		'one_hundred_php_bills', 'fifty_php_bills', 'twenty_php_bills',
		'ten_php_coin', 'five_php_coin', 'peso_php_coin', 'twenty_five_cent_php_coin'
	];
	const total = fields.reduce((sum, field) => sum + flt(frm.doc[field]), 0);
	await frm.set_value('total_cash', total);
	await frm.set_value('shortage_overage', total - flt(frm.doc.ending_balance));
}


async function select_naming_series(frm) { //Select naming series with regards to the branch
	if (frm.doc.branch == "Garcia's Pawnshop - BUC") {
		await frm.set_value('naming_series', "No.7-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - CC") {
		await frm.set_value('naming_series', "No.1-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - GTC") {
		await frm.set_value('naming_series', "No.4-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - MOL") {
		await frm.set_value('naming_series', "No.6-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - POB") {
		await frm.set_value('naming_series', "No.3-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - TNZ") {
		await frm.set_value('naming_series', "No.5-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - NOV") {
		await frm.set_value('naming_series', "No.8-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - PSC") {
		await frm.set_value('naming_series', "No.9-.######")
	} else if (frm.doc.branch == "TEST") {
		await frm.set_value('naming_series', "No-20-.######")
	}
}
