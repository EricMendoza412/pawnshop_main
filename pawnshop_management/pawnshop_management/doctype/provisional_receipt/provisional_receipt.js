// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt


//global variables
var branch_code_no;
var with_other_discount = false;
var og_total_no_discount;

frappe.ui.form.on('Provisional Receipt', {

	onload: function(frm) {
		frm.toggle_display(['pawn_ticket_no'], frm.doc.pawn_ticket_type !== "-Select-");
		frm.set_df_property('pawn_ticket_type', 'hidden', 1)
		frm.set_df_property('discount', 'hidden', 1)
		frm.set_df_property('additional_amortization', 'hidden', 1)
		if (frm.is_new()) {
			if(frm.doc.amended_from == null){
			frm.set_df_property('mode_of_payment', 'hidden', 1)
			}
		}
		frm.set_df_property('subasta_sales_no', 'hidden', 1)
		frm.set_df_property('other_discount', 'hidden', 1);
		frm.set_df_property('other_discount_tawad', 'hidden', 1);
		frm.set_df_property('other_discount_st', 'hidden', 1);
		frm.set_query('pawn_ticket_no', () => {
			return {
				"filters": {
					"workflow_state": ['in',['Active','Returned','Expired']],
					"branch": frm.doc.branch
				}
			}
		})
		with_other_discount = false;
		og_total_no_discount = null;
	},

	validate: function(frm){

		if (frm.doc.mode_of_payment == "-Select-"){
			frappe.throw('Please select mode of payment')
		}
		if (frm.doc.transaction_type == null || frm.doc.transaction_type == "-Select-") {
			frappe.throw('Please select transaction type');
		}

		if (frm.doc.transaction_type == "Renewal w/ Amortization" || frm.doc.transaction_type == "Amortization") {
			if (frm.doc.additional_amortization <= 0 || frm.doc.additional_amortization == null) {
				frappe.throw('Unable to proceed because Additional Amortization field is either empty or is equal to 0');
			}
		}

		if(frm.doc.mode_of_payment === 'Bank Transfer' || frm.doc.mode_of_payment === 'Cash & Bank Transfer' || frm.doc.mode_of_payment === 'GCash & Bank Transfer'){
			if(frm.doc.bank == "-Select-"){
				frappe.throw('Please select bank');
			}
		}

			if (frm.doc.mode_of_payment == "Cash & GCash") {
				if (frm.doc.total != parseFloat(frm.doc.cash) + parseFloat(frm.doc.gcash_amount_payment)) {
					frappe.throw('Payment breakdown does not match total')
				}
			} else if (frm.doc.mode_of_payment == "Cash & Bank Transfer") {
				if (frm.doc.total != parseFloat(frm.doc.cash) + parseFloat(frm.doc.bank_payment)) {
					frappe.throw('Payment breakdown does not match total')
				}
			} else if (frm.doc.mode_of_payment == "GCash & Bank Transfer") {
				if (frm.doc.total != parseFloat(frm.doc.gcash_amount_payment) + parseFloat(frm.doc.bank_payment)) {
					frappe.throw('Payment breakdown does not match total')
				}
			}
		
	},

	refresh: function(frm) {
		frm.toggle_display(['bank'], frm.doc.mode_of_payment === 'Bank Transfer' || frm.doc.mode_of_payment === 'Cash & Bank Transfer' || frm.doc.mode_of_payment === 'GCash & Bank Transfer');
		frm.toggle_display(['bank_payment'], frm.doc.mode_of_payment === 'Cash & Bank Transfer' || frm.doc.mode_of_payment === 'GCash & Bank Transfer');
		frm.toggle_display(['cash'], frm.doc.mode_of_payment === 'Cash & Bank Transfer' || frm.doc.mode_of_payment === 'Cash & GCash');
		frm.toggle_display(['gcash_amount_payment'], frm.doc.mode_of_payment === 'GCash & Bank Transfer' || frm.doc.mode_of_payment === 'Cash & GCash');
		let is_allowed = frappe.user_roles.includes('Administrator');
		frm.toggle_enable(['date_loan_granted' ,'expiry_date', 'maturity_date', 'branch', 'new_pawn_ticket_no'], is_allowed);
		if (frm.doc.discount > 0 ) {
			frm.set_df_property('discount', 'hidden', 0)
		}

		if (frm.doc.additional_amortization > 0) {
			frm.set_df_property('additional_amortization', 'hidden', 0)
		}

		if (frm.doc.transaction_type == 'Interest Payment' && frm.doc.docstatus == 1) {
			frm.set_df_property('interest_payment', 'hidden', 1);
			frm.set_df_property('discount', 'hidden', 1);
			frm.set_df_property('additional_amortization', 'hidden', 1);
			frm.set_df_property('advance_interest', 'hidden', 1);
		}

		if (frm.doc.transaction_type == 'Others' && frm.doc.docstatus == 1) {
			frm.set_df_property('subasta_sales_no', 'hidden', 0);
			frm.set_df_property('advance_interest', 'hidden', 1);
			frm.set_df_property('interest_payment', 'hidden', 1);
			frm.set_df_property('principal_amount', 'hidden', 1);
			frm.set_df_property('interest', 'hidden', 1);
			frm.set_df_property('amortization', 'hidden', 1);
			frm.set_df_property('previous_interest_payment', 'hidden', 1);
		}


		frm.toggle_display(['new_pawn_ticket_no'], (frm.doc.docstatus == 1 && frm.doc.new_pawn_ticket_no != ""))
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
		}
	},

	branch: function(frm){
		select_naming_series(frm);
	},

	maturity_date: function(frm){

		if (frm.doc.date_issued >= frm.doc.maturity_date) {
			if(frm.doc.transaction_type == "Amortization"){
					let dialog = new frappe.msgprint({
						title: 'Amortization not allowed',
						message: 'Date today is already AFTER Pawn Ticket maturity date.',
						indicator: 'red'
						});
					dialog.show();
					dialog.onhide = function() {
						location.reload();
					}
			}
		} else{
		   if (frm.doc.transaction_type == "Interest Payment") {
					let dialog = new frappe.msgprint({
						title: 'Interest Payment not allowed',
						message: 'Date today is still BEFORE Pawn Ticket maturity date.',
						indicator: 'red'
						});
					dialog.show();
					dialog.onhide = function() {
						location.reload();
					}
			}
		}
	},

	other_discount: function(frm){
		let new_total = frm.doc.total;
		frm.set_value('other_discount_tawad', frm.doc.interest);
		if(frm.doc.other_discount != "None"){
			if(!with_other_discount){
				frm.set_df_property('other_discount_tawad', 'hidden', 0);
				new_total -= frm.doc.interest;
				with_other_discount = true;
			}
		}else{
			frm.set_df_property('other_discount_tawad', 'hidden', 1);
			new_total += frm.doc.interest;
			with_other_discount = false;
		}

		frm.set_value('total', new_total);
		frm.refresh_field('total');
	},

	total: function(frm){
		//initialize original total with no discount for short term computation
		if(og_total_no_discount == null){
			og_total_no_discount = frm.doc.total;
		}
	},

	other_discount_st: function(frm){
		console.log(og_total_no_discount);
		let discount_amount;
		if(frm.doc.other_discount_st == "3%"){
			frm.set_df_property('discount', 'hidden', 0);
			discount_amount = frm.doc.principal_amount * 0.03;
		}else if(frm.doc.other_discount_st == "4%"){
			frm.set_df_property('discount', 'hidden', 0);
			discount_amount = frm.doc.principal_amount * 0.04;
		}else if(frm.doc.other_discount_st == "None"){
			frm.set_df_property('discount', 'hidden', 1);
			discount_amount = 0;
		}
		frm.set_value('discount', discount_amount);
		frm.set_value('total', og_total_no_discount - discount_amount);
		frm.refresh_field('total');
		frm.refresh_field('discount');
	},

	pawn_ticket_type: function(frm){
		frm.toggle_display(['pawn_ticket_no'], frm.doc.pawn_ticket_type !== "-Select-");
		frm.set_df_property('pawn_ticket_type', 'read_only', 1);
		show_fields_for_dummy(frm);
		if(frm.doc.pawn_ticket_type == "Subastado Sales Commissions"){
			frm.set_df_property('pawn_ticket_no', 'hidden', 1);
			frm.set_df_property('subasta_sales_no', 'hidden', 0);
			frm.set_df_property('subasta_sales_no', 'reqd', 1);
		}else{
			frm.set_df_property('pawn_ticket_no', 'reqd', 1);
		}

	},

	subasta_sales_no: function(frm){
		frm.toggle_display(['mode_of_payment'], frm.doc.pawn_ticket_no !== '');
	},

	pawn_ticket_no: function(frm){
		frm.toggle_display(['mode_of_payment'], frm.doc.pawn_ticket_no !== '');
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: frm.doc.pawn_ticket_type, // Replace with the actual doctype of your document
				filters: {
					name: frm.doc.pawn_ticket_no // Replace with the actual name of your document
				},
				fieldname: ['workflow_state','branch']
			},
			callback: function(response) {
				var workflowState = response.message.workflow_state;
				var branch = response.message.branch;

						if(frm.doc.transaction_type != "Others"){
							if(!((workflowState == "Active" || workflowState == "Expired" || workflowState == "Returned")&&(branch == frm.doc.branch))){
								if (workflowState != null){
									location.reload();
									}
								}
						}

							frm.set_df_property('pawn_ticket_no', 'read_only', 1);
							frm.clear_table('items');
							show_items(frm.doc.pawn_ticket_type, frm.doc.pawn_ticket_no);
							frm.refresh_field('items');

							if(frm.doc.transaction_type == 'Renewal' || frm.doc.transaction_type == 'Renewal w/ Amortization'){
								get_new_pawn_ticket_no(frm);
							}


							frappe.db.get_list('Provisional Receipt', {
								fields: ['additional_amortization','total','transaction_type'],
								filters: {
									pawn_ticket_type: frm.doc.pawn_ticket_type,
									transaction_type: ['in',['Interest Payment','Amortization']],
									pawn_ticket_no: frm.doc.pawn_ticket_no,
									docstatus: 1
								} 
							}).then(records => {
								
								let total_amortizations = 0.00;
								let temp_previous_interest_payment = 0.00

								for (let index = 0; index < records.length; index++) {
									
									if(records[index].transaction_type == 'Amortization'){
											total_amortizations += parseFloat(records[index].additional_amortization);
										}else{
											temp_previous_interest_payment += parseFloat(records[index].total);
										}

								}
								frm.set_value('previous_interest_payment', temp_previous_interest_payment);
								frm.set_value('amortization', total_amortizations);
								
								frm.refresh_field('previous_interest_payment');
								frm.refresh_field('amortization');

								if(frm.doc.transaction_type != "Others"){
									calculate_interest(frm);
								}
								
								var word = String(frm.doc.complete_name).lastIndexOf("Dummy");
								console.log(word);
								show_fields_for_dummy(frm)
							})
				}
			});
	},

	complete_name: function(frm){
		show_fields_for_dummy(frm)		
	},

	transaction_type: function(frm){
		if(frm.doc.transaction_type != "-Select-"){
		frm.set_df_property('transaction_type', 'read_only', 1)
		}
		frm.toggle_display(['pawn_ticket_type'], frm.doc.transaction_type !== "-Select-");
		frm.toggle_display(['new_pawn_ticket_no'], frm.doc.transaction_type == 'Renewal' || frm.doc.transaction_type == 'Renewal w/ Amortization');
		show_fields_for_dummy(frm);
		frm.set_value('bank_payment', 0.00);
		frm.set_value('gcash_amount_payment', 0.00);
		frm.set_value('cash', 0.00);
		frm.refresh_field('bank_payment');
		frm.refresh_field('gcash_amount_payment');
		frm.refresh_field('cash');
		frm.set_df_property('pawn_ticket_type', 'options', ['-Select-','Pawn Ticket Jewelry', 'Pawn Ticket Non Jewelry']);
		if (frm.doc.transaction_type == "Amortization") {
			show_payment_fields(frm);
			frm.set_df_property('interest_payment', 'hidden', 1);
			frm.set_df_property('advance_interest', 'hidden', 1);
			frm.set_df_property('number_of_months_to_pay_in_advance', 'hidden', 1);
		} else if(frm.doc.transaction_type == "Interest Payment") {
			show_payment_fields(frm);
			frm.set_df_property('interest_payment', 'hidden', 1);
			frm.set_df_property('additional_amortization', 'hidden', 1);
			frm.set_df_property('advance_interest', 'hidden', 1);
		} else if(frm.doc.transaction_type == "Redemption") {
			show_payment_fields(frm);
			frm.set_df_property('additional_amortization', 'hidden', 1);
			frm.set_df_property('advance_interest', 'hidden', 1);
			frm.set_df_property('number_of_months_to_pay_in_advance', 'hidden', 1);
		} else if (frm.doc.transaction_type == "Renewal") {
			show_payment_fields(frm);
			frm.set_df_property('additional_amortization', 'hidden', 1);
			frm.set_df_property('number_of_months_to_pay_in_advance', 'hidden', 1);
		} else if (frm.doc.transaction_type == "Renewal w/ Amortization") {
			show_payment_fields(frm);
			frm.set_df_property('number_of_months_to_pay_in_advance', 'hidden', 1);
		} else if (frm.doc.transaction_type == "Others"){
			show_payment_fields(frm);
			frm.set_df_property('pawn_ticket_type', 'options', ['-Select-','Pawn Ticket Jewelry', 'Pawn Ticket Non Jewelry','Subastado Sales Commissions']);
			frm.refresh_field('transaction_type');
			frm.set_df_property('interest_payment', 'hidden', 1);
			frm.set_df_property('advance_interest', 'hidden', 1);
			frm.set_df_property('additional_amortization', 'hidden', 1);
			frm.set_df_property('number_of_months_to_pay_in_advance', 'hidden', 1);
			frm.set_df_property('total', 'read_only', 0);
			frm.set_query('pawn_ticket_no', () => {
				return {"filters": {}}
				})
		}

	},

	mode_of_payment: function(frm){
		frm.set_value('bank_payment', 0.00);
		frm.set_value('gcash_amount_payment', 0.00);
		frm.set_value('cash', 0.00);
		frm.refresh_field('bank_payment');
		frm.refresh_field('gcash_amount_payment');
		frm.refresh_field('cash');
		frm.toggle_display(['bank'], frm.doc.mode_of_payment === 'Bank Transfer' || frm.doc.mode_of_payment === 'Cash & Bank Transfer' || frm.doc.mode_of_payment === 'GCash & Bank Transfer');
		frm.toggle_display(['bank_payment'], frm.doc.mode_of_payment === 'Cash & Bank Transfer' || frm.doc.mode_of_payment === 'GCash & Bank Transfer');
		frm.toggle_display(['cash'], frm.doc.mode_of_payment === 'Cash & Bank Transfer' || frm.doc.mode_of_payment === 'Cash & GCash');
		frm.toggle_display(['gcash_amount_payment'], frm.doc.mode_of_payment === 'GCash & Bank Transfer' || frm.doc.mode_of_payment === 'Cash & GCash');
		frm.toggle_display(['gcash_ref'], frm.doc.mode_of_payment === 'GCash' || frm.doc.mode_of_payment === 'GCash & Bank Transfer' || frm.doc.mode_of_payment === 'Cash & GCash');
		if(frm.doc.mode_of_payment === 'GCash' || frm.doc.mode_of_payment === 'GCash & Bank Transfer' || frm.doc.mode_of_payment === 'Cash & GCash'){
			frm.set_df_property('gcash_ref', 'reqd', 1)
		}else{
			frm.set_df_property('gcash_ref', 'reqd', 0)
		}
	},

	additional_amortization: function(frm){
		if (frm.doc.transaction_type == "Renewal w/ Amortization") {
			calculate_new_interest(frm);
			frm.set_value('total', (parseFloat(frm.doc.additional_amortization) + parseFloat(frm.doc.interest_payment) + parseFloat(frm.doc.advance_interest)) - parseFloat(frm.doc.discount) - parseFloat(frm.doc.previous_interest_payment));
			frm.refresh_field('total');
		} else if (frm.doc.transaction_type == "Amortization") {
			frm.set_value('total', parseFloat(frm.doc.additional_amortization));
			frm.refresh_field('total');
		}
	},

	advance_interest: function(frm){
		frm.set_value('total', (parseFloat(frm.doc.additional_amortization) + parseFloat(frm.doc.interest_payment)) - parseFloat(frm.doc.discount) + parseFloat(frm.doc.advance_interest) - parseFloat(frm.doc.previous_interest_payment));
		frm.refresh_field('total');
	},

	number_of_months_to_pay_in_advance: function(frm){
		let partial_interest_payment = parseFloat(frm.doc.interest) * parseInt(frm.doc.number_of_months_to_pay_in_advance);
		frm.set_value('total', partial_interest_payment);
		frm.refresh_field('total');

	},

	interest_payment: function(frm){
		if (frm.doc.transaction_type == "Amortization" ) {
			frm.set_value('total', (parseFloat(frm.doc.additional_amortization) + parseFloat(frm.doc.interest_payment)) + parseFloat(frm.doc.advance_interest));
			frm.refresh_field('total');
		} else if (frm.doc.transaction_type == "Redemption") {
			frm.set_value('total', (parseFloat(frm.doc.principal_amount) + parseFloat(frm.doc.interest_payment)) + parseFloat(frm.doc.advance_interest) - parseFloat(frm.doc.previous_interest_payment));
			frm.refresh_field('total');
		} else if (frm.doc.transaction_type == "Renewal") {
			frm.set_value('total', (parseFloat(frm.doc.interest_payment) + parseFloat(frm.doc.advance_interest)) - parseFloat(frm.doc.previous_interest_payment));
			frm.refresh_field('total');
			if(frm.doc.interest_payment > 0){
				frm.set_df_property('other_discount', 'hidden', 0);
			}
		} else if (frm.doc.transaction_type == "Renewal w/ Amortization") {
			frm.set_value('total', (parseFloat(frm.doc.additional_amortization) + parseFloat(frm.doc.interest_payment)) + parseFloat(frm.doc.advance_interest) - parseFloat(frm.doc.previous_interest_payment));
			frm.refresh_field('total');
			if(frm.doc.interest_payment > 0){
				frm.set_df_property('other_discount', 'hidden', 0);
			}
		}
	},

	number_of_months_to_pay_in_advance: function(frm){
		frm.set_value('total', frm.doc.number_of_months_to_pay_in_advance * frm.doc.interest);
		frm.refresh_field('total');
	},

	cash: function(frm){
		if (frm.doc.transaction_type == "Amortization" || frm.doc.transaction_type == "Renewal w/ Amortization") {
			frm.set_value('additional_amortization', parseFloat(frm.doc.cash) + parseFloat(frm.doc.gcash_amount_payment) + parseFloat(frm.doc.bank_payment))
			frm.refresh_field('additional_amortization')
		}
	},

	gcash_amount_payment: function(frm){
		if (frm.doc.transaction_type == "Amortization" || frm.doc.transaction_type == "Renewal w/ Amortization") {
			frm.set_value('additional_amortization', parseFloat(frm.doc.cash) + parseFloat(frm.doc.gcash_amount_payment) + parseFloat(frm.doc.bank_payment))
			frm.refresh_field('additional_amortization')
		}
	},

	bank_payment: function(frm){
		if (frm.doc.transaction_type == "Amortization" || frm.doc.transaction_type == "Renewal w/ Amortization") {
			frm.set_value('additional_amortization', parseFloat(frm.doc.cash) + parseFloat(frm.doc.gcash_amount_payment) + parseFloat(frm.doc.bank_payment))
			frm.refresh_field('additional_amortization')
		} 
	}
});

