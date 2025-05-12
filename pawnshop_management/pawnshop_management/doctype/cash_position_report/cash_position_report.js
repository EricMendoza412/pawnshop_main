// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cash Position Report', {
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
		if (frm.is_new()) {
			frappe.call({
				method: 'pawnshop_management.pawnshop_management.custom_codes.get_ip.get_ip',
				callback: function(data){
					let current_ip = data.message

					frappe.db.get_list('Branch IP Addressing', {
						fields: ['name'],
						filters: {
							ip_address: current_ip
						}
					}).then(records => {

						console.log (records[0].name);
						frm.set_value('branch', records[0].name);
						frm.refresh_field('branch');
					})
				}
			})
			// frappe.db.get_list('Cash Position Report', {
			// 	fields: ['ending_balance', 'date', 'creation'],
			// 	filters: {
			// 		date: frappe.datetime.add_days(frm.doc.date, -1)
			// 	}
			// }).then(records => {
			// 	let latest_record = records[0]
			// 	for (let index = 0; index < records.length; index++) {
			// 		if (latest_record.creation < records[index].creation) {
			// 			latest_record = records[index]
			// 		}
			// 	}
			// 	frm.set_value('beginning_balance', 0.00)
			// 	frm.set_value('beginning_balance', latest_record.ending_balance)
			// 	frm.refresh_field('beginning_balance')
			// })
		}
		// frm.set_value('date', frappe.datetime.now_date())
		// frm.add_custom_button('Test', () => {
		// 	get_provisional_receipts_of_the_day(frm, '2022-02-09');
		// 	get_non_jewelry_of_the_day(frm, '2022-02-27')
		// 	frappe.db.get_list('Cash Position Report', {
		// 		fields: ['ending_balance', 'date', 'creation'],
		// 		filters: {
		// 			date: frm.doc.date
		// 		}
		// 	}).then(records => {
		// 		// for (let index = 0; index < records.length; index++) {
		// 		// 	frm.set_value('beginning_balance',records[index].ending_balance);
		// 		// 	frm.refresh_field('beginning_balance');
		// 		// }
		// 	})
		// })
	},

	branch: function(frm){
		get_beginning_balance(frm)
		get_provisional_receipts_of_the_day(frm, frm.doc.date);
		get_non_jewelry_of_the_day(frm, frm.doc.date);
		get_gcash_provisional_receipt(frm, frm.doc.date);
		get_ps_fund_transfers(frm, frm.doc.date);
		get_subastado_sales(frm, frm.doc.date);
		select_naming_series(frm);
		get_jewelry_ab_of_the_day(frm, frm.doc.date);
		get_ats_of_the_day(frm, frm.doc.date);
		get_ar_of_the_day(frm, frm.doc.date);
		//get_additional_pawn_records(frm);
		//get_additional_redeem(frm);
		//get_additional_partial_payment(frm);
		//get_total_discount(frm);
	},

	date: function(frm){
		get_beginning_balance(frm)
		get_provisional_receipts_of_the_day(frm, frm.doc.date);
		get_non_jewelry_of_the_day(frm, frm.doc.date);
		get_gcash_provisional_receipt(frm, frm.doc.date);
		get_ps_fund_transfers(frm, frm.doc.date);
		get_subastado_sales(frm, frm.doc.date);
		select_naming_series(frm);
		get_jewelry_ab_of_the_day(frm, frm.doc.date);
		get_ats_of_the_day(frm, frm.doc.date);
		get_ar_of_the_day(frm, frm.doc.date);
		//get_additional_pawn_records(frm);
		//get_additional_redeem(frm);
		//get_additional_partial_payment(frm);
		//get_total_discount(frm);
	},

	validate: function(frm){
		// if (frm.doc.total_cash != frm.doc.ending_balance) {
		// 	frappe.throw("Cash on hand is not equal to the Ending Balance")
		// }
		if (frm.doc.total_cash == 0){
			frappe.throw("Cash on hand should not be zero")
		}
	},

	after_save: function(frm) {
		if (frm.doc.docstatus === 1) { // Check if the document is submitted
			frappe.msgprint({
				message: __('Please do not forget to refresh and print the Transaction Log. <br><br> Thank you'),
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
		frm.set_value('ending_balance', 0.00);
		frm.set_value('ending_balance', calculate_ending_balance());
		frm.refresh_field('ending_balance');
	},

	provisional_receipts: function(frm){
		frm.set_value('total_in', 0.00);
		frm.set_value('total_in', + calculate_total_in());
		frm.refresh_field('total_in');
	},

	selling: function(frm){
		frm.set_value('total_in', 0.00);
		frm.set_value('total_in', + calculate_total_in());
		frm.refresh_field('total_in');
	},

	cash_from_vault: function(frm){
		frm.set_value('total_in', 0.00);
		frm.set_value('total_in', + calculate_total_in());
		frm.refresh_field('total_in');
	},

	gcash_positive: function(frm){
		frm.set_value('total_in', 0.00);
		frm.set_value('total_in', + calculate_total_in());
		frm.refresh_field('total_in');
	},

	bank_transfer_return: function(frm){
		frm.set_value('total_in', 0.00);
		frm.set_value('total_in', + calculate_total_in());
		frm.refresh_field('total_in');
	},

	jewelry_a: function(frm){
		frm.set_value('total_out', 0.00);
		frm.set_value('total_out', calculate_total_out());
		frm.refresh_field('total_out');
	},

	jewelry_b: function(frm){
		frm.set_value('total_out', 0.00);
		frm.set_value('total_out', calculate_total_out());
		frm.refresh_field('total_out');
	},

	non_jewelry: function(frm){
		frm.set_value('total_out', 0.00);
		frm.set_value('total_out', calculate_total_out());
		frm.refresh_field('total_out');
	},

	agreement_to_sell: function(frm){
		frm.set_value('total_out', 0.00);
		frm.set_value('total_out', calculate_total_out());
		frm.refresh_field('total_out');
	},

	acknowledgement_receipts: function(frm){
		frm.set_value('total_out', 0.00);
		frm.set_value('total_out', calculate_total_out());
		frm.refresh_field('total_out');
	},

	gcash: function(frm){
		frm.set_value('total_out', 0.00);
		frm.set_value('total_out', calculate_total_out());
		frm.refresh_field('total_out');
	},

	bank_transfer: function(frm){
		frm.set_value('total_out', 0.00);
		frm.set_value('total_out', calculate_total_out());
		frm.refresh_field('total_out');
	},

	cash_to_vault: function(frm){
		frm.set_value('total_out', 0.00);
		frm.set_value('total_out', calculate_total_out());
		frm.refresh_field('total_out');
	},

	total_in: function(frm){
		frm.set_value('net_cash', 0.00);
		frm.set_value('net_cash', calculate_net_cash());
		frm.refresh_field('net_cash');
	},
	
	total_out: function(frm){
		frm.set_value('net_cash', 0.00);
		frm.set_value('net_cash', calculate_net_cash());
		frm.refresh_field('net_cash');
	},

	net_cash: function(frm){
		frm.set_value('ending_balance', 0.00);
		frm.set_value('ending_balance', calculate_ending_balance());
		frm.refresh_field('ending_balance');
	},

	one_thousand_php_bills: function(frm){
		total_cash_breakdown(frm);
	},

	five_hundred_php_bills: function(frm){
		total_cash_breakdown(frm);
	},

	two_hundred_php_bills: function(frm){
		total_cash_breakdown(frm);
	},

	one_hundred_php_bills: function(frm){
		total_cash_breakdown(frm);
	},

	fifty_php_bills: function(frm){
		total_cash_breakdown(frm);
	},

	twenty_php_bills: function(frm){
		total_cash_breakdown(frm);
	},

	ten_php_coin: function(frm){
		total_cash_breakdown(frm);
	},

	five_php_coin: function(frm){
		total_cash_breakdown(frm);
	},

	peso_php_coin: function(frm){
		total_cash_breakdown(frm);
	},

	twenty_five_cent_php_coin: function(frm){
		total_cash_breakdown(frm);
	},

	shortage_overage: function(frm){
		//total_cash_breakdown(frm);
	}
});


function get_beginning_balance(frm) {
	frappe.call('pawnshop_management.pawnshop_management.custom_codes.get_latest_cpr.get_latest_cpr', {
		branch: frm.doc.branch
	}).then(record => {
		let beginning_balance = parseFloat(record.message);
		frm.set_value('beginning_balance', 0.00);
		console.log(beginning_balance + "pumasok dito");
		if(!isNaN(beginning_balance)){
			frm.set_value('beginning_balance', beginning_balance);
		}
		frm.refresh_field('beginning_balance');
	})
}

function calculate_total_in() {
	var total_in = parseFloat(cur_frm.doc.provisional_receipts) + parseFloat(cur_frm.doc.selling) + parseFloat(cur_frm.doc.cash_from_vault) + parseFloat(cur_frm.doc.gcash_positive) + parseFloat(cur_frm.doc.bank_transfer_return);
	return total_in;
}

function calculate_total_out(){
	var total_out = parseFloat(cur_frm.doc.jewelry_a) + parseFloat(cur_frm.doc.jewelry_b) + parseFloat(cur_frm.doc.cash_to_vault) + parseFloat(cur_frm.doc.non_jewelry) + parseFloat(cur_frm.doc.agreement_to_sell) + parseFloat(cur_frm.doc.acknowledgement_receipts) + parseFloat(cur_frm.doc.gcash) + parseFloat(cur_frm.doc.bank_transfer);
	return total_out;
}

function calculate_net_cash() {
	var net_cash = calculate_total_in() - calculate_total_out();
	return net_cash;
}

function calculate_ending_balance() {
	var ending_balance = parseFloat(cur_frm.doc.beginning_balance) + calculate_net_cash();
	return ending_balance;
}
function get_provisional_receipts_of_the_day(frm, date_today = null) {	
		frappe.call('pawnshop_management.pawnshop_management.custom_codes.daily_balance.get_all_PR_total', {
			date: frm.doc.date,
			branch: frm.doc.branch
		}).then(r => {
			frm.set_value('provisional_receipts', r.message);
			frm.refresh_field('provisional_receipts');
		})
}
function get_ats_of_the_day(frm, date_today = null) {
		frappe.call('pawnshop_management.pawnshop_management.custom_codes.daily_balance.get_all_ATS_total', {
			date: frm.doc.date,
			branch: frm.doc.branch
		}).then(r => {
			frm.set_value('agreement_to_sell', r.message);
			frm.refresh_field('agreement_to_sell');
		})
}
function get_ar_of_the_day(frm, date_today = null) {
	frappe.call('pawnshop_management.pawnshop_management.custom_codes.daily_balance.get_all_AR_total', {
		date: frm.doc.date,
		branch: frm.doc.branch
	}).then(r => {
		frm.set_value('acknowledgement_receipts', r.message);
		frm.refresh_field('acknowledgement_receipts');
	})
}
function get_jewelry_ab_of_the_day(frm, date_today=null) {
    frappe.db.get_list('Pawn Ticket Jewelry', {
        fields: ['net_proceeds','pawn_ticket','item_series'],
        filters: {
            date_loan_granted: date_today,
            branch: frm.doc.branch,
            old_pawn_ticket: '',
            docstatus: 1
        },
        limit: 500
    }).then(records => {
        let temp_total_a = 0.00;
		let temp_total_b = 0.00;
        frm.set_value('jewelry_a', 0.00);
		frm.set_value('jewelry_b', 0.00);
        
        // Create an array of promises
        let promises = records.map(record => {
            return frappe.db.get_list('Provisional Receipt', {
                fields: ['pawn_ticket_no', 'principal_amount', 'interest'],
                filters: {
                    transaction_type: 'Amortization',
                    pawn_ticket_no: record.pawn_ticket,
                    docstatus: 1
                }
            }).then(records2 => {
                if (records2.length > 0) {
					if(record.item_series == 'A'){
						temp_total_a += parseFloat(records2[0].principal_amount) - parseFloat(records2[0].interest);
					}else{
						if(record.item_series == 'B'){
							temp_total_b += parseFloat(records2[0].principal_amount) - parseFloat(records2[0].interest);
						}
					}
                }else{
					if(record.item_series == 'A'){
						temp_total_a += parseFloat(record.net_proceeds);
					}else{
						if(record.item_series == 'B'){
							temp_total_b += parseFloat(record.net_proceeds);
						}
					}
				}
            });
        });
        // Wait for all promises to resolve
        Promise.all(promises).then(() => {
            frm.set_value('jewelry_a', temp_total_a);
            frm.refresh_field('jewelry_a');
			frm.set_value('jewelry_b', temp_total_b);
            frm.refresh_field('jewelry_b');
        });
    });
}


function get_non_jewelry_of_the_day(frm, date_today=null) {
		frappe.db.get_list('Pawn Ticket Non Jewelry', {
			fields: ['net_proceeds','pawn_ticket'],
			filters: {
				date_loan_granted: date_today,
				branch: frm.doc.branch,
				old_pawn_ticket: '',
				docstatus: 1
			},
			limit: 500
		}).then(records => {
			let temp_total = 0.00;
			frm.set_value('non_jewelry', 0.00);

			        // Create an array of promises
        	let promises = records.map(record => {
				return frappe.db.get_list('Provisional Receipt', {
					fields: ['pawn_ticket_no', 'principal_amount', 'interest'],
					filters: {
						transaction_type: 'Amortization',
						pawn_ticket_no: record.pawn_ticket,
						docstatus: 1
					}
				}).then(records2 => {
					if (records2.length > 0) {
							temp_total += parseFloat(records2[0].principal_amount) - parseFloat(records2[0].interest);
					}else{
							temp_total += parseFloat(record.net_proceeds);
					}
				});
			});
			// Wait for all promises to resolve
			Promise.all(promises).then(() => {
				frm.set_value('non_jewelry', temp_total);
				frm.refresh_field('non_jewelry');
			});
		})
}

function get_ps_fund_transfers(frm, date_today=null) {
	frappe.db.get_list('Fund Transfer', {
		fields: ['ps_cashier_to_vc','vc_to_ps_cashier'],
		filters: { date_of_transfer: date_today,branch: frm.doc.branch},
		limit: 500
	}).then(records => {
		let psToVc = 0;
		let vcToPs = 0;
		for (let index = 0; index < records.length; index++) {
			psToVc += records[index].ps_cashier_to_vc
			vcToPs += records[index].vc_to_ps_cashier
		}
		frm.set_value('cash_to_vault', psToVc);
		frm.set_value('cash_from_vault', vcToPs);
		frm.refresh_field('cash_to_vault');
		frm.refresh_field('cash_from_vault');
	})
}

function get_subastado_sales(frm, date_today=null) {
	frappe.db.get_list('Subastado Sales Commissions', {
		fields: ['mop_1','payment_1','mop_2','payment_2'],
		filters: { date_bought_or_returned: date_today, branch: frm.doc.branch},
		limit: 500
	}).then(records => {
		let cash = 0;
		let gcashRet = 0;
		let gcash = 0;
		let bankTransRet = 0;
		let bankTrans = 0;
		for (let index = 0; index < records.length; index++) {
			if(records[index].mop_1 == "Cash"){
				cash += parseInt(records[index].payment_1);	
			}
			if(records[index].mop_2 == "Cash"){
				cash += parseInt(records[index].payment_2);	
			}
			if(records[index].mop_1 == "Gcash"){
				if(records[index].payment_1 > 0){
					gcash += parseInt(records[index].payment_1);		
				}else{
					gcashRet += parseInt((records[index].payment_1 * -1));
					cash += parseInt(records[index].payment_1);
				}
			}
			if(records[index].mop_2 == "Gcash"){
				if(records[index].payment_2 > 0){
					gcash += parseInt(records[index].payment_2);		
				}else{
					gcashRet += parseInt((records[index].payment_2 * -1));
					cash += parseInt(records[index].payment_2);
				}
			}
			if(records[index].mop_1 == "BPI" || records[index].mop_1 == "BDO" || records[index].mop_1 == "EASTWEST"){
				if(records[index].payment_1 > 0){
					bankTrans += parseInt(records[index].payment_1);
				}else{
					bankTransRet += parseInt((records[index].payment_1 * -1));
					cash += parseInt(records[index].payment_1);
				}
			}
			if(records[index].mop_2 == "BPI" || records[index].mop_2 == "BDO" || records[index].mop_2 == "EASTWEST"){
				if(records[index].payment_2 > 0){
					bankTrans += parseInt(records[index].payment_2);
				}else{
					bankTransRet += parseInt((records[index].payment_2 * -1));
					cash += parseInt(records[index].payment_2);
				}
			}
		}
		cash = cash + gcash + bankTrans
		frm.set_value('selling', cash);
		frm.set_value('gcash', gcash);
		frm.set_value('gcash_positive', gcashRet);
		frm.set_value('bank_transfer', bankTrans);
		frm.set_value('bank_transfer_return', bankTransRet);
		

		frm.refresh_field('selling');
		//frm.refresh_field('gcash');
		frm.refresh_field('gcash_positive');
		//frm.refresh_field('bank_transfer');
		frm.refresh_field('bank_transfer_return');
		get_pr_mops(frm, date_today );
	})
}

function get_pr_mops(frm, date_today=null){
	frappe.db.get_list('Provisional Receipt', {
		fields: ['gcash_amount_payment','bank_payment','total','mode_of_payment'],
		filters: { 
				date_issued: date_today, 
				branch: frm.doc.branch,
				docstatus: 1,
				},
		limit: 500
	}).then(records => {
		let gcash2 = 0;
		let bankTrans2 = 0;
		for (let index = 0; index < records.length; index++) {
				gcash2 += parseInt(records[index].gcash_amount_payment);	
				bankTrans2 += parseInt(records[index].bank_payment);
				
				if(records[index].mode_of_payment == "GCash"){
					gcash2 += records[index].total
				}
				if(records[index].mode_of_payment == "Bank Transfer"){
					bankTrans2 += records[index].total
				}

		}
		
		gcash2 += parseInt(frm.doc.gcash);
		bankTrans2 += parseInt(frm.doc.bank_transfer);
		console.log(gcash2)

		frm.set_value('gcash', gcash2);
		frm.set_value('bank_transfer', bankTrans2);

		frm.refresh_field('gcash');
		frm.refresh_field('bank_transfer');
	})


}

function total_cash_breakdown(frm) {
	let total_cash_breakdown = 0.00
	let thousand_bill = parseFloat(frm.doc.one_thousand_php_bills);
	let five_hundred_bill = parseFloat(frm.doc.five_hundred_php_bills);
	let two_hundred_bill = parseFloat(frm.doc.two_hundred_php_bills);
	let one_hundred_bill = parseFloat(frm.doc.one_hundred_php_bills);
	let fifty_bill = parseFloat(frm.doc.fifty_php_bills);
	let twenty_bill = parseFloat(frm.doc.twenty_php_bills);
	let ten_peso_coin = parseFloat(frm.doc.ten_php_coin);
	let five_peso_coin = parseFloat(frm.doc.five_php_coin);
	let one_peso_coin = parseFloat(frm.doc.peso_php_coin);
	let twenty_five_cents = parseFloat(frm.doc.twenty_five_cent_php_coin);
	total_cash_breakdown = thousand_bill + five_hundred_bill + two_hundred_bill + one_hundred_bill + fifty_bill + twenty_bill + ten_peso_coin + five_peso_coin + one_peso_coin + twenty_five_cents;

	let ending_balance = parseFloat(frm.doc.ending_balance);
	let shortage_overage = 0.00;
	if (total_cash_breakdown != ending_balance) {
		if (total_cash_breakdown > ending_balance) {
			shortage_overage = total_cash_breakdown - ending_balance;
			frm.set_value('shortage_overage', shortage_overage);
			frm.refresh_field('shortage_overage');
		} else if (total_cash_breakdown < ending_balance) {
			shortage_overage = total_cash_breakdown - ending_balance;
			frm.set_value('shortage_overage', shortage_overage);
			frm.refresh_field('shortage_overage');
		} 
	} else {
		frm.set_value('shortage_overage', 0.00);
		frm.refresh_field('shortage_overage');
	}

	

	frm.set_value('total_cash', total_cash_breakdown);
	frm.refresh_field('total_cash');
}


function select_naming_series(frm) { //Select naming series with regards to the branch
	if (frm.doc.branch == "Garcia's Pawnshop - ALP") {
		frm.set_value('naming_series', "No.7-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - CC") {
		frm.set_value('naming_series', "No.1-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - GTC") {
		frm.set_value('naming_series', "No.4-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - MOL") {
		frm.set_value('naming_series', "No.6-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - POB") {
		frm.set_value('naming_series', "No.3-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - TNZ") {
		frm.set_value('naming_series', "No.5-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - NOV") {
		frm.set_value('naming_series', "No.8-.######")
	} else if (frm.doc.branch == "TEST") {
		frm.set_value('naming_series', "No-20-.######")
	}
}


function get_gcash_provisional_receipt(frm, date_today = null) {
	if (frm.doc.branch == "Rabie's House") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Rabie's House",
				mode_of_payment: "GCash"
			}
		}).then(records => {
			let temp_total = 0.00;
			//frm.set_value('gcash', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			//frm.set_value('gcash', temp_total);
			frm.refresh_field('gcash');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - TNZ") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - TNZ",
				mode_of_payment: "GCash"
			}
		}).then(records => {
			let temp_total = 0.00;
			// frm.set_value('gcash', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			//frm.set_value('gcash', temp_total);
			frm.refresh_field('gcash');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - POB") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - POB",
				mode_of_payment: "GCash"
			}
		}).then(records => {
			let temp_total = 0.00;
			//frm.set_value('gcash', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			//frm.set_value('gcash', temp_total);
			frm.refresh_field('gcash');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - MOL") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - MOL",
				mode_of_payment: "GCash"
			}
		}).then(records => {
			let temp_total = 0.00;
			//frm.set_value('gcash', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			//frm.set_value('gcash', temp_total);
			frm.refresh_field('gcash');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - GTC") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - GTC",
				mode_of_payment: "GCash"
			}
		}).then(records => {
			let temp_total = 0.00;
			//frm.set_value('gcash', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			//frm.set_value('gcash', temp_total);
			frm.refresh_field('gcash');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - CC") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - CC",
				mode_of_payment: "GCash"
			}
		}).then(records => {
			let temp_total = 0.00;
			//frm.set_value('gcash', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			//frm.set_value('gcash', temp_total);
			frm.refresh_field('gcash');
		})
	}
}

