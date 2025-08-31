// Copyright (c) 2025, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Installment Agreement Form', {

	refresh: function(frm) {
		if (frm.doc.down_payment === 0) {
            // Hide the print icon (top right of the form header)
            frm.page.hide_icon_group('print');
			//programmatically hide the Menu items
			frm.page.clear_menu();
        }


		
	},

	onload: function(frm) {
		if (frm.is_new()) {
			frm.set_value('start_date', frappe.datetime.get_today());

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
						frm.set_value('branch', records[0].name);
						frm.refresh_field('branch');

						// only allow Non Jewelry items with status "For Sale" to be selected in field "item_no"
						frm.set_query('item_no', function() {
							return {
								filters: {
									workflow_state: 'For Sale'
								}
							};
						});
					});
				}
			});
		}
	},

	type: function(frm) {
	//if type is laptop, hide locked_to_a_network and internet_connection_capability
		if(frm.doc.type == 'Laptop'){
			frm.set_df_property('locked_to_a_network', 'hidden', 1);
			frm.set_df_property('internet_connection_capability', 'hidden', 1);
			frm.set_df_property('disk_type', 'hidden', 0);
			//hide locked_to_a_network and internet_connection_capability in print format
			frm.set_df_property('locked_to_a_network', 'print_hide', 1);
			frm.set_df_property('internet_connection_capability', 'print_hide', 1);
			frm.set_df_property('disk_type', 'print_hide', 0);
		}else{
			//hide disk_type
			frm.set_df_property('locked_to_a_network', 'hidden', 0);
			frm.set_df_property('internet_connection_capability', 'hidden', 0);
			frm.set_df_property('disk_type', 'hidden', 1);
			//hide disk_type in print format
			frm.set_df_property('locked_to_a_network', 'print_hide', 0);
			frm.set_df_property('internet_connection_capability', 'print_hide', 0);
			frm.set_df_property('disk_type', 'print_hide', 1);
		}
	},



	customer_tracking_no: function(frm) {
		//Get the mobile_no from the customer_primary_contact from the customer using the customer_tracking_no field
		frappe.db.get_value('Customer', frm.doc.customer_tracking_no, 'customer_primary_contact', (r) => {
			if (r.customer_primary_contact) {
				frappe.db.get_value('Contact', r.customer_primary_contact, 'mobile_no', (res) => {
					frm.set_value('contact_number', res.mobile_no);
				});
			}
		});
	},

	item_no: function(frm) {
		if(frm.doc.type == 'Cellphone'){
			frm.set_df_property('locked_to_a_network', 'hidden', false);
		}else{
			frm.set_df_property('locked_to_a_network', 'hidden', true);
			frm.set_value('locked_to_a_network', '');
		}
		//New Max period of Installment
		// 2 months = PHP 4,000 – 9,999
		// 3 months = PHP 10,000 – 19,999
		// 4 months = PHP 20,000 and above
		
		
		if ( frm.doc.total_price >= 4000 && frm.doc.total_price <= 9999 ) {
			var max_period = 60; //60 days
			frm.set_value('due_date', frappe.datetime.add_days(frm.doc.start_date, max_period));
		}else if ( frm.doc.total_price >= 10000 && frm.doc.total_price <= 19999 ) {
			var max_period = 90; //90 days
			frm.set_value('due_date', frappe.datetime.add_days(frm.doc.start_date, max_period));
		} else if ( frm.doc.total_price >= 20000 ) {
			var max_period = 120; //120 days
			frm.set_value('due_date', frappe.datetime.add_days(frm.doc.start_date, max_period));
		} else {
			let d = frappe.msgprint({
					title: __('Notice'),
					message: __('Total Price must be at least PHP 4,000 to set an Item No.'),
					indicator: 'red',
					primary_action: {
						label: __('OK'),
						action() {
							location.reload(); // Refresh the page on OK
						}
					}
				});
			frm.set_value('total_price', 0);
			frm.set_value('down_payment', 0);

			}
	},

	// down_payment: function(frm) {
	// 	if ((frm.doc.total_price * 0.25) > frm.doc.down_payment) {
	// 		frappe.msgprint(__('Down Payment must be at least 25% of the Total Price.\n In this case, it must be at least: {0}', [Math.ceil(frm.doc.total_price * 0.25)]));
	// 		frm.set_value('down_payment', Math.ceil(frm.doc.total_price * 0.25));
	// 	}
	// 	frm.set_value('outstanding_balance', frm.doc.total_price - frm.doc.down_payment);
	// }
	total_price: function(frm) {
		//put value of total_price in outstanding_balance
		frm.set_value('outstanding_balance', frm.doc.total_price);

	},

	branch: function(frm) { //Select naming series with regards to the branch
			if (frm.doc.branch == "Garcia's Pawnshop - CC") {
				frm.set_value('naming_series', "1-.######.NJIS")
			} else if (frm.doc.branch == "Garcia's Pawnshop - GTC") {
				frm.set_value('naming_series', "4-.######.NJIS")
			} else if (frm.doc.branch == "Garcia's Pawnshop - MOL") {
				frm.set_value('naming_series', "6-.######.NJIS")
			} else if (frm.doc.branch == "Garcia's Pawnshop - POB") {
				frm.set_value('naming_series', "3-.######.NJIS")
			} else if (frm.doc.branch == "Garcia's Pawnshop - TNZ") {
				frm.set_value('naming_series', "5-.######.NJIS")
			} else if (frm.doc.branch == "Garcia's Pawnshop - ALP") {
				frm.set_value('naming_series', "7-.######.NJIS")
			} else if (frm.doc.branch == "Garcia's Pawnshop - NOV") {
				frm.set_value('naming_series', "8-.######.NJIS")
			} else if (frm.doc.branch == "Garcia's Pawnshop - PSC") {
				frm.set_value('naming_series', "9-.######.NJIS")
			} else if (frm.doc.branch == "TEST") {
				frm.set_value('naming_series', "20-.######.NJIS")
			}
		
	}
});
