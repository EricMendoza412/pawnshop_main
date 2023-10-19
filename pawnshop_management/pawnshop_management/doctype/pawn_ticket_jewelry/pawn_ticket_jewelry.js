// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pawn Ticket Jewelry', {
	after_save: function(frm){
		frm.set_df_property('customers_tracking_no', 'read_only', 1);
	},

	after_workflow_action: function(frm){
		frm.reload_doc()
	},

	refresh: function(frm){

		let is_allowed = frappe.user_roles.includes('Administrator');
		frm.toggle_enable(['date_loan_granted', 'branch'], is_allowed)

		if(frappe.user_roles.includes('Support Team')){
			frm.set_df_property('date_loan_granted', 'read_only', 0);
			frm.set_df_property('branch', 'read_only', 0);
		}

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

						frappe.db.get_value('Pawnshop Naming Series', records[0].name, 'jewelry_inventory_count')
						.then(r =>{
							let jewelry_inventory_count = r.message.jewelry_inventory_count
							frm.set_query('item_no', 'jewelry_items', function(){
								return {
									filters: {
										batch_number: String(jewelry_inventory_count),
										branch: records[0].name
									}
								}
							})
						})
					})
				}
			})
		}
		
		frm.fields_dict["jewelry_items"].grid.grid_buttons.find(".grid-add-row")[0].innerHTML = "Add Item"	//Change "Add Row" button of jewelry_items table into "Add Item"		

		if(frm.customers_tracking_no != null)
		{
			let html = ``;
			frappe.call({
				method: "pawnshop_management.pawnshop_management.utils.get_contact_image_by_customer",
				args: {
					customer: frm.doc.customers_tracking_no,
				},
				callback: function(r) {
					if (r.message) {
						$(frm.fields_dict['default_image'].wrapper).html(r.message);
					}
				}

			});
		}

	},

	branch: function(frm){
		if (frm.is_new() && frm.doc.amended_from == null) {
			frm.set_value('date_loan_granted', frappe.datetime.nowdate())
		}
		if (frm.is_new()){
			show_tracking_no(frm);
		}
	},

	date_loan_granted: function(frm){
		let default_maturity_date = frappe.datetime.add_days(frm.doc.date_loan_granted, 30);
		frm.set_value('maturity_date', default_maturity_date);

		let defaul_expiry_date = frappe.datetime.add_days(frm.doc.date_loan_granted, 120);
		frm.set_value('expiry_date', defaul_expiry_date);
	},

	desired_principal: function(frm, cdt, cdn) {
		set_series(frm);
		frm.refresh_fields('pawn_ticket');
		set_item_interest(frm)
	},

	inventory_tracking_no: function(frm, cdt, cdn){
		set_total_appraised_amount(frm, cdt, cdn);
	},

	customers_tracking_no: function(frm){
        let html = ``;
        frappe.call({
            method: "pawnshop_management.pawnshop_management.utils.get_contact_image_by_customer",
            args: {
                customer: frm.doc.customers_tracking_no,
            },
            callback: function(r) {
                if (r.message) {
                    $(frm.fields_dict['default_image'].wrapper).html(r.message);
                }
            }

        });


	},

	item_series: function(frm){
		if (frm.is_new()){
			show_tracking_no(frm);
		}		
	}
});

