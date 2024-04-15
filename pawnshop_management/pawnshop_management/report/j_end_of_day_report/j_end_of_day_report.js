// Copyright (c) 2016, Rabie Moses Santillan and contributors
// For license information, please see license.txt
/* eslint-disable */
var default_branch = [];

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
            default_branch.push(records[0].name); 
        })
    }
});

let is_allowed = frappe.user_roles.includes('Auditor') || frappe.user_roles.includes('Administrator');
if(is_allowed){
frappe.query_reports["J End of Day Report"] = {
	"filters": [
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Select",
			options: [
				"Garcia's Pawnshop - CC", 
				"Garcia's Pawnshop - GTC", 
				"Garcia's Pawnshop - MOL",
				"Garcia's Pawnshop - POB",
				"Garcia's Pawnshop - TNZ",
				"Garcia's Pawnshop - ALP",
				"Garcia's Pawnshop - NOV",
				"TEST"
			],
			default: default_branch
		},
		{
		 	fieldname: "item_series",
		 	label: __("Series"),
		 	fieldtype: "Select",
			options: ["A", "B"],
			default: "A"
		},
		{
			fieldname: "workflow_state",
			label: __("work flow"),
			fieldtype: "Select",
			options: ["Active", "Expired"],
			default: "Expired"
	   	}
	]
}
}else{
frappe.query_reports["J End of Day Report"] = {
	"filters": [
		{
			fieldname: "item_series",
			label: __("Series"),
			fieldtype: "Select",
		   options: ["A", "B"],
		   default: "A"
	   },
	   {
		   fieldname: "workflow_state",
		   label: __("work flow"),
		   fieldtype: "Select",
		   options: ["Active", "Expired"],
		   default: "Expired"
		  }
	]
}

}