function get_bank_transfer_provisional_receipt(frm, date_today = null) {
	if (frm.doc.branch == "Rabie's House") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Rabie's House",
				mode_of_payment: "Bank Transfer"
			}
		}).then(records => {
			let temp_total = 0.00;
			frm.set_value('bank_transfer', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			//frm.set_value('gcash', temp_total);
			frm.refresh_field('bank_transfer');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - TNZ") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - TNZ",
				mode_of_payment: "Bank Transfer"
			}
		}).then(records => {
			let temp_total = 0.00;
			frm.set_value('bank_transfer', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			frm.set_value('bank_transfer', temp_total);
			frm.refresh_field('bank_transfer');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - POB") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - POB",
				mode_of_payment: "Bank Transfer"
			}
		}).then(records => {
			let temp_total = 0.00;
			frm.set_value('bank_transfer', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			frm.set_value('bank_transfer', temp_total);
			frm.refresh_field('bank_transfer');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - MOL") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - MOL",
				mode_of_payment: "Bank Transfer"
			}
		}).then(records => {
			let temp_total = 0.00;
			frm.set_value('bank_transfer', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			frm.set_value('bank_transfer', temp_total);
			frm.refresh_field('bank_transfer');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - GTC") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - GTC",
				mode_of_payment: "Bank Transfer"
			}
		}).then(records => {
			let temp_total = 0.00;
			frm.set_value('bank_transfer', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			frm.set_value('bank_transfer', temp_total);
			frm.refresh_field('bank_transfer');
		})
	} else if (frm.doc.branch == "Garcia's Pawnshop - CC") {
		frappe.db.get_list('Provisional Receipt', {
			fields: ['total'],
			filters: {
				date_issued: date_today,
				docstatus: 1,
				branch: "Garcia's Pawnshop - CC",
				mode_of_payment: "Bank Transfer"
			}
		}).then(records => {
			let temp_total = 0.00;
			frm.set_value('bank_transfer', 0.00);
			for (let index = 0; index < records.length; index++) {
				temp_total += parseFloat(records[index].total)
			}
			frm.set_value('bank_transfer', temp_total);
			frm.refresh_field('bank_transfer');
		})
	}
}