// Copyright (c) 2022, Rabie Moses Santillan and contributors
// For license information, please see license.txt


var branch_name;

frappe.ui.form.on('Agreement to Sell', {
	refresh: function(frm) {

		let is_allowed = frappe.user_roles.includes('Administrator') || frappe.user_roles.includes('Support Team');
		frm.toggle_enable(['date_of_sale', 'branch'], is_allowed);
		set_appraiser_queries(frm);
		load_customer_id_pictures(frm);

	   if (frm.is_new()) {
		   frm.set_value('date_of_sale', frappe.datetime.nowdate())
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
		if (frm.doc.amended_from != null){
			var previous_pt = frm.doc.amended_from      //Naming for the next document created of amend
			const separator = previous_pt.split("-");
			
			if (separator.length == 2) {
				frm.set_value('form_number', frm.doc.amended_from + "-1");
				frm.refresh_field('form_number');
			} else {
				let new_Version = parseInt(separator[separator.length-1]);
				new_Version += 1;
				frm.set_value('form_number', separator[0] + "-" + separator[1] + "-" + new_Version);
				frm.refresh_field('pawn_ticket');
			}
		}

		},

	before_submit: function(frm) {
		if (flt(frm.doc.total_value) === 0) {
			frappe.throw(__('Total Value must not be zero'));
		}
	},

	branch: function(frm){
	   show_form_no(frm);
	   show_tracking_no(frm);
	   update_last_sb_dates(frm);

		//Filter of Jewelry items table
		frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch, 'jewelry_inventory_count')
		.then(r =>{
			let jewelry_inventory_count = r.message.jewelry_inventory_count
			frm.set_query('item_no', 'jewelry_items', function(){
				return {
					filters: {
						batch_number: String(jewelry_inventory_count),
						branch: frm.doc.branch
					}
				}
			})
		})

	},

	customer_tracker: function(frm){
		update_last_sb_dates(frm);
		load_customer_id_pictures(frm);
	},

	customer_id_picture: function(frm) {
		show_selected_customer_id_picture(frm);
	},

	assistant_appraiser_acct: function(frm){
		if (frm.doc.assistant_appraiser_acct == frm.doc.main_appraiser_acct) {
			frappe.msgprint({
				title: __('Error'),
				indicator: 'red',
				message: __('Assistant Appraiser cannot be the same as Main Appraiser')
			});
			frm.set_value('assistant_appraiser_acct', null);
			frm.refresh_field('assistant_appraiser_acct');
			frm.set_value('assistant_appraiser', null);
			frm.refresh_field('assistant_appraiser');
		}
	}

});

function set_appraiser_queries(frm) {
	const appraiser_roles = [
		"Appraiser",
		"Senior Appraiser",
		"Junior Appraiser",
		"Cashier",
		"Operations Supervisor",
		"Appraiser/Cashier",
		"Vault Custodian",
		"Operations Manager",
		"Area Manager"
	];

	frm.set_query('assistant_appraiser_acct', function() {
		return {
			"filters": {
				"role_profile_name": ["in", appraiser_roles]
			}
		};
	});

	frm.set_query('main_appraiser_acct', function() {
		return {
			"filters": {
				"role_profile_name": ["in", appraiser_roles]
			}
		};
	});
}

async function update_last_sb_dates(frm) {
	try {
		const customer = frm.doc.customer_tracker;
		if (!customer) {
			frm.set_value('last_sb_date_in_gp', null);
			frm.set_value('last_sb_date_in_branch', null);
			return;
		}

		const getLastSBDate = (filters) =>
			frappe.db.get_list('Agreement to Sell', {
				fields: ['date_of_sale'],
				filters,
				order_by: 'date_of_sale desc',
				limit: 1
			}).then(res => (res?.length ? res[0].date_of_sale : null));

		const baseFilters = {
			customer_tracker: customer,
			workflow_state: ['!=', 'Rejected'],
			docstatus: ['!=', 2]
		};

		if (!frm.is_new() && frm.doc.name) {
			baseFilters.name = ['!=', frm.doc.name];
		}

		const branchFilters = frm.doc.branch
			? { ...baseFilters, branch: frm.doc.branch }
			: null;

		const [lastSBGeneral, lastSBBranch] = await Promise.all([
			getLastSBDate(baseFilters),
			branchFilters ? getLastSBDate(branchFilters) : Promise.resolve(null)
		]);

		frm.set_value('last_sb_date_in_gp', lastSBGeneral);
		frm.set_value('last_sb_date_in_branch', branchFilters ? lastSBBranch : null);
	} catch (error) {
		console.error('Unable to fetch latest Agreement to Sell dates', error);
	}
}

