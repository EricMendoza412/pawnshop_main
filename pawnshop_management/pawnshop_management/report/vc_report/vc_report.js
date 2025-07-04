// Copyright (c) 2023, Rabie Moses Santillan and contributors
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


const date = new Date();
let day = date.getDate();
let month = date.getMonth() + 1;
let year = date.getFullYear();

// This arrangement can be altered based on how we want the date's format to appear.
let currentDate = `${year}-${month}-${day}`;

let is_allowed = frappe.user_roles.includes('Auditor') || frappe.user_roles.includes('Administrator');
if(is_allowed){
    frappe.query_reports["VC Report"] = {
        "filters": [
            {
                fieldname: "change_status_date",
                label: __("Date"),
                fieldtype: "Date",
                default: currentDate
            },
            {
                fieldname: "branch",
                label: __("Branch"),
                fieldtype: "Select",
                options: [
                    "Garcia\\'s Pawnshop - CC", 
                    "Garcia\\'s Pawnshop - GTC", 
                    "Garcia\\'s Pawnshop - MOL",
                    "Garcia\\'s Pawnshop - POB",
                    "Garcia\\'s Pawnshop - TNZ",
                    "Garcia\\'s Pawnshop - ALP",
                    "Garcia\\'s Pawnshop - NOV",
                    "Garcia\\'s Pawnshop - PSC",
                    "TEST"
                ],
                default: default_branch
            }
            
        ]
    };
}else{
    frappe.query_reports["VC Report"] = {
        "filters": [
            {
                fieldname: "change_status_date",
                label: __("Date"),
                fieldtype: "Read Only",
                default: currentDate
            }
            
        ]
    };

}


