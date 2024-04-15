// Copyright (c) 2023, Rabie Moses Santillan and contributors
// For license information, please see license.txt

frappe.ui.form.on('Acknowledgement Receipt', {
	// refresh: function(frm) {

	// }
	onload: function(frm){
		frm.set_df_property('pawn_ticket_no', 'hidden', 1);
		frm.set_df_property('subasta_sales_no', 'hidden', 1);

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
	validate: function(frm){
		if (frm.doc.total <= 0){
			frappe.throw('Please input amount')
		}
	},

	branch: function(frm){
		select_naming_series(frm);
	},

	pawn_ticket_type: function(frm){
		frm.set_df_property('pawn_ticket_type', 'read_only', 1);
		if(frm.doc.pawn_ticket_type == "-Select-"){
			frm.set_df_property('subasta_sales_no', 'hidden', 1);
			frm.set_df_property('pawn_ticket_no', 'hidden', 1);
		}else if(frm.doc.pawn_ticket_type == "Subastado Sales Commissions"){
			frm.set_df_property('subasta_sales_no', 'hidden', 0);
			frm.set_df_property('pawn_ticket_no', 'hidden', 1);
		}else{
			frm.set_df_property('subasta_sales_no', 'hidden', 1);
			frm.set_df_property('pawn_ticket_no', 'hidden', 0);
		}
	},

	pawn_ticket_no: function(frm){
		frm.set_df_property('pawn_ticket_no', 'read_only', 1);
	},

	subasta_sales_no: function(frm){
		frm.set_df_property('subasta_sales_no', 'read_only', 1);
	}

});

function select_naming_series(frm) { //Select naming series with regards to the branch

	if (frm.doc.branch == "Garcia's Pawnshop - CC") {
		frm.set_value('naming_series', "AR-1-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - GTC") {
		frm.set_value('naming_series', "AR-4-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - MOL") {
		frm.set_value('naming_series', "AR-6-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - POB") {
		frm.set_value('naming_series', "AR-3-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - TNZ") {
		frm.set_value('naming_series', "AR-5-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - ALP") {
		frm.set_value('naming_series', "AR-7-.######")
	} else if (frm.doc.branch == "Garcia's Pawnshop - NOV") {
		frm.set_value('naming_series', "AR-8-.######")
	} else if (frm.doc.branch == "TEST") {
		frm.set_value('naming_series', "AR-20-.######")
	}
	
	console.log(frm.doc.naming_series)
	frm.refresh_field('naming_series')
	
}