function load_customer_id_pictures(frm) {
	if (!frm.doc.customer_tracker) {
		frm._customer_id_picture_options = [];
		frm.set_df_property('customer_id_picture', 'options', []);
		frm.doc.customer_id_picture = null;
		frm.refresh_field('customer_id_picture');
		frm._all_customer_ids_expired = false;
		$(frm.fields_dict['default_image'].wrapper).html('');
		return;
	}

	frappe.call({
		method: "pawnshop_management.pawnshop_management.utils.get_contact_id_pictures_by_customer",
		args: {
			customer: frm.doc.customer_tracker,
		},
		callback: function(r) {
			const data = r.message || {};
			const options = data.options || [];
			frm._customer_id_picture_options = options;
			frm._all_customer_ids_expired = Boolean(data.all_customer_ids_expired);

			frm.set_df_property(
				'customer_id_picture',
				'options',
				options.map(option => option.label).join('\n')
			);

			frm.toggle_display('customer_id_picture', options.length > 1);

			if (data.selected) {
				const selected_option = options.find(option => option.value === data.selected);
				frm.doc.customer_id_picture = selected_option ? selected_option.label : null;
				frm.refresh_field('customer_id_picture');
			}

			if (data.html) {
				const selected_option = options.find(option => option.label === frm.doc.customer_id_picture);
				render_customer_id_picture(frm, data.html, selected_option);
			}
		}
	});
}

function show_selected_customer_id_picture(frm) {
	const selected = frm.doc.customer_id_picture;
	const options = frm._customer_id_picture_options || [];
	const selected_option = options.find(option => option.label === selected);

	if (!selected_option) {
		return;
	}

	if (selected_option.id_pic_name) {
		const image_url = get_customer_id_picture_url(selected_option.id_pic_name);
		const fallback_image_url = get_customer_id_picture_fallback_url(selected_option.id_pic_name);
		render_customer_id_picture(
			frm,
			`<img src="${escape_html(image_url)}" data-fallback-src="${escape_html(fallback_image_url)}" onerror="handle_customer_id_picture_error(this)" style="max-width: 400px; height: auto;">`,
			selected_option
		);
		return;
	}

	render_customer_id_picture(
		frm,
		`<div class="alert alert-warning">${__('No ID picture set for selected ID')}</div>`,
		selected_option
	);
}

function render_customer_id_picture(frm, image_html, selected_option) {
	const indicator = get_customer_id_expiry_indicator(frm, selected_option);
	$(frm.fields_dict['default_image'].wrapper).html(`${image_html}${indicator}`);
	make_customer_id_picture_zoomable(frm);
}

function get_customer_id_expiry_indicator(frm, selected_option) {
	let message = null;

	if (frm._all_customer_ids_expired) {
		message = __('All customer IDs have expired');
	} else if (selected_option && selected_option.is_expired) {
		message = __('Selected customer ID has expired');
	}

	if (!message) {
		return '';
	}

	return `<div style="color: #b42318; font-weight: 700; font-size: 14px; margin-top: 8px;">${message}</div>`;
}

function make_customer_id_picture_zoomable(frm) {
	const $wrapper = $(frm.fields_dict['default_image'].wrapper);
	const $image = $wrapper.find('img');

	if (!$image.length) {
		return;
	}

	$image
		.css('cursor', 'zoom-in')
		.attr('title', __('Click to zoom'))
		.off('click.customer_id_zoom')
		.on('click.customer_id_zoom', function() {
			const image_url = $(this).attr('src');
			const dialog = new frappe.ui.Dialog({
				title: __('Customer ID Picture'),
				size: 'large'
			});

			dialog.$body.html(
				`<div style="text-align: center;">
					<img src="${escape_html(image_url)}" style="max-width: 100%; max-height: 75vh; height: auto;">
				</div>`
			);
			dialog.show();
		});
}

function escape_html(value) {
	return $('<div>').text(value || '').html();
}

function get_customer_id_picture_url(id_pic_name) {
	return `https://firebasestorage.googleapis.com/v0/b/gpcustomersids.appspot.com/o/customerPictures%2F${encodeURIComponent(id_pic_name)}.jpg?alt=media`;
}