frappe.ui.form.on('Jewelry List', {

	item_no: function(frm, cdt, cdn){
		let table_length = parseInt(frm.doc.actual_items_j.length)
		if (frm.doc.actual_items_j.length > 1) {
			for (let index = 0; index < table_length - 1; index++) {
				if (frm.doc.actual_items_j[table_length-1].item_no == frm.doc.actual_items_j[index].item_no) {
					frm.doc.actual_items_j.pop(table_length-1);
					frm.refresh_field('actual_items_j');
					frappe.msgprint({
						title:__('Notification'),
						indicator:'red',
						message: __('Added item is already in the list. Item removed.')
					});
					//set_total_appraised_amount(frm, cdt, cdn);
				}
			}
		}	

		
	},
	actual_items_j_add: function(frm, cdt, cdn){
		let table_length = parseInt(frm.doc.actual_items_j.length)
		if (table_length > 4) {
			frm.fields_dict["actual_items_j"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "hidden";
		}
	},


	actual_items_j_remove: function(frm, cdt, cdn){ //calculate appraisal value when removing items
		let table_length = parseInt(frm.doc.actual_items_j.length)
		//set_total_appraised_amount(frm, cdt, cdn);
		if (table_length <= 4) {
			frm.fields_dict["actual_items_j"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "visible";
		}
	}
});

frappe.ui.form.on('Non Jewelry List', {
	item_no: function(frm, cdt, cdn){
		let table_length = parseInt(frm.doc.actual_items_nj.length)
		if (frm.doc.actual_items_nj.length > 1) {
			// for (let index = 0; index < table_length - 1; index++) {
			// 	if (frm.doc.non_jewelry_items[table_length-1].item_no == frm.doc.non_jewelry_items[index].item_no) {
			// 		frm.doc.non_jewelry_items.pop(table_length-1);
			// 		frm.refresh_field('actual_items_nj');
			// 		frappe.msgprint({
			// 			title:__('Notification'),
			// 			indicator:'red',
			// 			message: __('Added item is already in the list. Item removed.')
			// 		});
			// 		set_total_appraised_amount(frm, cdt, cdn);
			// 	}
			// }
		}	
	},

	// suggested_appraisal_value: function(frm, cdt, cdn){
	// 	set_total_appraised_amount(frm,cdt, cdn);
	// },

	actual_items_nj_remove: function(frm, cdt, cdn){
		//set_total_appraised_amount(frm, cdt, cdn);
		frm.fields_dict["actual_items_nj"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "visible";
	},

	actual_items_nj_add: function(frm, cdt, cdn){
		frm.fields_dict["actual_items_nj"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "hidden";
	}
});

function show_fields_for_dummy(frm) {
	frm.set_value('customer_name', "  ");
	frm.refresh_field('customer_name');
	var word = String(frm.doc.complete_name).lastIndexOf("Dummy");
	frm.toggle_display(['customer_tracking_no', 'customer_name'], word != -1 && (frm.doc.transaction_type == 'Renewal' || frm.doc.transaction_type == 'Renewal w/ Amortization'))
	frm.toggle_display(['actual_items_j'], word != -1 && frm.doc.pawn_ticket_type == 'Pawn Ticket Jewelry' && (frm.doc.transaction_type == 'Renewal' || frm.doc.transaction_type == 'Renewal w/ Amortization'))
	frm.toggle_display(['actual_items_nj'], word != -1 && frm.doc.pawn_ticket_type == 'Pawn Ticket Non Jewelry' && (frm.doc.transaction_type == 'Renewal' || frm.doc.transaction_type == 'Renewal w/ Amortization'))
	if (frm.doc.pawn_ticket_type == 'Pawn Ticket Jewelry') {
		cur_frm.clear_table('actual_items_nj')
		frm.refresh_field('actual_items_nj')
		if(word != -1 && (frm.doc.transaction_type == 'Renewal' || frm.doc.transaction_type == 'Renewal w/ Amortization')) {
			frm.toggle_reqd('actual_items_j', true)
			frm.toggle_reqd('customer_tracking_no', true)
		}
	} else if (frm.doc.pawn_ticket_type == 'Pawn Ticket Non Jewelry') {
		cur_frm.clear_table('actual_items_j')
		frm.refresh_field('actual_items_j')
		if(word != -1 && (frm.doc.transaction_type == 'Renewal' || frm.doc.transaction_type == 'Renewal w/ Amortization')) {
		frm.toggle_reqd('actual_items_nj', true)
		frm.toggle_reqd('customer_tracking_no', true)
		}
	}
}

function show_payment_fields(frm) {
	frm.set_df_property('amortization', 'hidden', 0);
	frm.set_df_property('interest_payment', 'hidden', 0);
	frm.set_df_property('additional_amortization', 'hidden', 0);
	frm.set_df_property('advance_interest', 'hidden', 0)
	frm.set_df_property('number_of_months_to_pay_in_advance', 'hidden', 0)
}

function calculate_interest(frm) {
	frm.set_value('interest_payment', 0.00);
	frm.refresh_field('interest_payment');
	
	var date_today = frm.doc.date_issued;											//frappe.datetime.get_today()
	if (date_today > frm.doc.maturity_date && date_today < frm.doc.expiry_date) {
		calculate_maturity_date_interest(frm);
		console.log("F1");
	} else if (date_today >= frm.doc.expiry_date) {
		calculate_expiry_date_interest(frm);
		console.log("F2");
	} else if (date_today <= frm.doc.maturity_date){
		calculate_total_amount(frm);
	}
}

function calculate_total_amount(frm){

	if (frm.doc.transaction_type == "Redemption") {
		frm.set_value('total', parseFloat(frm.doc.interest_payment) + parseFloat(frm.doc.principal_amount) - parseFloat(frm.doc.previous_interest_payment) - parseFloat(frm.doc.discount));
		frm.refresh_field('total');
		if(frm.doc.interest_payment == 0){
			console.log("dito pumasok");
			frm.set_df_property('other_discount_st', 'hidden', 0);
			frm.set_df_property('other_discount', 'hidden', 1);
		}else{
			console.log("2nd pasok");
			frm.set_df_property('other_discount', 'hidden', 0);
			frm.set_df_property('other_discount_st', 'hidden', 1);
		}
	} else if (frm.doc.transaction_type == "Renewal w/ Amortization") {
		if (frm.doc.additional_amortization == 0) {
			frm.set_value('advance_interest', frm.doc.interest);
			frm.refresh_field('advance_interest');
		}
	} else if(frm.doc.transaction_type == "Renewal"){
		frm.set_value('advance_interest', parseFloat(frm.doc.interest));
		frm.refresh_field('advance_interest');
		frm.set_value('total', parseFloat(frm.doc.interest_payment) + parseFloat(frm.doc.advance_interest) - parseFloat(frm.doc.previous_interest_payment));
		frm.refresh_field('total');
	}
}

function calculate_maturity_date_interest(frm) {
	frappe.db.get_doc('Holiday List', 'No Operations').then(function(r){
		var holidays_list = r.holidays;
		var holidays_before_maturity_date = null;
		var temp_maturity_date = maturity_date_of_the_month(frm)
		var multiplier = calculate_date_difference(frm.doc.date_issued, frm.doc.maturity_date).months + 1
		var temp_interest = frm.doc.interest;
		var date_today = frm.doc.date_issued; 										//frappe.datetime.get_today();
		var tawad_until_date = frappe.datetime.add_days(temp_maturity_date.previous_maturity_date, 2)

		for (let index = 0; index < holidays_list.length; index++) {				// Check if maturity date is a holiday
			if (holidays_list[index].holiday_date == temp_maturity_date.previous_maturity_date) {
				holidays_before_maturity_date = holidays_list[index].holiday_date
				break
			} else if (holidays_list[index].holiday_date == frappe.datetime.add_days(temp_maturity_date.previous_maturity_date, 1)) {
				holidays_before_maturity_date = holidays_list[index].holiday_date
				break
			} else if (holidays_list[index].holiday_date == frappe.datetime.add_days(temp_maturity_date.previous_maturity_date, 2)) {
				holidays_before_maturity_date = holidays_list[index].holiday_date
				break
			} else if (holidays_list[index].holiday_date == frappe.datetime.add_days(temp_maturity_date.previous_maturity_date, 3)) {
				holidays_before_maturity_date = holidays_list[index].holiday_date
				break
			}
		}

		console.log("Previous Maturity Date: " + temp_maturity_date.previous_maturity_date);

		if (temp_maturity_date.previous_maturity_date == holidays_before_maturity_date) {
			tawad_until_date = frappe.datetime.add_days(tawad_until_date, 1)
		} else if (frappe.datetime.add_days(temp_maturity_date.previous_maturity_date, 1) == holidays_before_maturity_date) {
			tawad_until_date = frappe.datetime.add_days(tawad_until_date, 1)
		} else if (frappe.datetime.add_days(temp_maturity_date.previous_maturity_date, 2) == holidays_before_maturity_date) {
			tawad_until_date = frappe.datetime.add_days(tawad_until_date, 1)
		}

		if (date_today > frm.doc.maturity_date) {
			console.log("Maturity date: " + temp_maturity_date.previous_maturity_date);
			console.log("SC1");
			if (temp_maturity_date.previous_maturity_date <= date_today && tawad_until_date >= date_today) {
				console.log("SC1-1");
				if (multiplier == 1 && frm.doc.date_issued > frm.doc.maturity_date && date_today > tawad_until_date) {
					console.log("SC1-1A");
					temp_interest = temp_interest * (multiplier);
				} else {
					console.log("SC1-1B");
					temp_interest = temp_interest * (multiplier - 1); 
				}
			} else {
				console.log("SC1-2");
				console.log(multiplier);
				temp_interest = temp_interest * multiplier
			}
		} else {
			console.log("SC2");
			temp_interest = 0.00;
		}
		console.log("Multiplier after: " + String(multiplier));
		console.log("Interest: " + temp_interest);
		frm.set_value('interest_payment', temp_interest);
		frm.refresh_field('interest_payment');
		calculate_total_amount(frm);
	});
}

function calculate_date_difference(current_date, due_date) {
	var date_today = current_date.split("-");
	var date_today_year = parseInt(date_today[0]);
	var date_today_month = parseInt(date_today[1]);
	var date_today_day = parseInt(date_today[2]);
	var maturity_date = due_date.split("-");
	var maturity_date_year = parseInt(maturity_date[0]);
	var maturity_date_month = parseInt(maturity_date[1]);
	var maturity_date_day = parseInt(maturity_date[2]);
	var year_difference = 0;
	var month_difference = 0;
	var day_difference = 0;
	var leap_year = false
	var months = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Dec"}
	var days_in_month = {"Jan": 31, "Feb": 28, "Mar": 31, "Apr": 30, "May": 31, "Jun": 30, "Jul": 31, "Aug": 31, "Sept": 30, "Oct": 31, "Nov": 30, "Dec": 31}
	
	if (date_today_year % 4 == 0) {
		leap_year = true
		days_in_month["Feb"] = 29
	}

	if (date_today_year > maturity_date_year) {
		year_difference = date_today_year - maturity_date_year -1
	} else {
		year_difference = 0
	}

	if (date_today_month >= maturity_date_month) {
		month_difference = (date_today_month - maturity_date_month)
		if (year_difference != 0) {
			month_difference += (12 * year_difference)
		}
	} else {
		month_difference = date_today_month + (12 - maturity_date_month)
		if (year_difference != 0) {
			month_difference += (12 * year_difference)
		}
	}

	if (date_today_day >= maturity_date_day) {
		day_difference =  date_today_day - maturity_date_day;
		
	} else {
		day_difference = date_today_day + (days_in_month[months[maturity_date_month]] - maturity_date_day);
		month_difference -= 1;
	}

	console.log("Month difference: " + month_difference);

	return {
		"days": day_difference,
		"months": month_difference
	}
}

function calculate_maturity_date_month_difference(frm) {
	var current_date = frm.doc.date_issued.split("-");				//frappe.datetime.get_today().split("-");
	var maturity_date = frm.doc.maturity_date.split("-");
	var month_difference = 0;
	
	if (parseInt(current_date[0]) > parseInt(maturity_date[0])) { //Calculate month difference if maturity date is for next year
		month_difference = Math.abs(parseInt(current_date[1]) - (12 - parseInt(maturity_date[1])));
	} else if(parseInt(current_date[0]) == parseInt(maturity_date[0])){ // Calculate month difference if maturity date is the same year
		month_difference = parseInt(current_date[1]) - parseInt(maturity_date[1]);
		if (month_difference < 0) {
			month_difference = 0;
		}
	}

	return month_difference; 
}

function maturity_date_of_the_month(frm) {
	var current_date = frm.doc.date_issued.split("-");//frappe.datetime.get_today().split("-");
	var maturity_date = frm.doc.maturity_date.split("-");
	var month_difference = 0;
	var current_maturity_date = frm.doc.maturity_date;
	var previous_maturity_date = frm.doc.maturity_date;
	
	if (parseInt(current_date[0]) > parseInt(maturity_date[0])) { //Calculate month difference if maturity date is for next year
		month_difference = Math.abs(parseInt(current_date[1]) + (12 - parseInt(maturity_date[1])));
	} else if(parseInt(current_date[0]) == parseInt(maturity_date[0])){ // Calculate month difference if maturity date is the same year
		month_difference = parseInt(current_date[1]) - parseInt(maturity_date[1]);
		if (month_difference < 0) {
			month_difference = 0;
		}
	}
	
	current_maturity_date = frappe.datetime.add_months(current_maturity_date, month_difference);
	var current_maturity_date_day = current_maturity_date.split("-");
	console.log(month_difference);

	if (current_date[0] > maturity_date[0]){
		console.log("MD1");
		if (current_date[2] > maturity_date[2]) {
			previous_maturity_date = current_maturity_date;
			current_maturity_date = frappe.datetime.add_months(previous_maturity_date, 1);
		} else {
			previous_maturity_date = frappe.datetime.add_months(current_maturity_date, -1);
		}
	} else if (current_date[0] == maturity_date[0]) {
		console.log("MD2");
		if (current_date[1] > maturity_date[1]) {
			console.log("MD2-1");
			if (current_date[2] >= current_maturity_date_day[2]) {
				console.log("MD2-1-1");
				previous_maturity_date = current_maturity_date
				current_maturity_date = frappe.datetime.add_months(frm.doc.maturity_date, month_difference + 1);
			} else {
				console.log("MD2-1-2");
				current_maturity_date = frappe.datetime.add_months(frm.doc.maturity_date, month_difference);
				previous_maturity_date = frappe.datetime.add_months(current_maturity_date, -1);
			}
		} else if(current_date[1] == maturity_date[1]){
			console.log("MD2-2");
			if (current_date[2] > current_maturity_date_day[2]) {
				console.log("MD2-2-1");
				current_maturity_date = frappe.datetime.add_months(frm.doc.maturity_date, month_difference + 1);
				previous_maturity_date = frappe.datetime.add_months(current_maturity_date, -1);
			} 
		} 
	}

	if (previous_maturity_date < frm.doc.maturity_date) {
		previous_maturity_date = frm.doc.maturity_date
	}

	return {
		'previous_maturity_date': previous_maturity_date,
		'current_maturity_date': current_maturity_date
	}
}

function expiry_interest_multiplier(frm) {
	var temp_expiry_date = expiry_date(frm).previous_expiry_date.split("-");
	var original_expiry_date = frm.doc.expiry_date;
	var actual_current_date = frm.doc.date_issued; //frappe.datetime.get_today();
	var split_current_date = frm.doc.date_issued.split("-"); //frappe.datetime.get_today().split("-")
	var split_original_expiry_date = frm.doc.expiry_date.split("-")
	var multiplier = 0;

	if (parseInt(temp_expiry_date[0]) > parseInt(split_original_expiry_date[0])) {
		console.log("A1");
		multiplier = parseInt(temp_expiry_date[1]) + (12 - parseInt(split_original_expiry_date[1])) + 1;
	} else if (parseInt(temp_expiry_date[0]) == parseInt(split_original_expiry_date[0])) {
		console.log("B1");
		if (parseInt(temp_expiry_date[1]) == parseInt(split_original_expiry_date[1])) {
			console.log("B1-1");
			if (actual_current_date > original_expiry_date) {
				console.log("B1-2");
				multiplier = 1;
			} 
		}else if (parseInt(temp_expiry_date[1]) > parseInt(split_original_expiry_date[1])) {
			console.log("B2");
			if (actual_current_date > original_expiry_date) {
				console.log("B2-1");
				multiplier = Math.abs(parseInt(temp_expiry_date[1]) - parseInt(split_original_expiry_date[1])) + 1;
			} else {
				console.log("B2-2");
				multiplier = Math.abs(parseInt(temp_expiry_date[1]) - parseInt(split_original_expiry_date[1]));
			}
		}
	}
	
	return multiplier
}

function expiry_date(frm) {			// To determin if the current date is really to be taken as the expiry date or the previous expiry date
	var actual_current_date = frm.doc.date_issued;
	var actual_previous_expiry_date = frm.doc.expiry_date;
	var actual_current_expiry_date = frm.doc.expiry_date;
	var previous_expiry_date = actual_previous_expiry_date.split("-");
	var current_expiry_date = actual_current_expiry_date.split("-");
	var current_date = actual_current_date.split("-");
	var month_difference = 0;
	

	if (actual_current_date > actual_previous_expiry_date) {
		if (parseInt(current_date[0]) > parseInt(previous_expiry_date[0])) {
			month_difference = parseInt(current_date[1]) + (12 - parseInt(previous_expiry_date[1]))
		} else if (parseInt(current_date[0]) == parseInt(previous_expiry_date[0])) {
			month_difference = parseInt(current_date[1]) - parseInt(previous_expiry_date[1]);
			if (month_difference < 0) {
				month_difference = 0;
			}
		}
	}

	if (current_date[0] > previous_expiry_date[0]){
		if (current_date[2] < previous_expiry_date[2]) {
			actual_current_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, month_difference);
			actual_previous_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, -1);
		} else {
			actual_current_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, month_difference + 1);
			actual_previous_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, -1);
		}

	} else if (current_date[0] == previous_expiry_date[0]) {
		if (current_date[1] > previous_expiry_date[1]) {
			if (current_date[2] > previous_expiry_date[2]) {
				actual_current_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, month_difference + 1);
				actual_previous_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, -1);
			} else {
				actual_current_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, month_difference);
				actual_previous_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, -1);
			}
		} else if(current_date[1] == previous_expiry_date[1]){
			if (current_date[2] > previous_expiry_date[2]) {
				actual_current_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, month_difference + 1);
				actual_previous_expiry_date = frappe.datetime.add_months(actual_current_expiry_date, -1);
			}
		}
	}
	console.log (actual_previous_expiry_date + " " + actual_current_expiry_date);
	return {
		'previous_expiry_date': actual_previous_expiry_date,
		'current_expiry_date': actual_current_expiry_date
	}
}

