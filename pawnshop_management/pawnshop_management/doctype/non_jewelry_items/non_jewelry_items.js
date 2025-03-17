// Copyright (c) 2021, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Non Jewelry Items', {
	onload: function(frm) {
		frm.message_shown = false; // Initialize message_shown
		if (frm.is_new()) {
			//frm.set_value('main_appraiser', frappe.user_info().fullname);
			//frm.disable_save();
		}
	},

	refresh: function(frm){
		let is_allowed = frappe.user_roles.includes('Administrator');
		frm.toggle_enable(
			[
				"branch"
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

			if (frm.doc.type == "Cellphone" || frm.doc.type == "Tablet") {
				frm.set_value('charger', 1)
				frm.refresh_field('charger')
			} else {
				frm.set_value('charger', 0)
				frm.refresh_field('charger')
			}

			//frm.disable_save();
		}else{
			if(!frappe.user_roles.includes('Administrator')){
				frm.set_df_property('type', 'read_only', 1);
				frm.set_df_property('brand', 'read_only', 1);
				frm.set_df_property('model', 'read_only', 1);
				frm.set_df_property('model_number', 'read_only', 1);
				frm.set_df_property('ram', 'read_only', 1);
				frm.set_df_property('internal_memory', 'read_only', 1);
				frm.set_df_property('disk_type', 'read_only', 1);
				frm.set_df_property('color', 'read_only', 1);
				frm.set_df_property('category', 'read_only', 1);
				frm.set_df_property('charger', 'read_only', 1);
				frm.set_df_property('case_box_or_bag', 'read_only', 1);
				frm.set_df_property('appraisal_value', 'read_only', 1);
				frm.set_df_property('assistant_appraiser', 'read_only', 1);
				frm.set_df_property('comments', 'read_only', 1);
				frm.set_df_property('charger', 'read_only', 1);
				frm.set_df_property('case', 'read_only', 1);
				frm.set_df_property('box', 'read_only', 1);
				frm.set_df_property('earphones', 'read_only', 1);
				frm.set_df_property('others', 'read_only', 1);
				frm.set_df_property('pin', 'read_only', 1);
				frm.set_df_property('manual', 'read_only', 1);
				frm.set_df_property('sim_card', 'read_only', 1);
				frm.set_df_property('sd_card', 'read_only', 1);
				frm.set_df_property('bag', 'read_only', 1);
				frm.set_df_property('extra_battery', 'read_only', 1);
				frm.set_df_property('extra_lens', 'read_only', 1);
				frm.set_df_property('not_openline', 'read_only', 1);
			}
		}


		frm.set_df_property('disk_type', 'hidden', 1);
		frm.set_df_property('internet_connection_capability', 'hidden', 1);
		frm.set_df_property('bag', 'hidden', 1);
		frm.set_df_property('extra_battery', 'hidden', 1);
		frm.set_df_property('extra_lens', 'hidden', 1);
		// frm.add_custom_button('Update Data', function(){
		// 	frappe.call({
		// 		method: 'pawnshop_management.pawnshop_management.custom_codes.import_gadgets_info.update_gadgets_data',
		// 		callback: (r) =>{
		// 			frappe.show_alert({
		// 				message:__('Update Successful'),
		// 				indicator:'green'
		// 			}, 5)
		// 		}
		// 	})
		// });

		frm.set_query('brand', function(){
			if (frm.doc.type == "Cellphone") {
				return {
					"filters": {
						"cellphone": 1
					}
				}	
			} else if (frm.doc.type == "Tablet") {
				return {
					"filters": {
						"tablet": 1
					}
				}
			} else if (frm.doc.type == "Laptop") {
				return {
					"filters": {
						"laptop": 1
					}
				}
			} else if (frm.doc.type == "Camera") {
				return {
					"filters": {
						"camera": 1
					}
				}
			} else if (frm.doc.type == "Motorcycle") {
				return {
					"filters": {
						"motorcycle": 1
					}
				}
			}
		});
		frm.set_query('model', function(){
			if (frm.doc.type == "Laptop") {
				if (frm.doc.brand != "Apple") {
					return {
						"filters": {
							"type": frm.doc.type,
							"brand": "",
							"workflow_state": "Accepted"
						}
					}
				} else {
					return {
						"filters": {
							"type": frm.doc.type,
							"brand": frm.doc.brand,
							"workflow_state": "Accepted"
						}
					}
				}
			} else {
				return {
					"filters": {
						"type": frm.doc.type,
						"brand": frm.doc.brand,
						"workflow_state": "Accepted"
					}
				}
			}
		});
		frm.set_query('assistant_appraiser', function() {
			return {
				"filters": {
					"role_profile_name": [
						"in", 
						[
							"Appraiser",
							"Supervisor",
							"Appraiser/Cashier",
							"Vault Custodian",
							"Operations Manager",
							"Area Manager"
						]
					]
				}
			};
		});
	},

	assistant_appraiser: function(frm){
		//if all required fields are not yet filled up, do not allow encoding of assistant appraiser
		let required_fields = ['brand', 'model', 'model_number','color'];
		let all_filled = required_fields.every(field => frm.doc[field]);

		if (!all_filled) {
			if (!frm.message_shown) {
				frappe.msgprint(__('Please fill all required fields before setting the assistant appraiser.'));
				frm.message_shown = true;
			}
			frm.set_value('assistant_appraiser', '');
			frm.set_value('assistant_appraiser_name', '');
			frm.refresh_field('assistant_appraiser');
			frm.refresh_field('assistant_appraiser_name');
		} else {
			frm.message_shown = false;
			//inform assisting appraiser name to perform their duties
			frappe.msgprint(__('Hello {0}, Please verify the encoded information against the actual gadget, then click Save once confirmed.', [frm.doc.assistant_appraiser_name]));
			
		}
	},

	branch: function(frm){
		show_item_no(frm)
	},

	type: function(frm){
		if (frm.doc.type == "Cellphone") {
			unhide_hidden_fields(frm);
			require_unrequired_fields(frm);
			frm.set_value('model_number', "");
			frm.refresh_field('model_number')
			frm.set_df_property('model', 'label', 'Model');
			frm.set_df_property('model_number', 'label', 'Model Number');
			frm.set_df_property('disk_type', 'reqd', 0);
			frm.set_df_property('disk_type', 'hidden', 1);
			frm.set_df_property('internet_connection_capability', 'reqd', 0);
			frm.set_df_property('internet_connection_capability', 'hidden', 1);
			frm.set_df_property('bag', 'hidden', 1);
			frm.set_df_property('extra_battery', 'hidden', 1);
			frm.set_df_property('extra_lens', 'hidden', 1);
		} else if (frm.doc.type == "Tablet") {
			unhide_hidden_fields(frm);
			require_unrequired_fields(frm);
			frm.set_value('model_number', "");
			frm.refresh_field('model_number')
			frm.set_df_property('model', 'label', 'Model');
			frm.set_df_property('model_number', 'label', 'Model Number');
			frm.set_df_property('disk_type', 'reqd', 0);
			frm.set_df_property('disk_type', 'hidden', 1);
			frm.set_df_property('bag', 'hidden', 1);
			frm.set_df_property('extra_battery', 'hidden', 1);
			frm.set_df_property('extra_lens', 'hidden', 1);
		} else if (frm.doc.type == "Laptop") {
			unhide_hidden_fields();
			require_unrequired_fields(frm);
			frm.set_value('model_number', "");
			frm.refresh_field('model_number')
			frm.set_df_property('model', 'label', 'Processor & Generation');
			frm.set_df_property('model_number', 'label', 'Model Name');
			frm.set_df_property('internet_connection_capability', 'reqd', 0);
			frm.set_df_property('internet_connection_capability', 'hidden', 1);
			frm.set_df_property('charger', 'hidden', 1);
			frm.set_df_property('pin', 'hidden', 1);
			frm.set_df_property('sim_card', 'hidden', 1);
			frm.set_df_property('sd_card', 'hidden', 1);
			frm.set_df_property('bag', 'hidden', 1);
			frm.set_df_property('extra_battery', 'hidden', 1);
			frm.set_df_property('extra_lens', 'hidden', 1);
		} else if (frm.doc.type == "Camera") {
			unhide_hidden_fields();
			require_unrequired_fields(frm);
			frm.set_df_property('model', 'label', 'Model');
			frm.set_value('model_number', "N/A")
			frm.refresh_field('model_number')
			frm.set_df_property('model_number', 'reqd', 0);
			frm.set_df_property('model_number', 'hidden', 1);
			frm.set_df_property('ram', 'reqd', 0);
			frm.set_df_property('ram', 'hidden', 1);
			frm.set_df_property('internal_memory', 'reqd', 0);
			frm.set_df_property('internal_memory', 'hidden', 1);
			frm.set_df_property('disk_type', 'reqd', 0);
			frm.set_df_property('disk_type', 'hidden', 1);
			frm.set_df_property('internet_connection_capability', 'reqd', 0);
			frm.set_df_property('internet_connection_capability', 'hidden', 1);
			frm.set_df_property('charger', 'hidden', 1);
			frm.set_df_property('case', 'hidden', 1);
			frm.set_df_property('box', 'hidden', 1);
			frm.set_df_property('earphones', 'hidden', 1);
			frm.set_df_property('pin', 'hidden', 1);
			frm.set_df_property('manual', 'hidden', 1);
			frm.set_df_property('sim_card', 'hidden', 1);
		}

		if (frm.doc.type == "Cellphone" || frm.doc.type == "Tablet") {
			frm.set_value('charger', 1)
			frm.refresh_field('charger')
		} 
	},

	brand: function(frm){
		if (frm.doc.type == "Laptop" && frm.doc.brand == "Apple") {
			frm.set_df_property('internal_memory', 'reqd', 0)
			frm.set_df_property('ram', 'reqd', 0);
			frm.refresh_field('ram')
			frm.refresh_field('internal_memory')
		}else if (frm.doc.brand == "Apple") {
			frm.set_df_property('ram', 'reqd', 0);
			frm.refresh_field('ram')
		}
	},

	model:function(frm){
		compute_nj_av(frm);
	},

	category: function(frm){
		compute_nj_av(frm);
	},

	charger: function(frm){
		compute_nj_av(frm)
	},

	not_openline: function(frm){
		compute_nj_av(frm)
	}
});