function get_customer_id_picture_fallback_url(id_pic_name) {
	return `https://storage.cloud.google.com/gpcustomersids.appspot.com/customerPictures/${encodeURIComponent(id_pic_name)}.jpg`;
}

function handle_customer_id_picture_error(image) {
	if (image.dataset.fallbackSrc && image.src !== image.dataset.fallbackSrc) {
		image.src = image.dataset.fallbackSrc;
		image.removeAttribute('data-fallback-src');
	}
}

function show_tracking_no(frm){ //Sets inventory tracking number
	let branch_code = 0;

	if (frm.doc.branch == "Garcia's Pawnshop - CC") {
		branch_code = 1;
		branch_name = "CC";
	}else if(frm.doc.branch == "Garcia's Pawnshop - POB") {
		branch_code = 3;
		branch_name = "POB";
	}else if(frm.doc.branch == "Garcia's Pawnshop - GTC") {
		branch_code = 4;
		branch_name = "GTC";
	}else if(frm.doc.branch == "Garcia's Pawnshop - TNZ") {
		branch_code = 5;
		branch_name = "TNZ";
	}else if(frm.doc.branch == "Garcia's Pawnshop - MOL") {
		branch_code = 6;
		branch_name = "MOL";
	}else if(frm.doc.branch == "Garcia's Pawnshop - BUC") {
		branch_code = 7;
		branch_name = "BUC";
	}else if(frm.doc.branch == "Garcia's Pawnshop - NOV") {
		branch_code = 8;
		branch_name = "NOV";
	}else if(frm.doc.branch == "Garcia's Pawnshop - PSC") {
		branch_code = 9;
		branch_name = "PSC";
	}else if(frm.doc.branch == "TEST") {
		branch_code = 20;
		branch_name = "TEST";
	}

	if (frm.doc.amended_from == null) {
	let jewelry_inv_count;
	frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['jewelry_inventory_count'])
	.then(value => {
		let tracking_no = value.message;
		jewelry_inv_count = parseInt(tracking_no.jewelry_inventory_count);
		frm.set_value('ats_tracking_no', 'ATS-'+branch_code+"-"+ jewelry_inv_count + 'J');
	})
	}
}


function show_form_no(frm) { 
   if (frm.doc.amended_from == null) {
	let jewelryinv_count;
		frappe.db.get_value('Pawnshop Naming Series', frm.doc.branch,['ats_jewelry_count'])
		.then(value => {
			let tracking_no = value.message;
			jewelryinv_count = parseInt(tracking_no.ats_jewelry_count);
			frm.set_value('form_number', branch_name+"-"+jewelryinv_count );
		})
	} 
}

function set_total_appraised_amount(frm) { // Calculate Total Amount
	let temp_principal = 0.00;
	$.each(frm.doc.jewelry_items, function(index, item){
		temp_principal += parseFloat(item.suggested_appraisal_value);
	});
	frm.set_value('total_value', temp_principal)
	frm.refresh_field('total_value')
	return temp_principal
}


frappe.ui.form.on('Jewelry List', {

	item_no: function(frm){
		if (frm.doctype !== 'Agreement to Sell') {
			return;
		}

		let table_length = parseInt(frm.doc.jewelry_items.length)
		if (frm.doc.jewelry_items.length > 1) {
			for (let index = 0; index < table_length - 1; index++) {
				if (frm.doc.jewelry_items[table_length-1].item_no == frm.doc.jewelry_items[index].item_no) {
					frm.doc.jewelry_items.pop(table_length-1);
					frm.refresh_field('jewelry_items');
					frappe.msgprint({
						title:__('Notification'),
						indicator:'red',
						message: __('Added item is already in the list. Item removed.')
					});
					set_total_appraised_amount(frm)
				}
			}
		}
	},
	suggested_appraisal_value: function(frm){
		if (frm.doctype !== 'Agreement to Sell') {
			return;
		}

		set_total_appraised_amount(frm);
	},
	jewelry_items_remove: function(frm){ //calculate appraisal value when removing items
		if (frm.doctype !== 'Agreement to Sell') {
			return;
		}

		let table_length = parseInt(frm.doc.jewelry_items.length)
		set_total_appraised_amount(frm);
		if (table_length <= 4) {
			frm.fields_dict["jewelry_items"].grid.grid_buttons.find(".grid-add-row")[0].style.visibility = "visible";
		}
	}
	}	
)