function calculate_expiry_date_interest(frm) {
	frappe.db.get_doc('Holiday List', 'No Operations').then(function(r){
		var holidays_list = r.holidays;
		var holidays_before_expiry_date = null;
		var initial_interest = parseFloat(frm.doc.interest);
		if (Math.abs(frappe.datetime.get_day_diff(frm.doc.date_loan_granted, frm.doc.expiry_date)) == 90) {
			initial_interest *= 2
		} else if (Math.abs(frappe.datetime.get_day_diff(frm.doc.date_loan_granted, frm.doc.expiry_date)) == 120) {
			initial_interest *= 3
		}
		var temp_expiry_date = expiry_date(frm)
		var multiplier = expiry_interest_multiplier(frm);
		var temp_interest = frm.doc.interest
		var date_today = frm.doc.date_issued; //frappe.datetime.get_today();

		for (let index = 0; index < holidays_list.length; index++) {
			
			if (holidays_list[index].holiday_date == temp_expiry_date.previous_expiry_date) {
				holidays_before_expiry_date = holidays_list[index].holiday_date
				break
			} else if (holidays_list[index].holiday_date == frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 1)) {
				holidays_before_expiry_date = holidays_list[index].holiday_date
				break
			} else if (holidays_list[index].holiday_date == frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 2)) {
				holidays_before_expiry_date = holidays_list[index].holiday_date
				break
			} else if (holidays_list[index].holiday_date == frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 3)) {
				holidays_before_expiry_date = holidays_list[index].holiday_date
				break
			}
		}

		if (date_today > frm.doc.expiry_date) {
			if (temp_expiry_date.previous_expiry_date == holidays_before_expiry_date) {
				console.log("A1");
				if (date_today > frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 3)) {
					temp_interest = initial_interest + (temp_interest * multiplier);
				} else {
					multiplier = multiplier - 1;
					if (multiplier <= 0) {
						multiplier = 0;
					}
					temp_interest = initial_interest + (temp_interest * (multiplier));
				}
			} else if(frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 3) == holidays_before_expiry_date){
				console.log("B1");
				if (date_today > frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 3)) {
					temp_interest = initial_interest + (temp_interest * multiplier);
				} else {
					multiplier = multiplier - 1;
					if (multiplier <= 0) {
						multiplier = 0;
					}
					temp_interest = initial_interest + (temp_interest * (multiplier));
				}
			} else if (frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 2) == holidays_before_expiry_date) {
				console.log("C1");
				if (date_today > frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 3)) {
					console.log("C1-1");
					temp_interest = initial_interest + (temp_interest * multiplier);
					console.log(multiplier);
				} else {
					console.log("C1-2");
					multiplier = multiplier - 1;
					if (multiplier <= 0) {
						multiplier = 0;
					}
					temp_interest = initial_interest + (temp_interest * (multiplier));
					console.log(multiplier);
				}
			} else if (frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 1) == holidays_before_expiry_date) {
				console.log("D1");
				if (date_today > frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 3)) {
					console.log("D1-1");
					temp_interest = initial_interest + (temp_interest * multiplier);
				} else {
					multiplier = multiplier - 1;
					console.log("D1-2");
					if (multiplier <= 0) {
						multiplier = 0;
					}
					temp_interest = initial_interest + (temp_interest * (multiplier));
				}
			} else {
				console.log("E1");
				if (date_today > frappe.datetime.add_days(temp_expiry_date.previous_expiry_date, 2)) {
					console.log("E1-1");
					temp_interest = initial_interest + (temp_interest * (multiplier));
				} else {
					multiplier = multiplier - 1;
					console.log("E1-2");
					if (multiplier <= 0) {
						multiplier = 0;
					}
					temp_interest = initial_interest + (temp_interest * multiplier);
				}
				console.log("The multiplier is " + multiplier);
				console.log("The interest is " + temp_interest);
			}
		} else {
			temp_interest = initial_interest;
		}
		console.log("Interest: " + temp_interest);
		frm.set_value('interest_payment', temp_interest)
		frm.refresh_field('interest_payment')
		calculate_total_amount(frm);
	});
}

