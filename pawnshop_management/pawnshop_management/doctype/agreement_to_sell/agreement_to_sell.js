// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt


var branch_name;

frappe.ui.form.on('Agreement to Sell', {
	refresh: function(frm) {

		let is_allowed = frappe.user_roles.includes('Administrator') || frappe.user_roles.includes('Support Team');
		frm.toggle_enable(['date_of_sale', 'branch'], is_allowed);

	   if (frm.is_new()) {
		   frm.set_value('date_of_sale', frappe.datetime.nowdate())
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
		if (frm.doc.amended_from != null){
			var previous_pt = frm.doc.amended_from      //Naming for the next document created of amend
			const separator = previous_pt.split("-");
			
			if (separator.length == 2) {
				frm.set_value('form_number', frm.doc.amended_from + "-1");
				frm.refresh_field('form_number');
			} else {
				let new_Version = parseInt(separator[separator.length-1]);
				new_Version += 1;
				frm.set_value('form_number', separator[0] + "-" + separator[1] + "-" + new_Version);
				frm.refresh_field('pawn_ticket');
			}
		}

		},

	validate: function(frm, cdt, cdn){
			if (frm.doc.total_value <= 0){
				frappe.throw(__('Total value cannot be zero'));
			}
		},

	branch: function(frm){
	   show_form_no(frm);
	   show_tracking_no(frm);

		//Filter of Jewelry items table
		frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch, 'jewelry_inventory_count')
		.then(r =>{
			let jewelry_inventory_count = r.message.jewelry_inventory_count
			frm.set_query('item_no', 'jewelry_items', function(){
				return {
					filters: {
						batch_number: String(jewelry_inventory_count),
						branch: frm.doc.branch
					}
				}
			})
		})

	}

});

function show_tracking_no(frm){ //Sets inventory tracking number
	let branch_code = 0;

	if (frm.doc.branch == "Garcia's Pawnshop - CC") {
		branch_code = 1;
		branch_name = "CC";
	}else if(frm.doc.branch == "Garcia's Pawnshop - POB") {
		branch_code = 3;
		branch_name = "POB";
	}else if(frm.doc.branch == "Garcia's Pawnshop - GTC") {
		branch_code = 4;
		branch_name = "GTC";
	}else if(frm.doc.branch == "Garcia's Pawnshop - TNZ") {
		branch_code = 5;
		branch_name = "TNZ";
	}else if(frm.doc.branch == "Garcia's Pawnshop - MOL") {
		branch_code = 6;
		branch_name = "MOL";
	}else if(frm.doc.branch == "Garcia's Pawnshop - ALP") {
		branch_code = 7;
		branch_name = "ALP";
	}else if(frm.doc.branch == "Garcia's Pawnshop - NOV") {
		branch_code = 8;
		branch_name = "NOV";
	}else if(frm.doc.branch == "Garcia's Pawnshop - PSC") {
		branch_code = 9;
		branch_name = "PSC";
	}else if(frm.doc.branch == "TEST") {
		branch_code = 20;
		branch_name = "TEST";
	}

	if (frm.doc.amended_from == null) {
	let jewelry_inv_count;
	frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['jewelry_inventory_count'])
	.then(value => {
		let tracking_no = value.message;
		jewelry_inv_count = parseInt(tracking_no.jewelry_inventory_count);
		frm.set_value('ats_tracking_no', 'ATS-'+branch_code+"-"+ jewelry_inv_count + 'J');
	})
	}
}


function show_form_no(frm) { 
   if (frm.doc.amended_from == null) {
	let jewelryinv_count;
		frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['ats_jewelry_count'])
		.then(value => {
			let tracking_no = value.message;
			jewelryinv_count = parseInt(tracking_no.ats_jewelry_count);
			frm.set_value('form_number', branch_name+"-"+jewelryinv_count );
		})
	} 
}

function set_total_appraised_amount(frm) { // Calculate Total Amount
	let temp_principal = 0.00;
	$.each(frm.doc.jewelry_items, function(index, item){
		temp_principal += parseFloat(item.suggested_appraisal_value);
	});
	frm.set_value('total_value', temp_principal)
	frm.refresh_field('total_value')
	return temp_principal
}


frappe.ui.form.on('Jewelry List', {

	item_no: function(frm){
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
					set_total_appraised_amount(frm)
				}
			}
		}
	},
	suggested_appraisal_value: function(frm){
		set_total_appraised_amount(frm);
	},
	jewelry_items_remove: function(frm){ //calculate appraisal value when removing items
		let table_length = parseInt(frm.doc.jewelry_items.length)
		set_total_appraised_amount(frm);
		if (table_length <= 4) {
			frm.fields_dict["jewelry_items"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "visible";
		}
	}
	}	
)

