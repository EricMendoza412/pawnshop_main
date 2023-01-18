// Copyright (c) 2016, Rabie Moses Santillan and contributors
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
                    default_branch.push("Garcia's Pawnshop - POB");
                } else if (current_ip == ip["molino"]) {
                    default_branch.push("Garcia's Pawnshop - MOL");
                } else if (current_ip == ip["gtc"]) {
                    default_branch.push("Garcia's Pawnshop - GTC");
                } else if (current_ip == ip["tanza"]) {
                    default_branch.push("Garcia's Pawnshop - TNZ");
                }
            }
        })
    }
});

let is_allowed = frappe.user_roles.includes('Administrator','Auditor');
if(is_allowed){
    frappe.query_reports["NJ End of the Day Repor"] = {
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
                ],
                default: default_branch
                
            }

            // ,{
            // 	fieldname: "date_loan_granted",
            // 	label: __("Date Loan Granted"),
            // 	fieldtype: "Date"
            // }
        ]
    }
}else{
    frappe.query_reports["NJ End of the Day Repor"] = {
        "filters": [
            {
                fieldname: "branch",
                label: __("Branch"),
                fieldtype: "Data",
                default: default_branch
            }
        ]
    }

}
