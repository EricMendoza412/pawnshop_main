frappe.ui.form.on('Text Blast', {
	setup(frm) {
		frappe.call({
			method: 'pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.get_recipient_options',
			callback(r) {
				const options = (r.message || []).join('\n');
				frm.set_df_property('recipient_options', 'options', options);
				frm.refresh_field('recipient_options');
			}
		});
	},

	refresh(frm) {
		update_message_length(frm);
		if (!frm.is_new() && frm.doc.workflow_state === 'Sent') {
			frm.add_custom_button(__('Retry Failed SMS'), () => {
				frappe.call({
					method: 'pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.retry_text_blast',
					args: { text_blast_name: frm.doc.name },
					freeze: true,
					freeze_message: __('Queueing failed SMS recipients...'),
					callback() {
						frappe.show_alert({ message: __('Text Blast retry queued.'), indicator: 'green' });
					}
				});
			}, __('Actions'));
		}
	},

	message(frm) {
		update_message_length(frm);
	},

	recipient_options(frm) {
		if (!frm.doc.recipient_options) {
			frm.clear_table('recipient_list');
			frm.refresh_field('recipient_list');
			return;
		}

		frappe.call({
			method: 'pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.get_branch_recipients',
			args: { branch: frm.doc.recipient_options },
			freeze: true,
			freeze_message: __('Loading branch customers...'),
			callback(r) {
				frm.clear_table('recipient_list');
				(r.message || []).forEach(recipient => {
					const row = frm.add_child('recipient_list');
					row.contact_name = recipient.contact_name;
					row.mobile_number = recipient.mobile_number;
				});
				frm.refresh_field('recipient_list');
			}
		});
	}
});

function update_message_length(frm) {
	const characters = (frm.doc.message || '').length;
	const segments = Math.max(1, Math.ceil(characters / 160));
	const capacity = segments * 160;
	frm.set_value('message_length', __('Characters: {0} / {1}\nSMS Segments: {2}', [characters, capacity, segments]));
}
