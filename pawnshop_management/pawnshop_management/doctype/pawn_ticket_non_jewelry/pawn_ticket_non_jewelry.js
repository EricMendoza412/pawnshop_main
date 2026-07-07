// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pawn Ticket Non Jewelry', {

	onload: function(frm) {
		//console.log(record.message);
		// if((frm.doc.expiry_date == frm.doc.expiry_date) && (frm.doc.date_loan_granted == frappe.datetime.get_today())){		
			
		// 		frappe.msgprint({
		// 		title:__('Please tell Customer'),
		// 		message: __('30 days nalang po tayo sa Sanglang gadgets. Expired na po ang sangla sa '+frm.doc.expiry_date+ ', mareremata po ito pag hindi natubuan o natubos bago ang expiry date.')
		// 		})
		// 	}
			
    },
	
	after_workflow_action: function(frm){
		frm.reload_doc()
	},

	validate: function(frm, cdt, cdn){
		const pawn_ticket_name = frm.doc.pawn_ticket || frm.doc.name;
		const run_validation = () => {
			var temp_principal = 0.0;
			$.each(frm.doc.non_jewelry_items, function(index, item){
				temp_principal += parseFloat(item.suggested_appraisal_value);
			});

			if (frm.doc.desired_principal > temp_principal) {
				frappe.throw(__('Desired Principal is greater than the total value of items'));
			}

			if (frm.doc.desired_principal <= 0){
				frappe.throw(__('Desired Principal cannot be zero'));
			}
		};

		if (!pawn_ticket_name) {
			run_validation();
			return;
		}

		return frappe.db.exists('Pawn Ticket Jewelry', pawn_ticket_name).then(exists => {
			if (exists) {
				frappe.msgprint({
					title: __('Error'),
					indicator: 'red',
					message: __('Pawn Ticket with the same name exists in Pawn Ticket Jewelry. Please refresh the document and try again.')
				});
				frappe.validated = false;
				return;
			}

			run_validation();
		});
	},
	after_save: function(frm){
		frm.set_df_property('customers_tracking_no', 'read_only', 1);
	},

	refresh: function(frm){
		const is_administrator = frappe.session.user === 'Administrator';
		const can_send_smart_sms = ['Active', 'Expired'].includes(frm.doc.workflow_state);
		const today = frappe.datetime.get_today();
		const is_today_or_within_previous_5_days = function(date) {
			if (!date) {
				return false;
			}

			const days_from_today = frappe.datetime.get_day_diff(today, date);
			return days_from_today >= 0 && days_from_today <= 5;
		};

		const add_expiry_sms_button = function() {
			if (!can_send_smart_sms || !is_today_or_within_previous_5_days(frm.doc.expiry_date) || frm.doc.texted_upon_expiry) {
				return;
			}

			frm.add_custom_button(__('Expiry Date SMS'), function() {
				frappe.call({
					method: 'pawnshop_management.pawnshop_management.smart_a2p.send_expiry_date_sms',
					args: {
						reference_doctype: frm.doc.doctype,
						reference_name: frm.doc.name
					},
					freeze: true,
					freeze_message: __('Sending SMART SMS...'),
					callback: function(r) {
						if (!r.exc) {
							frappe.msgprint({
								title: __('SMART SMS Sent'),
								indicator: 'green',
								message: __('Sent SMART SMS to {0}. SMART SMS Log: {1}', [r.message.destination, r.message.log])
							});
						}
					}
				});
			});
		};

		if (is_administrator) {
			add_expiry_sms_button();
		} else if (frm.doc.branch) {
			frappe.call({
				method: "pawnshop_management.operations_access_control.access_control.get_active_branch_roles",
				args: { branch: frm.doc.branch },
				callback(response) {
					if ((response.message || {})["Vault Custodian"]) {
						add_expiry_sms_button();
					}
				},
			});
		}

		//make customers_tracking_no and jewelry_items read only after saving
		if(!frm.is_new() && frm.doc.docstatus == 0){
			frm.set_df_property('customers_tracking_no', 'read_only', 1);
			frm.set_df_property('non_jewelry_items', 'read_only', 1);
			frm.set_df_property('desired_principal', 'read_only', 1);
		}

		let dlg_workf_good = false
		if((frm.doc.date_loan_granted == frappe.datetime.get_today()) && (frm.doc.workflow_state == 'Active')){
			dlg_workf_good = true
		} 
		let role_good = false
		if(frappe.user_roles.includes('Operations Manager') || frappe.user_roles.includes('Administrator') || frappe.user_roles.includes('Support Team') || frappe.user_roles.includes('Supervisor')){
			role_good = true
		}


		if(dlg_workf_good && role_good){
			// frm.add_custom_button('Printing Error', function(){

			// 	frappe.msgprint({
			// 		title: __('Notification'),
			// 		message: __('Tranfer this PT to the next available PT?'),
			// 		primary_action:{
			// 			'label': 'Yes',
			// 			async action(values) {
						
			// 				let series;
			// 				if (frm.doc.item_series == "A") {
			// 					series = "a_series";
			// 				} else if (frm.doc.item_series == "B") {
			// 					series = "b_series";
			// 				}

			// 				if(series){
			// 					frappe.db.get_value("Pawnshop Naming Series", frm.doc.branch, series)
			// 					.then(r => {
			// 						let current_count
			// 						let pta = r.message.a_series;
			// 						let ptb = r.message.b_series;

			// 						let branchCode
			// 						frappe.db.get_value("Branch IP Addressing", frm.doc.branch, "branch_code")
			// 						.then(r => {
			// 							branchCode = r.message.branch_code;
									
			// 							if(pta){
			// 								current_count = branchCode + "-" + pta}
			// 							else{
			// 								current_count = branchCode + "-" + ptb + "B"}

			// 							frappe.call({
			// 								method: 'pawnshop_management.pawnshop_management.custom_codes.paper_jammed.transfer_to_next_pt_nj',
			// 								args: {
			// 									pawn_ticket: String(frm.doc.name),
			// 									nxt_pt: String(current_count)
			// 								},
			// 								callback: (r) =>{
			// 									frappe.msgprint({
			// 										title:__('Notification'),
			// 										indicator:'green',
			// 										message: __('Successfully transferred to Pawn Ticket# ' + current_count)
			// 									});
			// 								}
			// 							})
			// 						})
			// 					})
			// 				}

			// 			}
			// 		}
			// 	});
				
			// });
			frm.add_custom_button('Printing Error NJ', async function () {
				frappe.msgprint({
					title: __('Notification'),
					message: __('Transfer this PT to the next available PT?'),
					primary_action: {
						'label': 'Yes',
						async action() {

							let series;
							if (frm.doc.item_series === "A") series = "a_series";
							else if (frm.doc.item_series === "B") series = "b_series";

							if (!series) {
								frappe.msgprint(__('Missing item series (A/B).'));
								return;
							}

							try {
								cur_dialog.hide();  // Close the message box
								// Prevent spam-clicks while we work
								frappe.dom.freeze(__('Transferring...'));

								const ns = await frappe.db.get_value("Pawnshop Naming Series", frm.doc.branch, [series]);
								const pta = ns?.message?.a_series;
								const ptb = ns?.message?.b_series;

								const bres = await frappe.db.get_value("Branch IP Addressing", frm.doc.branch, ["branch_code"]);
								const branchCode = bres?.message?.branch_code;

								let current_count;
								if (pta) current_count = `${branchCode}-${pta}`;
								else current_count = `${branchCode}-${ptb}B`;

								const r = await frappe.call({
									method: 'pawnshop_management.pawnshop_management.custom_codes.paper_jammed.transfer_to_next_pt_nj',
									args: {
										pawn_ticket: String(frm.doc.name),
										nxt_pt: String(current_count)
									},
									freeze: true,
									freeze_message: __('Transferring...')
								});

								if (!r.exc) {
									frappe.show_alert({ message: __('Transferred to Pawn Ticket # {0}', [current_count]), indicator: 'green' });

									// CRITICAL: pull fresh state from server so workflow_state/docstatus update is reflected
									//await frm.reload_doc();

									// Optional: also route to the new PT
									//frappe.set_route('Form', 'Pawn Ticket Non Jewelry', r.message.new_pt_docname);
									// Then reload and clear cache
									location.reload();
								}

							} catch (e) {
								console.error(e);
								frappe.msgprint({ title: __('Error'), indicator: 'red', message: e.message || __('Transfer failed') });
							} finally {
								frappe.dom.unfreeze();

							}
						}
					}
				});
			});

		}

		let is_allowed = frappe.user_roles.includes('Administrator');
		frm.toggle_enable(['date_loan_granted', 'branch'], is_allowed)
		frm.fields_dict["non_jewelry_items"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "hidden";

		if (frm.is_new()) {

			frm.set_value('date_loan_granted', frappe.datetime.nowdate())

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

						frappe.db.get_value('Pawnshop Naming Series', records[0].name, 'inventory_count')
						.then(r =>{
							let nj_inventory_count = r.message.inventory_count
							frm.set_query('item_no', 'non_jewelry_items', function(){
								return {
									filters: {
										batch_number: String(nj_inventory_count),
										branch: records[0].name
									}
								}
							})
						})
					})
				}
			})
		}

		if(frm.doc.interest_rate == "0"){
			frm.set_df_property('interest_rate', 'hidden', 1);
		}
		frm.fields_dict["non_jewelry_items"].grid.grid_buttons.find(".grid-add-row")[0].innerHTML = "Add Item"	//Change "Add Row" button of jewelry_items table into "Add Item"

		//if workflow_state is "In Transit" or "For Sale" disable Actions. The Transfer Tracker doctype controls the workflow state
		if (frm.doc.workflow_state == "Expired" && !frappe.user_roles.includes('Administrator')) {

			 // hide/clear the Actions dropdown
			if (frm.page.clear_actions_menu) {
				frm.page.clear_actions_menu();           // Frappe API: clears Actions items
			}

			// some versions still render the empty button—hide it via DOM as fallback
			const $actions = $(frm.page.wrapper).find('.actions-btn-group');
			if ($actions.length) $actions.hide();
		}else {
			// optional: show back if state changes
			$(frm.page.wrapper).find('.actions-btn-group').show();
			}

		load_customer_id_pictures(frm);

	},

	branch: function(frm){
		if (frm.is_new()){
			show_tracking_no(frm);
		}	
		if (frm.is_new() && frm.doc.amended_from == null) {
			frm.set_value('date_loan_granted', frappe.datetime.nowdate())
		}
	},

	date_loan_granted: function(frm){
		let default_maturity_date = frappe.datetime.add_days(frm.doc.date_loan_granted, 30);
		frm.set_value('maturity_date', default_maturity_date);

		let defaul_expiry_date = frappe.datetime.add_days(frm.doc.date_loan_granted, 30);
		frm.set_value('expiry_date', defaul_expiry_date);
	},

	desired_principal: function(frm, cdt, cdn) {
		if (frm.is_new()){
			show_tracking_no(frm);
		}	
		frm.refresh_fields('pawn_ticket');
		set_item_interest(frm)
		frm.set_value('original_principal', frm.doc.desired_principal);
	},

	inventory_tracking_no: function(frm, cdt, cdn){
		set_total_appraised_amount(frm, cdt, cdn);
	},

	customers_tracking_no: async function(frm){
		if (frm.is_new()){
			show_tracking_no(frm);
		}
		load_customer_id_pictures(frm);

		// if form is not amended
		if (frm.doc.amended_from == null) {
			try {
				const customer = frm.doc.customers_tracking_no;
				if (!customer) {
					frm.set_value('last_j_sangla_date_in_gp', null);
					frm.set_value('last_j_sangla_date_in_branch', null);
					frm.set_value('last_nj_sangla_date_in_gp', null);
					frm.set_value('last_nj_sangla_date_in_branch', null);
					return;
				}

				const r = await frappe.db.get_value('Customer', customer, 'disabled');
				if (r?.message?.disabled) {
					const message = 'This customer record is disabled';
					frappe.msgprint(message);
					setTimeout(function(){
						frm.set_value('customers_full_name', "");
						frm.set_value('customer_birthday', "");
						frm.set_value('customers_tracking_no', "");
					},2000);
					return;
				}

				const getLastLoanDate = (doctype, filters) =>
					frappe.db.get_list(doctype, {
						fields: ['date_loan_granted'],
						filters,
						order_by: 'date_loan_granted desc',
						limit: 1
					}).then(res => (res?.length ? res[0].date_loan_granted : null));

				const baseFilters = {
					customers_tracking_no: customer,
					old_pawn_ticket: '',
					workflow_state: ['!=', 'Rejected']
				};

				const branchFilters = frm.doc.branch
					? { ...baseFilters, branch: frm.doc.branch }
					: null;

				const [[lastJGeneral, lastJBranch], [lastNJGeneral, lastNJBranch]] = await Promise.all([
					Promise.all([
						getLastLoanDate('Pawn Ticket Jewelry', baseFilters),
						branchFilters ? getLastLoanDate('Pawn Ticket Jewelry', branchFilters) : Promise.resolve(null)
					]),
					Promise.all([
						getLastLoanDate('Pawn Ticket Non Jewelry', baseFilters),
						branchFilters ? getLastLoanDate('Pawn Ticket Non Jewelry', branchFilters) : Promise.resolve(null)
					])
				]);

				frm.set_value('last_j_sangla_date_in_gp', lastJGeneral);
				frm.set_value('last_j_sangla_date_in_branch', branchFilters ? lastJBranch : null);
				frm.set_value('last_nj_sangla_date_in_gp', lastNJGeneral);
				frm.set_value('last_nj_sangla_date_in_branch', branchFilters ? lastNJBranch : null);
			} catch (error) {
				console.error('Unable to fetch latest pawn ticket dates', error);
			}
		}

	},

	amended_from: function(frm){
		if (frm.is_new()){
			set_amended_pawn_ticket(frm);
		}
	},

	customer_id_picture: function(frm) {
		show_selected_customer_id_picture(frm);
	}

});

