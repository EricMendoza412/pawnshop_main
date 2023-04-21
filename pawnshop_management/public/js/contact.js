frappe.ui.form.on("Contact", {
    refresh: function(frm) {
        let html = ``;
        frappe.call({
            method: "pawnshop_management.pawnshop_management.utils.get_contact_image",
            args: {
                contact: frm.doc.name,
            },
            callback: function(r) {
                if (r.message) {
                    $(frm.fields_dict['default_image'].wrapper).html(r.message);
                }
            }

        });
    }
});