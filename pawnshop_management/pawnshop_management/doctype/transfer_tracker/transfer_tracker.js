// Copyright (c) 2024, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transfer Tracker', {
	// refresh: function(frm) {

	// }

	onload: function(frm) {
		// set value of date_of_transfer to current date
		//check if form is new
		if (frm.is_new()) {
		frm.set_value('date_of_transfer', frappe.datetime.nowdate());

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

						//if user is a Subastado member and not Administrator, set origin to Subastado NJ
						if (frappe.user.has_role("Subastado member") && frappe.session.user != "Administrator") {	
							frm.set_value('origin', 'Subastado NJ');
						}else{
							frm.set_value('origin', records[0].name);
						}
						
						frm.refresh_field('origin');

					})
				}
			})

		// If user has role Subastado member, Transfer Type should be Transfer of Display Items and should be read only
		if (frappe.user.has_role("Subastado member") && frappe.session.user != "Administrator") {
			frm.set_value('transfer_type', 'Transfer of Display Items');
			frm.set_df_property('transfer_type', 'read_only', 1);
			frm.refresh_field('transfer_type');
		}	
		

		//Put name of current user in the field released_by
		frm.set_value('released_by', frappe.session.user);
		frm.refresh_field('released_by');
		//Disable save button until witnessed_by and rover is filled out
		frm.disable_save();
		//Hide nj_items table until transfer_type is filled out
		frm.set_df_property('nj_items', 'hidden', 1);
		frm.refresh_field('nj_items');
		}
		
		
	},

	origin: function(frm) {

		frappe.db.get_value("Pawnshop Naming Series", frm.doc.origin, "nj_transfer_form")
		.then(r => {
			let current_form = r.message.nj_transfer_form;
			frappe.db.get_value("Branch IP Addressing", frm.doc.origin, "branch_code")
				.then(r => {
					let branchCode = r.message.branch_code;
					if (frappe.user.has_role("Subastado member") && frappe.session.user != "Administrator") {
					current_form = "SCG-"+ current_form	
					}else{
					current_form = branchCode + "-"+ current_form	
					}
						frm.set_value('transfer_no', current_form );
						frm.refresh_field('transfer_no');
				})
		})
	},

	witnessed_by: function(frm){
		if (frm.doc.witnessed_by != null) {
			//ask for password
			frappe.prompt({
				label: 'Password',
				fieldname: 'password',
				fieldtype: 'Password'
			}, (password) => {
				frappe.call({
					method: 'pawnshop_management.pawnshop_management.custom_codes.passwords.check_password',
					args: {
						user: String(frm.doc.witnessed_by),
						pwd: password.password
					},
					callback: function(usr){
						if (frm.doc.witnessed_by == usr.message) {
							frappe.msgprint({
								title: __('Approved!'),
								indicator: 'green',
								message: __('Witness Approved')
							});
							//check if both witnessed_by and rover is filled out before enabling save
							if (frm.doc.rover != null) {
								frm.enable_save();
							}

						} else {
							frm.set_value('witnessed_by', null);
							frm.refresh_field('witnessed_by');
							frappe.msgprint({
								title: __('Password Invalid'),
								indicator: 'red',
								message: __(usr.message)
							});
						}
					}
				})
			})
		}
	},
	rover: function(frm){
		if (frm.doc.rover != null) {
			//ask for password
			frappe.prompt({
				label: 'Password',
				fieldname: 'password',
				fieldtype: 'Password'
			}, (password) => {
				frappe.call({
					method: 'pawnshop_management.pawnshop_management.custom_codes.passwords.check_password',
					args: {
						user: String(frm.doc.rover),
						pwd: password.password
					},
					callback: function(usr){
						if (frm.doc.rover == usr.message) {
							frappe.msgprint({
								title: __('Approved!'),
								indicator: 'green',
								message: __('Rover Approved')
							});
							//check if both witnessed_by and rover is filled out before enabling save
							if (frm.doc.witnessed_by != null) {
								frm.enable_save();
							}
						} else {
							frm.set_value('rover', null);
							frm.refresh_field('rover');
							frappe.msgprint({
								title: __('Password Invalid'),
								indicator: 'red',
								message: __(usr.message)
							});
						}
					}
				})
			})
		}

	},

	transfer_type: function(frm){
		if (frm.doc.transfer_type == "Pull out of Expired Sangla") {
				//Set Destination to Subastado NJ and make it read only
				frm.set_value('destination', 'Subastado NJ');
				frm.set_df_property('destination', 'read_only', 1);
				frm.refresh_field('destination');
				//Set filter for NJ items table based on the origin except if user is a Subastado member
				frm.set_query('item_no', 'nj_items', function(){
					return {
						filters: {
							workflow_State: 'Collected',
							branch: frm.doc.origin
						}
					}
				})
						
		}else if (frm.doc.transfer_type == "Transfer of Display Items") {
				frm.set_value('destination', '');
				frm.set_df_property('destination', 'read_only', 0);
				frm.refresh_field('destination');
				//Set filter for NJ items table based on the origin except if user is a Subastado member
				frm.set_query('item_no', 'nj_items', function(){
					return {
						filters: {
							workflow_State: 'For Sale',
							current_location: frm.doc.origin
						}
					}
				})

		}
		//Show nj_items table
		frm.set_df_property('nj_items', 'hidden', 0);
		frm.refresh_field('nj_items');

		}

	});

	frappe.ui.form.on('Transfer Items', {
	//do something when an item is added to the nj_items table
	nj_items_add: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		//Nothing to do here yet
	},

	item_no: async function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		//Check if the item_no already exists in the table
		let exists = false;
		frm.doc.nj_items.forEach(function(item) {
			if(item.item_no == row.item_no && item.name != row.name) {
				exists = true;
			}
		});
		if(exists) {
			frappe.msgprint('Item already exists in the table');
			//delete the row
			frm.get_field('nj_items').grid.grid_rows_by_docname[row.name].remove();
			frm.refresh_field('nj_items');
			return;
		}

		//get total pt_principal from all item_no in the table and set it to total_cost
		if(frm.doc.transfer_type == "Pull out of Expired Sangla"){
			//There is no pt_principal yet, get it from the most recent Pawn Ticket Non Jewelry of the NJ item
			// 1) Get parent names from child rows
			const childRows = await frappe.db.get_list('Non Jewelry List', {
			fields: ['parent'],
			filters: { item_no: row.item_no, parenttype: 'Pawn Ticket Non Jewelry' },
			limit: 500
			});
			const parents = childRows.map(r => r.parent);

			// 2) Get the latest PTNJ by expiry_date with workflow status expired
			let latest = null;
			if (parents.length) {
			const ptnj = await frappe.db.get_list('Pawn Ticket Non Jewelry', {
				fields: ['name', 'expiry_date', 'desired_principal'],
				filters: { name: ['in', parents], workflow_state: ['!=', 'Rejected'] },
				order_by: 'expiry_date desc',
				limit: 1
			});
			latest = ptnj[0];
			}
			if (latest) {
			// 3) Set the pt_principal field in the child table row and the name in the last_pawn_ticket field of the row
			frappe.model.set_value(cdt, cdn, 'pt_principal', latest.desired_principal);
			frappe.model.set_value(cdt, cdn, 'last_pawn_ticket', latest.name);
			frm.refresh_field('nj_items');
			}

			let total = 0;
			frm.doc.nj_items.forEach(function(item) {
				total += parseFloat(item.pt_principal);
			});
			//set total_cost to total
			frm.set_value('total_cost', total);
			frm.refresh_field('total_cost');


		}else if(frm.doc.transfer_type == "Transfer of Display Items"){
			//get the pt_principal from the Non Jewelry Items doctype
			let pt_principal = await frappe.db.get_value('Non Jewelry Items', row.item_no, 'pt_principal');
			frappe.model.set_value(cdt, cdn, 'pt_principal', pt_principal.message.pt_principal);
			frappe.model.set_value(cdt, cdn, 'last_pawn_ticket', 'Unnecessary');
			frm.refresh_field('nj_items');

			//get total pt_principal from all item_no in the table and set it to total_cost
			let total = 0;
			frm.doc.nj_items.forEach(function(item) {
				total += parseFloat(item.pt_principal);
			});
			//set total_cost to total
			frm.set_value('total_cost', total);
			frm.refresh_field('total_cost');
		}
		
	},
	nj_items_remove: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		//get total pt_principal from all item_no in the table and set it to total_cost
		let total = 0;
		
		frm.doc.nj_items.forEach(function(item) {
			total += item.pt_principal;
		});
		//set total_cost to total
		frm.set_value('total_cost', total);
		frm.refresh_field('total_cost');
	}
});


