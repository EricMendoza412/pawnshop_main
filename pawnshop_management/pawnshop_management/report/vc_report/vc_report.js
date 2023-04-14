// Copyright (c) 2023, Rabie Moses Santillan and contributors
// For license information, please see license.txt
/* eslint-disable */
var default_branch = [];

frappe.call({
    method: 'pawnshop_management.pawnshop_management.custom_codes.get_ip.get_ip',
    callback: function(data){
        let current_ip = data.message
        frappe.call({
            method: 'pawnshop_management.pawnshop_management.custom_codes.get_ip.get_ip_from_settings',
            callback: (result) => {
                let ip = result.message;
                if (current_ip == ip["cavite_city"]) {
                    default_branch.push("Garcia's Pawnshop - CC"); 
                } else if (current_ip == ip["poblacion"]) {
                    default_branch.push("Garcia\\'s Pawnshop - POB");
                } else if (current_ip == ip["molino"]) {
                    default_branch.push("Garcia\\'s Pawnshop - MOL");
                } else if (current_ip == ip["gtc"]) {
                    default_branch.push("Garcia\\'s Pawnshop - GTC");
                } else if (current_ip == ip["tanza"]) {
                    default_branch.push("Garcia\\'s Pawnshop - TNZ");
                }
            }
        })
    }
});


const date = new Date();
let day = date.getDate();
let month = date.getMonth() + 1;
let year = date.getFullYear();

// This arrangement can be altered based on how we want the date's format to appear.
let currentDate = `${year}-${month}-${day}`;

frappe.query_reports["VC Report"] = {
	"filters": [
		{
			fieldname: "change_status_date",
			label: __("Date"),
			fieldtype: "Date",
			default: currentDate
		}
        
	]
};
