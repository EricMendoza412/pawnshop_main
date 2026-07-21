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
		show_processing_progress(frm);
		if (!frm.is_new() && frm.doc.workflow_state === 'Sent') {
			frm.add_custom_button(__('View Batches'), () => {
				frappe.set_route('List', 'Text Blast Batch', { text_blast: frm.doc.name });
			}, __('Actions'));
			frm.add_custom_button(__('Retry Failed / Unsent SMS'), () => {
				frappe.call({
					method: 'pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.retry_text_blast',
					args: { text_blast_name: frm.doc.name },
					freeze: true,
					freeze_message: __('Queueing failed and unsent SMS recipients...'),
					callback(r) {
						const result = r.message || {};
						if (result.queued) {
							frappe.show_alert({
								message: __('Text Blast retry queued for {0} recipient(s).', [result.eligible]),
								indicator: 'green'
							});
						} else {
							frappe.msgprint({
								title: __('Nothing to Retry'),
								indicator: 'blue',
								message: __('No recipients are eligible. Successful: {0}; maximum attempts reached: {1}.', [result.successful || 0, result.exhausted || 0])
							});
						}
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

function show_processing_progress(frm) {
	if (frm.is_new() || frm.doc.workflow_state !== 'Sent') return;
	const progress = frm.doc.processing_progress || 0;
	frm.dashboard.add_progress(
		__('Text Blast Processing'),
		progress,
		__('Accepted: {0}; Failed: {1}; Unsent: {2}; Batches: {3}/{4}', [
			frm.doc.accepted_recipients || 0,
			frm.doc.failed_recipients || 0,
			frm.doc.unsent_recipients || 0,
			frm.doc.completed_batches || 0,
			frm.doc.total_batches || 0
		])
	);
	if (['Queued', 'Processing'].includes(frm.doc.processing_status)) {
		clearTimeout(frm.text_blast_refresh_timer);
		frm.text_blast_refresh_timer = setTimeout(() => frm.reload_doc(), 10000);
	}
}