frappe.ui.form.on('Non Jewelry List', {
	item_no: function(frm, cdt, cdn){
		let table_length = parseInt(frm.doc.non_jewelry_items.length)
		if (frm.doc.non_jewelry_items.length > 1) {
			for (let index = 0; index < table_length - 1; index++) {
				// if (frm.doc.non_jewelry_items[table_length-1].item_no == frm.doc.non_jewelry_items[index].item_no) {
				// 	frm.doc.non_jewelry_items.pop(table_length-1);
				// 	//frm.refresh_field('non_jewelry_items');
				// 	// frappe.msgprint({
				// 	// 	title:__('Notification'),
				// 	// 	indicator:'red',
				// 	// 	message: __('Added item is already in the list. Item removed.')
				// 	// });
				// 	set_total_appraised_amount(frm, cdt, cdn);
				// }
			}
		}	
	},

	suggested_appraisal_value: function(frm, cdt, cdn){
		set_total_appraised_amount(frm,cdt, cdn);
	},

	non_jewelry_items_remove: function(frm, cdt, cdn){
		set_total_appraised_amount(frm, cdt, cdn);
		frm.fields_dict["non_jewelry_items"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "visible";
	},

	non_jewelry_items_add: function(frm, cdt, cdn){
		frm.fields_dict["non_jewelry_items"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "hidden";
	}
});


function show_tracking_no(frm){ //Sets inventory tracking number
	if (frm.doc.amended_from == null) {
		let branch_code = 0;

		frappe.db.get_list('Branch IP Addressing', {
			fields: ['branch_code'],
			filters: {
				name: frm.doc.branch
			}
		}).then(records => {
			branch_code = records[0].branch_code;
			frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['b_series', 'inventory_count'])
			.then(value => {
				let tracking_no = value.message;
				let non_jewelry_count = parseInt(tracking_no.inventory_count);
				let new_ticket_no = parseInt(tracking_no.b_series);
				frm.set_value('pawn_ticket', branch_code + "-" + new_ticket_no + frm.doc.item_series);
				frm.set_value('inventory_tracking_no', branch_code + "-" + non_jewelry_count + 'NJ');
				frm.refresh_field('pawn_ticket');
			})
		})
	} else {
		set_amended_pawn_ticket(frm);
	}


	// if (frm.doc.branch == "Garcia's Pawnshop - CC") {
	// 	if (frm.doc.amended_from == null) {
	// 		frappe.db.get_value('Pawnshop Naming Series', "Garcia's Pawnshop - CC",['b_series', 'inventory_count'])
	// 		.then(value => {
	// 			let tracking_no = value.message;
	// 			let non_jewelry_count = parseInt(tracking_no.inventory_count);
	// 			let new_ticket_no = parseInt(tracking_no.b_series);
	// 			frm.set_value('pawn_ticket', "1-"+ new_ticket_no + frm.doc.item_series);
	// 			frm.set_value('inventory_tracking_no', "1-"+ non_jewelry_count + 'NJ');
	// 			frm.refresh_field('pawn_ticket');
	// 		})
	// 	} else {
	// 		var previous_pt = frm.doc.amended_from      //Naming for the next document created of amend
	// 		if (count_dash_characters(previous_pt) < 2) {
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-1");
	// 			frm.refresh_field('pawn_ticket');
	// 		} else {
	// 			var index_of_last_dash_caharacter = previous_pt.lastIndexOf("-")
	// 			var current_amend_count = index_of_last_dash_caharacter.slice(index_of_last_dash_caharacter, -1)
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-" + parseInt(current_amend_count) + 1);
	// 			frm.refresh_field('pawn_ticket');
	// 		}
	// 	}
	// } else if (frm.doc.branch == "Garcia's Pawnshop - GTC") {
	// 	if (frm.doc.amended_from == null){
	// 		frappe.db.get_value('Pawnshop Naming Series',"Garcia's Pawnshop - GTC",['b_series', 'inventory_count'])
	// 		.then(value => {
	// 			let tracking_no = value.message;
	// 			let non_jewelry_count = parseInt(tracking_no.inventory_count);
	// 			let new_ticket_no = parseInt(tracking_no.b_series);
	// 			frm.set_value('pawn_ticket', "4-"+ new_ticket_no + frm.doc.item_series);
	// 			frm.set_value('inventory_tracking_no', "4-" + non_jewelry_count + 'NJ');
	// 			frm.refresh_field('pawn_ticket');
	// 		})
	// 	} else {
	// 		var previous_pt = frm.doc.amended_from      //Naming for the next document created of amend
	// 		if (count_dash_characters(previous_pt) < 2) {
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-1");
	// 			frm.refresh_field('pawn_ticket');
	// 		} else {
	// 			var index_of_last_dash_caharacter = previous_pt.lastIndexOf("-")
	// 			var current_amend_count = index_of_last_dash_caharacter.slice(index_of_last_dash_caharacter, -1)
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-" + parseInt(current_amend_count) + 1);
	// 			frm.refresh_field('pawn_ticket');
	// 		}
	// 	}
		
	// } else if (frm.doc.branch == "Garcia's Pawnshop - MOL") {
	// 	if (frm.doc.amended_from == null) {
	// 		frappe.db.get_value('Pawnshop Naming Series', "Garcia's Pawnshop - MOL",['b_series', 'inventory_count'])
	// 		.then(value => {
	// 			let tracking_no = value.message;
	// 			let non_jewelry_count = parseInt(tracking_no.inventory_count);
	// 			let new_ticket_no = parseInt(tracking_no.b_series);
	// 			frm.set_value('pawn_ticket', "6-" +new_ticket_no + frm.doc.item_series);
	// 			frm.set_value('inventory_tracking_no', "6-" + non_jewelry_count + 'NJ');
	// 			frm.refresh_field('pawn_ticket');
	// 		})
	// 	} else {
	// 		var previous_pt = frm.doc.amended_from      //Naming for the next document created of amend
	// 		if (count_dash_characters(previous_pt) < 2) {
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-1");
	// 			frm.refresh_field('pawn_ticket');
	// 		} else {
	// 			var index_of_last_dash_caharacter = previous_pt.lastIndexOf("-")
	// 			var current_amend_count = index_of_last_dash_caharacter.slice(index_of_last_dash_caharacter, -1)
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-" + parseInt(current_amend_count) + 1);
	// 			frm.refresh_field('pawn_ticket');
	// 		}
	// 	}
		
	// } else if (frm.doc.branch == "Garcia's Pawnshop - POB") {
	// 	if (frm.doc.amended_from == null) {
	// 		frappe.db.get_value('Pawnshop Naming Series', "Garcia's Pawnshop - POB",['b_series', 'inventory_count'])
	// 		.then(value => {
	// 			let tracking_no = value.message;
	// 			let non_jewelry_count = parseInt(tracking_no.inventory_count);
	// 			let new_ticket_no = parseInt(tracking_no.b_series);
	// 			frm.set_value('pawn_ticket', "3-" + new_ticket_no + frm.doc.item_series);
	// 			frm.set_value('inventory_tracking_no', "3-"+ non_jewelry_count + 'NJ');
	// 			frm.refresh_field('pawn_ticket');
	// 		})
	// 	} else {
	// 		var previous_pt = frm.doc.amended_from      //Naming for the next document created of amend
	// 		if (count_dash_characters(previous_pt) < 2) {
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-1");
	// 			frm.refresh_field('pawn_ticket');
	// 		} else {
	// 			var index_of_last_dash_caharacter = previous_pt.lastIndexOf("-")
	// 			var current_amend_count = index_of_last_dash_caharacter.slice(index_of_last_dash_caharacter, -1)
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-" + parseInt(current_amend_count) + 1);
	// 			frm.refresh_field('pawn_ticket');
	// 		}
	// 	}
	// } else if (frm.doc.branch == "Garcia's Pawnshop - TNZ") {
	// 	if (frm.doc.amended_from == null) {
	// 		frappe.db.get_value('Pawnshop Naming Series', "Garcia's Pawnshop - TNZ",['b_series', 'inventory_count'])
	// 		.then(value => {
	// 			let tracking_no = value.message;
	// 			let non_jewelry_count = parseInt(tracking_no.inventory_count);
	// 			let new_ticket_no = parseInt(tracking_no.b_series);
	// 			frm.set_value('pawn_ticket', "5-"+ new_ticket_no + frm.doc.item_series);
	// 			frm.set_value('inventory_tracking_no', "5-" + non_jewelry_count + 'NJ');
	// 			frm.refresh_field('pawn_ticket');
	// 		})
	// 	} else {
	// 		var previous_pt = frm.doc.amended_from      //Naming for the next document created of amend
	// 		if (count_dash_characters(previous_pt) < 2) {
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-1");
	// 			frm.refresh_field('pawn_ticket');
	// 		} else {
	// 			var index_of_last_dash_caharacter = previous_pt.lastIndexOf("-")
	// 			var current_amend_count = index_of_last_dash_caharacter.slice(index_of_last_dash_caharacter, -1)
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-" + parseInt(current_amend_count) + 1);
	// 			frm.refresh_field('pawn_ticket');
	// 		}
	// 	}
	// } else if (frm.doc.branch == "Rabie's House") {
	// 	if (frm.doc.amended_from == null) {
	// 		console.log(frm.doc.amended_from);
	// 		frappe.db.get_value('Pawnshop Naming Series', "Rabie's House",['b_series', 'inventory_count'])
	// 		.then(value => {
	// 			let tracking_no = value.message;
	// 			let non_jewelry_count = parseInt(tracking_no.inventory_count);
	// 			let new_ticket_no = parseInt(tracking_no.b_series);
	// 			frm.set_value('pawn_ticket', "20-"+ new_ticket_no + frm.doc.item_series);
	// 			frm.set_value('inventory_tracking_no', "20-" + non_jewelry_count + 'NJ');
	// 			frm.refresh_field('pawn_ticket');
	// 		})
	// 	} else {
	// 		var previous_pt = String(frm.doc.amended_from);      //Naming for the next document created of amend
	// 		console.log(count_dash_characters(previous_pt));
	// 		if (count_dash_characters(previous_pt) < 2) {
	// 			console.log("Hi");
	// 			frm.set_value('pawn_ticket', frm.doc.amended_from + "-1");
	// 			frm.refresh_field('pawn_ticket');
	// 		} else {
	// 			console.log("Hello");
	// 			var index_of_last_dash_caharacter = parseInt(frm.doc.amended_from.lastIndexOf("-"))
	// 			var current_amend_count = frm.doc.amended_from.substr((index_of_last_dash_caharacter + 1))
	// 			var original_pt = frm.doc.amended_from.slice(0, parseInt(index_of_last_dash_caharacter))

	// 			frm.set_value('pawn_ticket', original_pt + "-" + (parseInt(current_amend_count) + 1));
	// 			frm.refresh_field('pawn_ticket');
	// 		}
	// 	}
	// } 
	
}

function set_total_appraised_amount(frm, cdt, cdn) { 			// Calculate Principal Amount
	let temp_principal = 0.00;
	$.each(frm.doc.non_jewelry_items, function(index, item){
		temp_principal += parseFloat(item.suggested_appraisal_value);
	});
	frm.set_value('desired_principal', temp_principal);
	set_item_interest(frm)
	return temp_principal
}

function set_item_interest(frm) {
	var principal = parseFloat(frm.doc.desired_principal);
	var interest = 0.00;
	var net_proceeds = 0.00;
	frappe.db.get_single_value('Pawnshop Management Settings', 'gadget_interest_rate').then(value => {
		interest = parseFloat(value)/100 * principal;
		frm.set_value('interest', interest);
		net_proceeds = principal - interest;
		frm.set_value('net_proceeds', net_proceeds);
		frm.set_value('interest_rate',value);
	});
}

function load_customer_id_pictures(frm) {
	if (!frm.doc.customers_tracking_no) {
		frm._customer_id_picture_options = [];
		frm.set_df_property('customer_id_picture', 'options', []);
		frm.doc.customer_id_picture = null;
		frm.refresh_field('customer_id_picture');
		frm._all_customer_ids_expired = false;
		$(frm.fields_dict['default_image'].wrapper).html('');
		return;
	}

	frappe.call({
		method: "pawnshop_management.pawnshop_management.utils.get_contact_id_pictures_by_customer",
		args: {
			customer: frm.doc.customers_tracking_no,
		},
		callback: function(r) {
			const data = r.message || {};
			const options = data.options || [];
			frm._customer_id_picture_options = options;
			frm._all_customer_ids_expired = Boolean(data.all_customer_ids_expired);

			frm.set_df_property(
				'customer_id_picture',
				'options',
				options.map(option => option.label).join('\n')
			);

			frm.toggle_display('customer_id_picture', options.length > 1);

			if (data.selected) {
				const selected_option = options.find(option => option.value === data.selected);
				frm.doc.customer_id_picture = selected_option ? selected_option.label : null;
				frm.refresh_field('customer_id_picture');
			}

			if (data.html) {
				const selected_option = options.find(option => option.label === frm.doc.customer_id_picture);
				render_customer_id_picture(frm, data.html, selected_option);
			}
		}
	});
}

function show_selected_customer_id_picture(frm) {
	const selected = frm.doc.customer_id_picture;
	const options = frm._customer_id_picture_options || [];
	const selected_option = options.find(option => option.label === selected);

	if (!selected_option) {
		return;
	}

	if (selected_option.id_pic_name) {
		const image_url = get_customer_id_picture_url(selected_option.id_pic_name);
		const fallback_image_url = get_customer_id_picture_fallback_url(selected_option.id_pic_name);
		render_customer_id_picture(
			frm,
			`<img src="${escape_html(image_url)}" data-fallback-src="${escape_html(fallback_image_url)}" onerror="handle_customer_id_picture_error(this)" style="max-width: 400px; height: auto;">`,
			selected_option
		);
		return;
	}

	render_customer_id_picture(
		frm,
		`<div class="alert alert-warning">${__('No ID picture set for selected ID')}</div>`,
		selected_option
	);
}

function render_customer_id_picture(frm, image_html, selected_option) {
	const indicator = get_customer_id_expiry_indicator(frm, selected_option);
	$(frm.fields_dict['default_image'].wrapper).html(`${image_html}${indicator}`);
	make_customer_id_picture_zoomable(frm);
}

function get_customer_id_expiry_indicator(frm, selected_option) {
	let message = null;

	if (frm._all_customer_ids_expired) {
		message = __('All customer IDs have expired');
	} else if (selected_option && selected_option.is_expired) {
		message = __('Selected customer ID has expired');
	}

	if (!message) {
		return '';
	}

	return `<div style="color: #b42318; font-weight: 700; font-size: 14px; margin-top: 8px;">${message}</div>`;
}

function make_customer_id_picture_zoomable(frm) {
	const $wrapper = $(frm.fields_dict['default_image'].wrapper);
	const $image = $wrapper.find('img');

	if (!$image.length) {
		return;
	}

	$image
		.css('cursor', 'zoom-in')
		.attr('title', __('Click to zoom'))
		.off('click.customer_id_zoom')
		.on('click.customer_id_zoom', function() {
			const image_url = $(this).attr('src');
			const dialog = new frappe.ui.Dialog({
				title: __('Customer ID Picture'),
				size: 'large'
			});

			dialog.$body.html(
				`<div style="text-align: center;">
					<img src="${escape_html(image_url)}" style="max-width: 100%; max-height: 75vh; height: auto;">
				</div>`
			);
			dialog.show();
		});
}

function escape_html(value) {
	return $('<div>').text(value || '').html();
}

function get_customer_id_picture_url(id_pic_name) {
	return `https://firebasestorage.googleapis.com/v0/b/gpcustomersids.appspot.com/o/customerPictures%2F${encodeURIComponent(id_pic_name)}.jpg?alt=media`;
}

function get_customer_id_picture_fallback_url(id_pic_name) {
	return `https://storage.cloud.google.com/gpcustomersids.appspot.com/customerPictures/${encodeURIComponent(id_pic_name)}.jpg`;
}

function handle_customer_id_picture_error(image) {
	if (image.dataset.fallbackSrc && image.src !== image.dataset.fallbackSrc) {
		image.src = image.dataset.fallbackSrc;
		image.removeAttribute('data-fallback-src');
	}
}

function null_checker(number) {
	if (number == null) {
		number = 0;
	}
	return parseInt(number)
}

function get_amended_pawn_ticket_name(amended_from) {
	if (!amended_from) {
		return "";
	}

	if ((amended_from.match(/-/g) || []).length < 2) {
		return amended_from + "-1";
	}

	const last_dash_index = amended_from.lastIndexOf("-");
	const base_pawn_ticket = amended_from.slice(0, last_dash_index);
	const amend_count = amended_from.slice(last_dash_index + 1);

	if (/^\d+$/.test(amend_count)) {
		return base_pawn_ticket + "-" + (parseInt(amend_count, 10) + 1);
	}

	return amended_from + "-1";
}

function set_amended_pawn_ticket(frm) {
	frm.set_value('pawn_ticket', get_amended_pawn_ticket_name(frm.doc.amended_from));
	frm.refresh_field('pawn_ticket');
}