frappe.ui.form.on('Jewelry List', {

	item_no: function(frm, cdt, cdn){
		let table_length = parseInt(frm.doc.jewelry_items.length)
		if (frm.doc.jewelry_items.length > 1) {
			for (let index = 0; index < table_length - 1; index++) {
				if (frm.doc.jewelry_items[table_length-1].item_no == frm.doc.jewelry_items[index].item_no) {
					frm.doc.jewelry_items.pop(table_length-1);
					frm.refresh_field('jewelry_items');
					frappe.msgprint({
						title:__('Notification'),
						indicator:'red',
						message: __('Added item is already in the list. Item removed.')
					});
					set_total_appraised_amount(frm, cdt, cdn);
				}
			}
		}	

		
	},
	jewelry_items_add: function(frm, cdt, cdn){
		let table_length = parseInt(frm.doc.jewelry_items.length)
		if (table_length > 4) {
			frm.fields_dict["jewelry_items"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "hidden";
		}
	},

	suggested_appraisal_value: function(frm, cdt, cdn){
		set_total_appraised_amount(frm,cdt, cdn);
	},

	jewelry_items_remove: function(frm, cdt, cdn){ //calculate appraisal value when removing items
		let table_length = parseInt(frm.doc.jewelry_items.length)
		set_total_appraised_amount(frm, cdt, cdn);
		if (table_length <= 4) {
			frm.fields_dict["jewelry_items"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "visible";
		}
	}
});


function set_series(frm) { //Set the pawn ticket series
	if (frm.is_new()){

		if(parseInt(frm.doc.desired_principal) > 8000 || parseInt(frm.doc.desired_principal) < 1500){
			frm.set_value('item_series', "B")
		}else{
			frm.set_value('item_series', "A")
		}
		frm.refresh_field('item_series');
	}	
}

function show_tracking_no(frm){ //Sets inventory tracking number
	let branch_code = 0;

	frappe.db.get_list('Branch IP Addressing', {
		fields: ['branch_code'],
		filters: {
			name: frm.doc.branch
		}
	}).then(records => {
		branch_code = records[0].branch_code;

		if (frm.doc.amended_from == null) {
			let jewelry_inv_count;
			if (frm.doc.item_series == "A") {
				frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['a_series', 'jewelry_inventory_count'])
				.then(value => {
					let tracking_no = value.message;
					jewelry_inv_count = parseInt(tracking_no.jewelry_inventory_count);
					let new_ticket_no = parseInt(tracking_no.a_series);
					frm.set_value('pawn_ticket', branch_code+"-"+ new_ticket_no);
					frm.set_value('inventory_tracking_no', branch_code+"-"+ jewelry_inv_count + 'J');
					frm.refresh_field('pawn_ticket');
				})
			} else if (frm.doc.item_series == "B") {
				frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['b_series', 'jewelry_inventory_count'])
				.then(value => {
					let tracking_no = value.message;
					jewelry_inv_count = parseInt(tracking_no.jewelry_inventory_count);
					let new_ticket_no = parseInt(tracking_no.b_series);
					frm.set_value('pawn_ticket', branch_code+"-"+ new_ticket_no + frm.doc.item_series);
					frm.set_value('inventory_tracking_no', branch_code+"-"+ jewelry_inv_count + 'J');
					frm.refresh_field('pawn_ticket');
				})
			} else if (frm.doc.item_series == "Automatic") {
				frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['b_series', 'jewelry_inventory_count'])
				.then(value => {
					let tracking_no = value.message;
					jewelry_inv_count = parseInt(tracking_no.jewelry_inventory_count);
					frm.set_value('inventory_tracking_no', branch_code+"-"+ jewelry_inv_count + 'J');
				})
				}
			
		} else if (frm.doc.amended_from != ""){
			var previous_pt = frm.doc.amended_from      //Naming for the next document created of amend
			if (count_dash_characters(previous_pt) < 2) {
				frm.set_value('pawn_ticket', frm.doc.amended_from + "-1");
				frm.refresh_field('pawn_ticket');
			} else {
				var index_of_last_dash_caharacter = previous_pt.lastIndexOf("-")
				var current_amend_count = index_of_last_dash_caharacter.slice(index_of_last_dash_caharacter, -1)
				frm.set_value('pawn_ticket', frm.doc.amended_from + "-" + parseInt(current_amend_count) + 1);
				frm.refresh_field('pawn_ticket');
			}
		}



	})
}


function set_total_appraised_amount(frm, cdt, cdn) { // Calculate Principal Amount
	let temp_principal = 0.00;
	$.each(frm.doc.jewelry_items, function(index, item){
		temp_principal += parseFloat(item.desired_principal);
	});
	frm.set_value('desired_principal', temp_principal)
	set_item_interest(frm)
	return temp_principal
}

function set_item_interest(frm) {
	var principal = parseFloat(frm.doc.desired_principal);
	var interest = 0.00;
	var net_proceeds = 0.00;

	frappe.db.get_single_value('Pawnshop Management Settings', 'jewelry_interest_rate').then(value => {
		interest = (parseFloat(value)/100) * (parseFloat(principal));
		frm.set_value('interest', interest);
		net_proceeds = principal - interest;
		frm.set_value('net_proceeds', net_proceeds)
	});
}

function null_checker(number) {
	if (number == null) {
		number = 0;
	}
	return parseInt(number)
}

function count_dash_characters(string) {
	var dash_character_count = 0
	for (let index = 0; index < string.length; index++) {
		if (string[index] == "-") {
			dash_character_count++
		}
	}
	return dash_character_count
}