function compute_nj_av(frm) {
	frappe.db.get_value('Models', frm.doc.model, ['defective', 'minimum', 'maximum', 'no_charger_less']).then(function(r){
		let price_suggestion = r.message;
		var initial_price;
		if (frm.doc.category == "Maximum") {
			initial_price = parseFloat(price_suggestion.maximum);
		} else if (frm.doc.category == "Minimum") {
			initial_price = parseFloat(price_suggestion.minimum);
		} else {
			initial_price = parseFloat(price_suggestion.defective);
		}

		if(price_suggestion.no_charger_less != 1){
			if (frm.doc.charger == 0){
				initial_price = initial_price - 300;
			}
		}

		if(frm.doc.not_openline == 1){
			//initial_price = initial_price - 1500;
			initial_price = initial_price * 0.85;
			initial_price = Math.round(initial_price / 100) * 100;
			if(initial_price < 0){
				initial_price = 0;
			}
		}
		frm.set_value('appraisal_value', initial_price)
		frm.refresh_field('appraisal_value')
	});
}

function show_item_no(frm) {
	frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['item_count', 'inventory_count'])
	.then(value => {
		frappe.db.get_list('Branch IP Addressing', {
			fields: ['branch_code'],
			filters: {
				name: frm.doc.branch
			}
		}).then(records => {
			let branch_code = records[0].branch_code;
			let non_jewelry_inventory_count = parseInt(value.message.inventory_count);
			let non_jewelry_count = parseInt(value.message.item_count)
			frm.set_value('batch_number', non_jewelry_inventory_count)
			frm.set_value('item_no', branch_code+ '-' + non_jewelry_inventory_count + 'NJ' + '-' + non_jewelry_count)
		})
	})
}

