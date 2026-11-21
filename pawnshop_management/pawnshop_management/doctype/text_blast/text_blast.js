frappe.ui.form.on('Text Blast', {
	onload(frm) {
		const rows = frm.doc.recipient_list || [];
		// Frappe inserts a placeholder for required tables on new documents.
		if (frm.is_new() && rows.length === 1 && !rows[0].contact_name && !rows[0].mobile_number) {
			frm.clear_table('recipient_list');
			frm.refresh_field('recipient_list');
		}
	},

	refresh(frm) {
		load_branch_options(frm);
		update_message_length(frm);
		// Frappe's change event fires on blur; input gives immediate encoding feedback.
		if (frm.fields_dict.message.$input) {
			frm.fields_dict.message.$input.off('input.text_blast').on('input.text_blast', function () {
				update_message_length(frm, this.value);
			});
		}
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

	recipient_options: selection_changed,
	recipient_filter: selection_changed,
	from_date: selection_changed,
	to_date: selection_changed,
	preview_recipients(frm) {
		if (frm.doc.workflow_state !== 'Draft') return;
		const args = selection_args(frm);
		if (!args.branch || !args.recipient_filter || !args.from_date || !args.to_date) {
			frappe.msgprint(__('Select a registered branch, filter, From Date and To Date.'));
			return;
		}
		if (args.from_date > args.to_date) {
			frappe.msgprint(__('From Date must be on or before To Date.'));
			return;
		}
		const signature = JSON.stringify(args);
		frappe.call({
			method: 'pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.get_branch_recipients',
			args,
			freeze: true,
			freeze_message: __('Finding matching customers...'),
			callback(r) {
				if (r.exc || signature !== JSON.stringify(selection_args(frm))) return;
				const recipients = r.message || [];
				if (!recipients.length) {
					frappe.msgprint(__('No matching recipients with mobile numbers were found.'));
					return;
				}
				const total = sms_metrics(frm.doc.message).segments * recipients.length;
				frappe.confirm(__('Found {0} unique mobile recipients. Estimated total SMS segments: {1}. Replace the current recipient list with these recipients?', [recipients.length, total]), () => {
					if (frm.doc.workflow_state !== 'Draft' || signature !== JSON.stringify(selection_args(frm))) return;
					frm.clear_table('recipient_list');
					recipients.forEach(recipient => {
						Object.assign(frm.add_child('recipient_list'), recipient);
					});
					frm.refresh_field('recipient_list');
					frm.dirty();
					update_message_length(frm);
				});
			}
		});
	}
});

frappe.ui.form.on('Recipient List', {
	contact_name(frm) { update_message_length(frm); },
	recipient_list_add(frm) { update_message_length(frm); },
	recipient_list_remove(frm) { update_message_length(frm); }
});

// The form is reused across documents, but field metadata is document-specific.
// Cache the response on the form and reapply it to the active document on refresh.
function load_branch_options(frm) {
	const instructions = __('Choose a branch, filter and dates, then preview matching recipients. Manual selection is also available.');
	const retry_label = __('Retry Loading Branches');
	const show_status = message => {
		frm.set_df_property('recipient_options', 'description', message ? `${message} ${instructions}` : instructions);
	};
	const apply_options = () => {
		const selected = frm.doc.recipient_options;
		const branches = frm.text_blast_branch_options.slice();
		// Preserve saved selections even if a branch no longer appears in the response.
		if (selected && !branches.includes(selected)) branches.push(selected);
		frm.text_blast_applying_branch_options = true;
		try {
			frm.set_df_property('recipient_options', 'options', [''].concat(branches).join('\n'));
			frm.refresh_field('recipient_options');
		} finally {
			frm.text_blast_applying_branch_options = false;
		}
		show_status('');
		frm.remove_custom_button(retry_label);
	};
	if (frm.text_blast_branch_options) {
		apply_options();
		return;
	}
	show_status(__('Loading branches...'));
	if (frm.text_blast_branches_loading) return;
	frm.text_blast_branches_loading = true;
	frm.remove_custom_button(retry_label);
	const failed = () => {
		frm.text_blast_branches_loading = false;
		show_status(__('Unable to load branches. Use Retry Loading Branches to try again.'));
		frm.add_custom_button(retry_label, () => load_branch_options(frm));
	};
	frappe.call({
		method: 'pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.get_recipient_options',
		callback(r) {
			if (r.exc || !Array.isArray(r.message) || !r.message.length ||
				r.message.some(branch => typeof branch !== 'string' || !branch.trim())) {
				failed();
				return;
			}
			frm.text_blast_branches_loading = false;
			frm.text_blast_branch_options = [...new Set(r.message)];
			apply_options();
		},
		error: failed
	});
}

function selection_args(frm) {
	return {branch: frm.doc.recipient_options, recipient_filter: frm.doc.recipient_filter,
		from_date: frm.doc.from_date, to_date: frm.doc.to_date};
}

function selection_changed(frm) {
	if (frm.text_blast_applying_branch_options) return;
	if (frm.doc.workflow_state !== 'Draft') return;
	// A list loaded for previous criteria must not silently survive a criteria change.
	frm.clear_table('recipient_list');
	frm.refresh_field('recipient_list');
	update_message_length(frm);
}

function sms_metrics(message) {
	message = message || '';
	const basic = new Set("@\u00a3$\u00a5\u00e8\u00e9\u00f9\u00ec\u00f2\u00c7\n\u00d8\u00f8\r\u00c5\u00e5\u0394_\u03a6\u0393\u039b\u03a9\u03a0\u03a8\u03a3\u0398\u039e\u00c6\u00e6\u00df\u00c9 !\"#\u00a4%&'()*+,-./0123456789:;<=>?\u00a1ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c4\u00d6\u00d1\u00dc\u00a7\u00bfabcdefghijklmnopqrstuvwxyz\u00e4\u00f6\u00f1\u00fc\u00e0");
	const extended = new Set("\f^{}\\[~]|\u20ac");
	const characters = Array.from(message);
	const unsupported = [...new Set(characters.filter(c => !basic.has(c) && !extended.has(c)))];
	const unicode = unsupported.length > 0;
	const units = unicode ? message.length : characters.reduce((sum, c) => sum + (extended.has(c) ? 2 : 1), 0);
	const single = unicode ? 70 : 160;
	const multipart = unicode ? 67 : 153;
	const segments = units ? (units <= single ? 1 : Math.ceil(units / multipart)) : 0;
	return {encoding: unicode ? 'Unicode' : 'GSM', characters: characters.length, units, segments, unsupported};
}

function update_message_length(frm, input) {
	const metrics = sms_metrics(typeof input === 'string' ? input : frm.doc.message);
	const recipients = (frm.doc.recipient_list || []).filter(row => row.contact_name).length;
	const display = `Encoding: ${metrics.encoding} | Character count: ${metrics.units}\n${metrics.segments} (SMS Segments) x ${recipients} (Recipients) = ${metrics.segments * recipients} (Estimated total SMS Segments)`;
	if (frm.doc.workflow_state === 'Draft') frm.set_value('message_length', display);
	const warning = metrics.unsupported.length ? __('Unicode increases SMS charges. Remove or replace these characters: {0}. Unicode allows 70 units for one SMS, or 67 per multipart segment.', [metrics.unsupported.map(c => `${c} (U+${c.codePointAt(0).toString(16).toUpperCase()})`).join(', ')]) : '';
	frm.fields_dict.encoding_warning.$wrapper.empty();
	if (warning) $('<div class="alert alert-warning">').text(warning).appendTo(frm.fields_dict.encoding_warning.$wrapper);
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