function show_items(doctype, doc_name, doc_table_name = null) {
	frappe.db.get_doc(doctype, doc_name).then(function(r){
		if (doctype == "Pawn Ticket Non Jewelry") {
			var item_list = r.non_jewelry_items
			for (let index = 0; index < item_list.length; index++) {
				let childTable = cur_frm.add_child("items");
				childTable.item_code = item_list[index].item_no;
				childTable.description = item_list[index].model + ", " + item_list[index].model_number
			}
			cur_frm.refresh_field('items')
		} else if (doctype == "Pawn Ticket Jewelry") {
			var item_list = r.jewelry_items
			for (let index = 0; index < item_list.length; index++) {
				let childTable = cur_frm.add_child("items");
				childTable.item_code = item_list[index].item_no;
				childTable.description = item_list[index].type + ", " + item_list[index].karat + ", " + item_list[index].karat_category + ", " + item_list[index].color;
			}
			cur_frm.refresh_field('items')
		}
		
	})
}

function select_naming_series(frm) { //Select naming series with regards to the branch

	if (frm.doc.branch == "Garcia's Pawnshop - CC") {
		branch_code_no = 1;
		frm.set_value('naming_series', "No-1-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - GTC") {
		branch_code_no = 4;
		frm.set_value('naming_series', "No-4-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - MOL") {
		branch_code_no = 6;
		frm.set_value('naming_series', "No-6-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - POB") {
		branch_code_no = 3;
		frm.set_value('naming_series', "No-3-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - TNZ") {
		branch_code_no = 5;
		frm.set_value('naming_series', "No-5-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - ALP") {
		branch_code_no = 7;
		frm.set_value('naming_series', "No-7-.######")
	}

}

function get_new_pawn_ticket_no(frm) {

	if (frm.doc.pawn_ticket_type == "Pawn Ticket Jewelry") {
		frappe.db.get_value("Pawn Ticket Jewelry", frm.doc.pawn_ticket_no, "item_series")
		.then(data => {
			if (data.message.item_series == "A") {
				frappe.db.get_value("Pawnshop Naming Series", frm.doc.branch , "a_series")
				.then(r => {
					let current_count = r.message.a_series;
					frm.set_value('new_pawn_ticket_no', branch_code_no + "-" + current_count)
					frm.refresh_field('new_pawn_ticket_no')

				})
			} else if (data.message.item_series == "B") {
				frappe.db.get_value("Pawnshop Naming Series", frm.doc.branch, "b_series")
				.then(r => {
					let current_count = r.message.b_series;
					frm.set_value('new_pawn_ticket_no', branch_code_no + "-" + current_count + "B")
					frm.refresh_field('new_pawn_ticket_no')

				})
			}
		})
	} else if (frm.doc.pawn_ticket_type == "Pawn Ticket Non Jewelry") {
		frappe.db.get_value("Pawnshop Naming Series", frm.doc.branch, "b_series")
		.then(r => {
			let current_count = r.message.b_series;
			frm.set_value('new_pawn_ticket_no', branch_code_no + "-" + current_count + "B")
			frm.refresh_field('new_pawn_ticket_no')

		})
	}

}



function calculate_new_interest(frm) {
	frm.set_value('advance_interest', 0.00);
	frm.refresh_field('advance_interest');
	if (frm.doc.pawn_ticket_type == "Pawn Ticket Non Jewelry") {
		frappe.db.get_single_value('Pawnshop Management Settings', 'gadget_interest_rate')
		.then(rate => {
			let new_interest = (parseFloat(frm.doc.principal_amount) - parseFloat(frm.doc.additional_amortization)) * (rate/100);
			frm.set_value('advance_interest', new_interest);
			frm.refresh_field('advance_interest');
		})
	} else {
		frappe.db.get_single_value('Pawnshop Management Settings', 'jewelry_interest_rate')
		.then(rate => {
			let new_interest = (parseFloat(frm.doc.principal_amount) - parseFloat(frm.doc.additional_amortization)) * (rate/100);
			frm.set_value('advance_interest', new_interest);
			frm.refresh_field('advance_interest');
		})
	}
}