function unhide_hidden_fields(frm) {
	if (cur_frm.get_docfield('model_number').hidden) {
		cur_frm.set_df_property('model_number', 'hidden', 0);
	}

	if (cur_frm.get_docfield('ram').hidden) {
		cur_frm.set_df_property('ram', 'hidden', 0);
	}

	if (cur_frm.get_docfield('internal_memory').hidden) {
		cur_frm.set_df_property('internal_memory', 'hidden', 0);
	}

	if (cur_frm.get_docfield('disk_type').hidden) {
		cur_frm.set_df_property('disk_type', 'hidden', 0);
	}

	if (cur_frm.get_docfield('internet_connection_capability').hidden) {
		cur_frm.set_df_property('internet_connection_capability', 'hidden', 0);
	}

	if (cur_frm.get_docfield('charger').hidden) {
		cur_frm.set_df_property('charger', 'hidden', 0);
	}

	if (cur_frm.get_docfield('case').hidden) {
		cur_frm.set_df_property('case', 'hidden', 0);
	}

	if (cur_frm.get_docfield('box').hidden) {
		cur_frm.set_df_property('box', 'hidden', 0);
	}

	if (cur_frm.get_docfield('earphones').hidden) {
		cur_frm.set_df_property('earphones', 'hidden', 0);
	}

	if (cur_frm.get_docfield('pin').hidden) {
		cur_frm.set_df_property('pin', 'hidden', 0);
	}

	if (cur_frm.get_docfield('manual').hidden) {
		cur_frm.set_df_property('manual', 'hidden', 0);
	}

	if (cur_frm.get_docfield('sim_card').hidden) {
		cur_frm.set_df_property('sim_card', 'hidden', 0);
	}

	if (cur_frm.get_docfield('sd_card').hidden) {
		cur_frm.set_df_property('sd_card', 'hidden', 0);
	}

	if (cur_frm.get_docfield('bag').hidden) {
		cur_frm.set_df_property('bag', 'hidden', 0);
	}

	if (cur_frm.get_docfield('extra_battery').hidden) {
		cur_frm.set_df_property('extra_battery', 'hidden', 0);
	}

	if (cur_frm.get_docfield('extra_lens').hidden) {
		cur_frm.set_df_property('extra_lens', 'hidden', 0);
	}
}

function require_unrequired_fields(frm) {
	frm.set_df_property('model_number', 'reqd', 1);
	frm.set_df_property('ram', 'reqd', 1);
	frm.set_df_property('internal_memory', 'reqd', 1);
	frm.set_df_property('disk_type', 'reqd', 1);
	frm.set_df_property('internet_connection_capability', 'reqd', 1);
}