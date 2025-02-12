// Copyright (c) 2021, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Jewelry Items', {
	onload: function(frm) {
		if (frm.is_new()) {
			//frm.set_value('main_appraiser', frappe.user_info().fullname);
			//frm.disable_save();
		}
	},

	validate: function(frm){
		if (parseFloat(frm.doc.desired_principal) > parseFloat(frm.doc.appraisal_value)) {
			frappe.throw(__('Desired principal is greater than appraisal value'));
		}
		if(frm.doc.type == "-Select-"){
			frappe.throw(__('Please choose the item type'));
		}
		if(frm.doc.karat == "-Select-"){
			frappe.throw(__('Please input item karat'));
		}
		if(frm.doc.karat_category == "-Select-"){
			frappe.throw(__('Please choose karat category'));
		}
		if(parseFloat(frm.doc.total_weight) > 500){
			frappe.throw(__('Inputted grams exceeds limit'));
		}
	},

	refresh: function(frm){

		let is_allowed = frappe.user_roles.includes('Administrator');
		frm.toggle_enable(["branch"],is_allowed);

		frm.toggle_display(['sizelength', 'selling_price', 'selling_price_per_gram'], frm.doc.workflow_state === "Pulled Out" || frm.doc.workflow_state === "Scrap" || frm.doc.workflow_state === "On Display" || frm.doc.workflow_state === "Sold")
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
		}else{
			if(!frappe.user_roles.includes('Administrator')){
				frm.set_df_property('type', 'read_only', 1);
				frm.set_df_property('total_weight', 'read_only', 1);
				frm.set_df_property('karat', 'read_only', 1);
				frm.set_df_property('karat_category', 'read_only', 1);
				frm.set_df_property('densi', 'read_only', 1);
				frm.set_df_property('additional_for_stone', 'read_only', 1);
				frm.set_df_property('color', 'read_only', 1);
				frm.set_df_property('colors_if_multi', 'read_only', 1);
				frm.set_df_property('appraisal_value', 'read_only', 1);
				frm.set_df_property('desired_principal', 'read_only', 1);
				frm.set_df_property('assistant_appraiser_acct', 'read_only', 1);
				frm.set_df_property('main_appraiser_acct', 'read_only', 1);
				frm.set_df_property('comments', 'read_only', 1);
				frm.set_df_property('karats', 'read_only', 1);
			}
			if(frappe.user_roles.includes('Support Team')){
				frm.set_df_property('type', 'read_only', 0);
				frm.set_df_property('total_weight', 'read_only', 0);
				frm.set_df_property('karat', 'read_only', 0);
				frm.set_df_property('karat_category', 'read_only', 0);
				frm.set_df_property('densi', 'read_only', 0);
				frm.set_df_property('additional_for_stone', 'read_only', 0);
				frm.set_df_property('color', 'read_only', 0);
				frm.set_df_property('colors_if_multi', 'read_only', 0);
				frm.set_df_property('appraisal_value', 'read_only', 0);
				frm.set_df_property('desired_principal', 'read_only', 0);
				frm.set_df_property('main_appraiser_acct', 'read_only', 0);
				frm.set_df_property('comments', 'read_only', 0);
				frm.set_df_property('karats', 'read_only', 0);
				frm.set_df_property('branch', 'read_only', 0);
			}
			if(frappe.user_roles.includes('Operations Manager') && frm.doc.workflow_state == "Pawned"){
				frm.set_df_property('type', 'read_only', 0);
				frm.set_df_property('karat_category', 'read_only', 0);
				frm.set_df_property('color', 'read_only', 0);
				frm.set_df_property('densi', 'read_only', 0);
				frm.set_df_property('additional_for_stone', 'read_only', 0);
				frm.set_df_property('colors_if_multi', 'read_only', 0);
				frm.set_df_property('comments', 'read_only', 0);
				frm.set_df_property('karats', 'read_only', 0);
				//if the Jewely Item is created today, the Operations manager can edit the Appraisal Value and Desired Principal
				// Also check if there is a submitted "Cash Position Report" document for today with the same "branch"
					frappe.db.count('Cash Position Report', {
						filters: {
							branch: frm.doc.branch,
							date: frappe.datetime.nowdate(),
							docstatus: 1
						}
					}).then(count => {
						if (count === 0) {
							//print message count is zero
							//frappe.msgprint({"message": "count is zero", "title": "Error"});

							let today = new Date();
							let created_date = new Date(frm.doc.creation);
							if(today.toDateString() == created_date.toDateString()){
								frm.set_df_property('appraisal_value', 'read_only', 0);
								frm.set_df_property('desired_principal', 'read_only', 0);
							}
						}
					})
				
			}
		}
		frm.set_query('assistant_appraiser_acct', function() {
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
		frm.set_query('main_appraiser_acct', function() {
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

	//assistant_appraiser: function(frm){
		// if (frm.doc.assistant_appraiser != null) {
		// 	frappe.prompt({
		// 		label: 'Password',
		// 		fieldname: 'password',
		// 		fieldtype: 'Password'
		// 	}, (password) => {
		// 		frappe.call({
		// 			method: 'pawnshop_management.pawnshop_management.custom_codes.passwords.check_password',
		// 			args: {
		// 				user: String(frm.doc.assistant_appraiser),
		// 				pwd: password.password
		// 			},
		// 			callback: function(usr){
		// 				if (frm.doc.assistant_appraiser == usr.message) {
		// 					frappe.msgprint({
		// 						title: __('Approved!'),
		// 						indicator: 'green',
		// 						message: __('Appraisal Approved')
		// 					});
		// 					frm.enable_save();
		// 				} else {
		// 					frm.set_value('assistant_appraiser', null);
		// 					frm.refresh_field('assistant_appraiser');
		// 					frappe.msgprint({
		// 						title: __('Password Invalid'),
		// 						indicator: 'red',
		// 						message: __(usr.message)
		// 					});
		// 				}
		// 			}
		// 		})
		// 	})
		// }
	//},

	branch: function(frm){
		show_item_no(frm);
	},

	appraisal_value: function(frm){
		frm.set_value('desired_principal', parseFloat(frm.doc.appraisal_value))
		frm.refresh_field('desired_principal')
	}

});

frappe.ui.form.on('Jewelry Karat List', {
	karat: function(frm, cdt, cdn){
		if (frm.doc.karats.length> 1) {
			frm.set_value('karat', 'Multiple Karat');
			frm.refresh_field('karat')
		} else {
			frm.set_value('karat', frm.doc.karats[0].karat);
			frm.refresh_field('karat')
		}
	},

	weight: function(frm, cdt, cdn){
		set_total_weight(frm, cdt, cdn)
	},

	karats_remove: function(frm, cdt, cdn){
		console.log("Hello");
		set_total_weight(frm, cdt, cdn)
	}
});

function set_total_weight(frm, cdt, cdn) {
	let total_weight = 0.00;
	$.each(frm.doc.karats, function(index, item){
		total_weight += parseFloat(item.weight);
	});
	frm.set_value('total_weight', total_weight)
	frm.refresh_field('total_weight')
}

function show_item_no(frm) {
	frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['jewelry_item_count', 'jewelry_inventory_count'])
	.then(value => {
		//get branch code
		frappe.db.get_list('Branch IP Addressing', {
			fields: ['branch_code'],
			filters: {
				name: frm.doc.branch
			}
		}).then(records => {
			let branch_code = records[0].branch_code;
			let jewelry_inventory_count = parseInt(value.message.jewelry_inventory_count);
			let jewelry_count = parseInt(value.message.jewelry_item_count)
			frm.set_value('batch_number', jewelry_inventory_count)
			frm.set_value('item_no', branch_code + '-' + jewelry_inventory_count + 'J' + '-' + jewelry_count)
		})
	})
}