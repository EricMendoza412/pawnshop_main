// Copyright (c) 2024, Rabie Moses Santillan and contributors
// For license information, please see license.txt

const JEWELRY_TYPE_FIELD_MAP = Object.freeze({
	Earrings: 'earrings_count',
	Bracelet: 'bracelet_count',
	Necklace: 'necklace_count',
	Ring: 'ring_count',
	Bangles: 'bangles_count',
	Pendant: 'pendant_count',
	Set: 'set_count',
	Earcuff: 'earcuff_count',
	'Gold Coin': 'gold_coin_count'
});

const getEmptyJewelryCounts = () => {
	const counts = {};
	Object.values(JEWELRY_TYPE_FIELD_MAP).forEach(fieldname => {
		counts[fieldname] = 0;
	});
	return counts;
};

const toNumberSafe = value => {
	const num = parseFloat(value);
	return Number.isFinite(num) ? num : 0;
};

const DISPLAY_TRANSFER_TYPES = Object.freeze([
	'Transfer of Display Items',
	'Issue as company used item'
]);

const BASE_TRANSFER_TYPE_OPTIONS = Object.freeze([
	'',
	'Pull out of Expired Sangla',
	'Transfer of Display Items'
]);

const COMPANY_USED_TRANSFER_TYPE = 'Issue as company used item';

const isDisplayTransferType = transferType => DISPLAY_TRANSFER_TYPES.includes(transferType);
const PULLOUT_TRANSFER_TYPE = 'Pull out of Expired Sangla';

const syncTransferTypeOptions = frm => {
	if (!frm) return;

	const options = [...BASE_TRANSFER_TYPE_OPTIONS];
	const canSeeCompanyUsedOption =
		frappe.user.has_role('Subastado member NJ') ||
		frm.doc.docstatus === 1 ||
		frm.doc.transfer_type === COMPANY_USED_TRANSFER_TYPE;

	if (canSeeCompanyUsedOption) {
		options.push(COMPANY_USED_TRANSFER_TYPE);
	}

	frm.set_df_property('transfer_type', 'options', options.join('\n'));

	if (
		frm.doc.transfer_type === COMPANY_USED_TRANSFER_TYPE &&
		!frappe.user.has_role('Subastado member NJ') &&
		frm.doc.docstatus !== 1
	) {
		frm.set_value('transfer_type', '');
	}

	frm.refresh_field('transfer_type');
};

const isPulloutTransferType = transferType => transferType === PULLOUT_TRANSFER_TYPE;

const syncPulloutDateFieldState = frm => {
	if (!frm) return;

	const isEditable = isPulloutTransferType(frm.doc.transfer_type);
	frm.set_df_property('from_date', 'read_only', !isEditable);
	frm.set_df_property('to_date', 'read_only', !isEditable);
	frm.refresh_field('from_date');
	frm.refresh_field('to_date');
};

const recalculateJewelryTransferTotals = frm => {
	if (!frm || !frm.doc) return;

	const totalJewelryPrincipal = (frm.doc.j_items || []).reduce(
		(sum, child) => sum + toNumberSafe(child.principal),
		0
	);
	const totalJewelryPrice = (frm.doc.j_items || []).reduce(
		(sum, child) => sum + toNumberSafe(child.selling_price),
		0
	);

	if (isDisplayTransferType(frm.doc.transfer_type)) {
		frm.set_value('total_price', totalJewelryPrice);
	} else if (isPulloutTransferType(frm.doc.transfer_type)) {
		frm.set_value('total_cost', totalJewelryPrincipal);
	}
};

const setJItemsFromRows = (frm, rows) => {
	frm.clear_table('j_items');

	(rows || []).forEach(row => {
		const child = frm.add_child('j_items');
		child.last_pawn_ticket = row.last_pawn_ticket || '';
		child.item_no = row.item_no || '';
		child.type = row.type || '';
		child.weight = row.weight || 0;
		child.karat = row.karat || '';
		child.color = row.color || '';
		child.densi = row.densi || '';
		child.principal = toNumberSafe(row.principal);
		child.selling_price = toNumberSafe(row.selling_price);
		child.date_loan_granted = row.date_loan_granted || '';
	});

	frm.refresh_field('j_items');
	updateJewelryCounts(frm);
	recalculateJewelryTransferTotals(frm);
	updatePawnTicketEnvelopeCounts(frm);
};

const populatePulloutJewelryItemsByDateRange = async frm => {
	if (!frm || !frm.doc) return;
	if (!isPulloutTransferType(frm.doc.transfer_type) || frm.doc.item_type !== 'Jewelry Items') return;

	const { origin, from_date: fromDate, to_date: toDate } = frm.doc;
	if (!fromDate || !toDate) return;

	if (fromDate > toDate) {
		frappe.msgprint(__('From Date cannot be later than To Date.'));
		return;
	}

	try {
		const { message } = await frappe.call({
			method: 'pawnshop_management.pawnshop_management.doctype.transfer_tracker.transfer_tracker.get_jewelry_pullout_items',
			args: {
				origin,
				from_date: fromDate,
				to_date: toDate
			}
		});

		const rows = message || [];
		setJItemsFromRows(frm, rows);
		if (!rows.length) {
			frappe.msgprint(__('No jewelry items found from {0} to {1}.', [fromDate, toDate]));
		}
	} catch (error) {
		console.warn('Unable to populate jewelry items from date range', error);
	}
};

const updateJewelryCounts = frm => {
	//update total_count as well as individual counts based on j_items table
	if (!frm || !frm.doc) return;

	const counts = getEmptyJewelryCounts();

	const rowsToCount =
		frm.doc.item_type === 'SB Jewelry Items'
			? (frm.doc.sb_items || [])
			: frm.doc.item_type === 'Jewelry Items'
				? (frm.doc.j_items || [])
				: [];

	rowsToCount.forEach(row => {
		const type = (row.type || '').trim();
		const fieldname = JEWELRY_TYPE_FIELD_MAP[type];
		if (fieldname) {
			counts[fieldname] += 1;
		}
	});

	Object.entries(counts).forEach(([fieldname, value]) => {
		const currentValue = Number(frm.doc[fieldname] || 0);
		if (currentValue !== value) {
			frm.set_value(fieldname, value);
		}
	});
	
	const totalCount = Object.values(counts).reduce((sum, value) => sum + value, 0);
	if (Number(frm.doc.total_items || 0) !== totalCount) {
		frm.set_value('total_items', totalCount);
	}
};

const setJItemItemNoEditable = frm => {
	if (!frm || !frm.doc) return;

	const jItemsField = frm.get_field('j_items');
	if (!jItemsField || !jItemsField.grid) return;

	const makeEditable = isDisplayTransferType(frm.doc.transfer_type);
	jItemsField.grid.update_docfield_property('item_no', 'read_only', !makeEditable);
	jItemsField.grid.update_docfield_property('last_pawn_ticket', 'read_only', makeEditable);
	jItemsField.grid.refresh();
};

const updatePawnTicketEnvelopeCounts = async frm => {
	// count unique pawn tickets by series (A/B) and update envelope totals
	if (!frm || !frm.doc) return;

	const extractTickets = rows =>
		(rows || [])
			.map(row => (row.last_pawn_ticket || '').trim())
			.filter(ticket => ticket && ticket.toLowerCase() !== 'unnecessary');

	const fetchTicketSeries = async (doctype, tickets) => {
		if (!tickets.length) return new Map();
		const rows = await frappe.db.get_list(doctype, {
			fields: ['name', 'item_series'],
			filters: { name: ['in', tickets] },
			limit: tickets.length
		});
		const map = new Map();
		rows.forEach(row => {
			const ticket = (row.name || '').trim();
			if (!ticket) return;
			map.set(ticket, (row.item_series || '').trim().toUpperCase());
		});
		return map;
	};

	const uniqueTickets = Array.from(
		new Set(
			[
				...extractTickets(frm.doc.j_items),
				...extractTickets(frm.doc.nj_items) // include last pawn tickets from nj_items as well
			]
		)
	);

	if (!uniqueTickets.length) {
		const resetValues = {};
		if (Number(frm.doc.pawn_ticket_a_cb || 0) !== 0) resetValues.pawn_ticket_a_cb = 0;
		if (Number(frm.doc.pawn_ticket_b_ncb || 0) !== 0) resetValues.pawn_ticket_b_ncb = 0;
		if (Number(frm.doc.total_envelopes || 0) !== 0) resetValues.total_envelopes = 0;
		if (Object.keys(resetValues).length) {
			frm.set_value(resetValues);
		}
		return;
	}

	try {
		const pjSeries = await fetchTicketSeries('Pawn Ticket Jewelry', uniqueTickets);
		const ptnjSeries = await fetchTicketSeries('Pawn Ticket Non Jewelry', uniqueTickets);

		const seriesByTicket = new Map();
		uniqueTickets.forEach(ticket => {
			// prioritize Jewelry entry, fallback to Non Jewelry
			if (pjSeries.has(ticket)) {
				seriesByTicket.set(ticket, pjSeries.get(ticket));
			} else if (ptnjSeries.has(ticket)) {
				seriesByTicket.set(ticket, ptnjSeries.get(ticket));
			}
		});

		let countA = 0;
		let countB = 0;
		seriesByTicket.forEach(series => {
			if (series === 'A') countA += 1;
			else if (series === 'B') countB += 1;
		});

		const total = countA + countB;
		const updates = {};
		if (Number(frm.doc.pawn_ticket_a_cb || 0) !== countA) updates.pawn_ticket_a_cb = countA;
		if (Number(frm.doc.pawn_ticket_b_ncb || 0) !== countB) updates.pawn_ticket_b_ncb = countB;
		if (Number(frm.doc.total_envelopes || 0) !== total) updates.total_envelopes = total;

		if (Object.keys(updates).length) {
			frm.set_value(updates);
		}
	} catch (error) {
		console.warn('Unable to fetch pawn ticket series', error);
		return;
	}
};

frappe.ui.form.on('Transfer Tracker', {
	refresh(frm) {

		syncTransferTypeOptions(frm);
		syncPulloutDateFieldState(frm);

		updateJewelryCounts(frm);
		updatePawnTicketEnvelopeCounts(frm);

		//if transfer type is Pull out of Expired Sangla, hide selling_price column in nj_items table
		if (frm.doc.transfer_type == "Pull out of Expired Sangla") {
			frm.get_field('nj_items').grid.set_column_disp('selling_price', false);
			frm.get_field('j_items').grid.set_column_disp('selling_price', false);
			frm.refresh_field('nj_items');
			frm.refresh_field('j_items');
			frm.set_df_property('total_price', 'hidden', 1);
			frm.refresh_field('total_price');
		}else if (isDisplayTransferType(frm.doc.transfer_type)) {
			frm.get_field('nj_items').grid.set_column_disp('selling_price', true);
			frm.get_field('j_items').grid.set_column_disp('selling_price', true);
			frm.refresh_field('nj_items');
			frm.refresh_field('j_items');
			frm.set_df_property('total_cost', 'hidden', 1);
			frm.refresh_field('total_cost');
		}

		setJItemItemNoEditable(frm);
	},

	onload: function(frm) {
		syncTransferTypeOptions(frm);
		syncPulloutDateFieldState(frm);

		if (frappe.session.user == "Administrator"){
			frm.set_df_property('origin', 'read_only', 0);
			frm.refresh_field('origin');
		}
		// set value of date_of_transfer to current date
		//check if form is new
		if (frm.is_new()) {
		frm.set_value('date_of_transfer', frappe.datetime.nowdate());
		frm.set_df_property('transfer_type', 'read_only', 1);

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

						//if user is a Subastado member and not Administrator, set origin to Subastado NJ
						if (frappe.user.has_role("Subastado member NJ") && frappe.session.user != "Administrator") {	
							frm.set_value('origin', 'Subastado NJ');
						}else if (frappe.user.has_role("Subastado member J") && frappe.session.user != "Administrator"){
							frm.set_value('origin', 'Subastado J');
						}else if (frappe.user.has_role("Chief Executive Officer") && frappe.session.user != "Administrator"){
							frm.set_value('origin', 'Garcia\'s Pawnshop - Head Office');
						}else {
							frm.set_value('origin', records[0].name);
						}
						
						frm.refresh_field('origin');

					})
				}
			})

		// // If user has role Subastado member, Transfer Type should be Transfer of Display Items and should be read only
		// if ((frappe.user.has_role("Subastado member J") || frappe.user.has_role("Subastado member NJ")) && frappe.session.user != "Administrator") {
		// 	frm.set_value('transfer_type', 'Transfer of Display Items');
		// 	frm.set_df_property('transfer_type', 'read_only', 1);
		// 	frm.refresh_field('transfer_type');
		// }	
		

		//Put name of current user in the field released_by
		frm.set_value('released_by', frappe.session.user);
		frm.refresh_field('released_by');
		//Disable save button until witnessed_by and rover is filled out
		frm.disable_save();
		//Hide nj_items table until transfer_type is filled out
		frm.set_df_property('nj_items', 'hidden', 1);
		frm.refresh_field('nj_items');
		//Hide j_items table until transfer_type is filled out
		frm.set_df_property('j_items', 'hidden', 1);
		frm.refresh_field('j_items');
		//Hide sb_items table until transfer_type is filled out
		frm.set_df_property('sb_items', 'hidden', 1);
		frm.refresh_field('sb_items');
		}
		
	},

	item_type: function(frm){

		if(frm.doc.item_type != ""){
			frm.set_df_property('transfer_type', 'read_only', 0);
			frm.refresh_field('transfer_type');
			frm.set_df_property('item_type', 'read_only', 1);
		
			if(frm.doc.item_type == "Non Jewelry Items"){
			// make nj items table appear
			frm.set_df_property('nj_items', 'hidden', 0);
			frm.refresh_field('nj_items');
			}else {
				if(frm.doc.item_type == "Jewelry Items"){
					// make j items table appear
					frm.set_df_property('j_items', 'hidden', 0);
					frm.refresh_field('j_items');
				}else if(frm.doc.item_type == "SB Jewelry Items"){
					// make sb items table appear
					frm.set_df_property('sb_items', 'hidden', 0);
					frm.refresh_field('sb_items');
					// Make Destination "Subastado J" and read only
					frm.set_value('destination', 'Subastado J');
					frm.set_df_property('destination', 'read_only', 1);
					frm.refresh_field('destination');
					// Make Transfer Type "Pull out of Expired Sangla" and read only
					frm.set_value('transfer_type', 'Pull out of Expired Sangla');
					frm.set_df_property('transfer_type', 'read_only', 1);
					frm.refresh_field('transfer_type');
				}

			// make all fields under Jewelry Item Counts not hidden
			frm.set_df_property('earrings_count', 'hidden', 0);
			frm.refresh_field('earrings_count');
			frm.set_df_property('bracelet_count', 'hidden', 0);
			frm.refresh_field('bracelet_count');
			frm.set_df_property('necklace_count', 'hidden', 0);
			frm.refresh_field('necklace_count');
			frm.set_df_property('ring_count', 'hidden', 0);
			frm.refresh_field('ring_count');
			frm.set_df_property('bangles_count', 'hidden', 0);
			frm.refresh_field('bangles_count');
			frm.set_df_property('pendant_count', 'hidden', 0);
			frm.refresh_field('pendant_count');
			frm.set_df_property('set_count', 'hidden', 0);
			frm.refresh_field('set_count');
			frm.set_df_property('earcuff_count', 'hidden', 0);
			frm.refresh_field('earcuff_count');
			frm.set_df_property('gold_coin_count', 'hidden', 0);
			frm.refresh_field('gold_coin_count');
			frm.set_df_property('total_items', 'hidden', 0);
			frm.refresh_field('total_items');
			}

			updateJewelryCounts(frm);
			syncPulloutDateFieldState(frm);
		
		}



	},

	origin: function(frm) {

		frappe.db.get_value("Pawnshop Naming Series", frm.doc.origin, "nj_transfer_form")
		.then(r => {
			let current_form = r.message.nj_transfer_form;
			frappe.db.get_value("Branch IP Addressing", frm.doc.origin, "branch_code")
				.then(r => {
					let branchCode = r.message.branch_code;
					if (frappe.user.has_role("Subastado member NJ") && frappe.session.user != "Administrator") {
						current_form = "SCG-"+ current_form	
						frm.set_value('item_type', 'Non Jewelry Items');
					}else if (frappe.user.has_role("Subastado member J") && frappe.session.user != "Administrator"){
						current_form = "SCJ-"+ current_form
						frm.set_value('item_type', 'Jewelry Items');
					}else {
						current_form = branchCode + "-"+ current_form	
					}
						frm.set_value('transfer_no', current_form );
						frm.refresh_field('transfer_no');
				})
		})
	},

	witnessed_by: function(frm){
		const userId = frm.doc.witnessed_by;
		if (!userId || frm._witnessPromptOpen) return;

		frm._witnessPromptOpen = true;

		let promptSubmitted = false;
		const dialog = frappe.prompt({
			label: 'Password',
			fieldname: 'password',
			fieldtype: 'Password'
		}, (password) => {
			promptSubmitted = true;
			frappe.call({
				method: 'pawnshop_management.pawnshop_management.custom_codes.passwords.check_password',
				args: {
					user: String(frm.doc.witnessed_by),
					pwd: password.password
				},
				callback: function(usr){
					if (frm.doc.witnessed_by == usr.message) {
						frappe.msgprint({
							title: __('Approved!'),
							indicator: 'green',
							message: __('Witness Approved')
						});
						//check if both witnessed_by and rover is filled out before enabling save
						if (frm.doc.rover != null) {
							frm.enable_save();
						}

					} else {
						frm.set_value('witnessed_by', null);
						frm.refresh_field('witnessed_by');
						frappe.msgprint({
							title: __('Password Invalid'),
							indicator: 'red',
							message: __(usr.message)
						});
					}
				}
			})
		});

		dialog.$wrapper.on('hidden.bs.modal', () => {
			if (!promptSubmitted) {
				frm.set_value('witnessed_by', null);
				frm.refresh_field('witnessed_by');
			}
			frm._witnessPromptOpen = false;
		});
	},
	rover: function(frm){
		const userId = frm.doc.rover;
		if (!userId || frm._roverPromptOpen) return;

		frm._roverPromptOpen = true;

		let promptSubmitted = false;
		const dialog = frappe.prompt({
			label: 'Password',
			fieldname: 'password',
			fieldtype: 'Password'
		}, (password) => {
			promptSubmitted = true;
			frappe.call({
				method: 'pawnshop_management.pawnshop_management.custom_codes.passwords.check_password',
				args: {
					user: String(frm.doc.rover),
					pwd: password.password
				},
				callback: function(usr){
					if (frm.doc.rover == usr.message) {
						frappe.msgprint({
							title: __('Approved!'),
							indicator: 'green',
							message: __('Rover Approved')
						});
						//check if both witnessed_by and rover is filled out before enabling save
						if (frm.doc.witnessed_by != null) {
							frm.enable_save();
						}
					} else {
						frm.set_value('rover', null);
						frm.refresh_field('rover');
						frappe.msgprint({
							title: __('Password Invalid'),
							indicator: 'red',
							message: __(usr.message)
						});
					}
				}
			})
		})
		dialog.$wrapper.on('hidden.bs.modal', () => {
			if (!promptSubmitted) {
				frm.set_value('rover', null);
				frm.refresh_field('rover');
			}
			frm._roverPromptOpen = false;
		});
	},

	destination: function(frm){
		if (frm.doc.destination == "Accounting Office"){ 
			frm.set_df_property('person_responsible', 'read_only', 0);
		} else {
			frm.set_df_property('person_responsible', 'read_only', 1);
			frm.set_value('person_responsible', '');
		}
	
	},

	transfer_type: function(frm){
			//once transfer_type is selected, make it read only
			frm.set_df_property('transfer_type', 'read_only', 1);
			frm.refresh_field('transfer_type');
			syncPulloutDateFieldState(frm);

				if (frm.doc.transfer_type == "Pull out of Expired Sangla") {
						//Set Destination to Subastado NJ and make it read only
						let destinationReadOnly = 1;
						
						if(frm.doc.item_type == "Non Jewelry Items"){
							if (frappe.user.has_role("Subastado member NJ") || frappe.user.has_role("Subastado member")) {
							// Keep destination editable for Subastado users.
							destinationReadOnly = 0;
							}else {
							frm.set_value('destination', 'Subastado NJ');
							}
						//Set filter for NJ items table based on the origin except if user is a Subastado member
						frm.set_query('item_no', 'nj_items', function(){
							return {
								filters: {
									workflow_State: 'Collected',
									branch: frm.doc.origin
								}
							}
						})
					}else if(frm.doc.item_type == "Jewelry Items"){
						frm.set_value('destination', 'Subastado J');
						//Set filter for J items table based on the origin except if user is a Subastado member
						frm.set_query('last_pawn_ticket', 'j_items', function(){
							return {
								filters: {
									workflow_State: ['in',['Active', 'Expired']],
									branch: frm.doc.origin
								}
							}
						})
					}

						frm.set_df_property('destination', 'read_only', destinationReadOnly);
						frm.refresh_field('destination');

							
			}else if (isDisplayTransferType(frm.doc.transfer_type)) {
					frm.set_value('destination', '');
					frm.set_df_property('destination', 'read_only', 0);
					frm.refresh_field('destination');

					if(frm.doc.item_type == "Non Jewelry Items"){
						//Set filter for NJ items table based on the origin except if user is a Subastado member
						frm.set_query('item_no', 'nj_items', function(){
							return {
								filters: {
									workflow_State: 'For Sale',
									current_location: frm.doc.origin
								}
							}
						})
					} else if(frm.doc.item_type == "Jewelry Items"){
						//Set filter for J items table based on the origin except if user is a Subastado member
						frm.set_query('item_no', 'j_items', function(){
							return {
								filters: {
									workflow_State: 'For Sale',
									current_location: frm.doc.origin
								}
							}
						})

						//Hide last pawn ticket
						frm.get_field('j_items').grid.set_column_disp('last_pawn_ticket', false);
						frm.refresh_field('j_items');
					
					}

			}

			setJItemItemNoEditable(frm);
			if (isPulloutTransferType(frm.doc.transfer_type) && frm.doc.item_type === 'Jewelry Items') {
				populatePulloutJewelryItemsByDateRange(frm);
			}
		
	},

	from_date(frm) {
		populatePulloutJewelryItemsByDateRange(frm);
	},

	to_date(frm) {
		populatePulloutJewelryItemsByDateRange(frm);
	},

	j_items_add(frm) {
		updateJewelryCounts(frm);
		updatePawnTicketEnvelopeCounts(frm);
	},

	j_items_remove(frm) {
		updateJewelryCounts(frm);
		updatePawnTicketEnvelopeCounts(frm);
	}

	});

	frappe.ui.form.on('Transfer Items', {
	//do something when an item is added to the nj_items table
		nj_items_add: function(frm, cdt, cdn) {
			let row = locals[cdt][cdn];
			//Nothing to do here yet
		},

		item_no: async function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		//Check if the item_no already exists in the table
		let exists = false;
		frm.doc.nj_items.forEach(function(item) {
			if(item.item_no == row.item_no && item.name != row.name) {
				exists = true;
			}
		});
		if(exists) {
			frappe.msgprint('Item already exists in the table');
			//delete the row
			frm.get_field('nj_items').grid.grid_rows_by_docname[row.name].remove();
			frm.refresh_field('nj_items');
			return;
		}

		//get total pt_principal from all item_no in the table and set it to total_cost
		if(frm.doc.transfer_type == "Pull out of Expired Sangla"){
			//There is no pt_principal yet, get it from the most recent Pawn Ticket Non Jewelry of the NJ item
			// 1) Get parent names from child rows
			const childRows = await frappe.db.get_list('Non Jewelry List', {
			fields: ['parent'],
			filters: { item_no: row.item_no, parenttype: 'Pawn Ticket Non Jewelry' },
			limit: 500
			});
			const parents = childRows.map(r => r.parent);

			// 2) Get the latest PTNJ by expiry_date with workflow status expired
			let latest = null;
			if (parents.length) {
			const ptnj = await frappe.db.get_list('Pawn Ticket Non Jewelry', {
				fields: ['name', 'expiry_date', 'desired_principal'],
				filters: { name: ['in', parents], workflow_state: ['!=', 'Rejected'] },
				order_by: 'expiry_date desc',
				limit: 1
			});
			latest = ptnj[0];
			}
			if (latest) {
			// 3) Set the pt_principal field in the child table row and the name in the last_pawn_ticket field of the row
			frappe.model.set_value(cdt, cdn, 'pt_principal', latest.desired_principal);
			frappe.model.set_value(cdt, cdn, 'last_pawn_ticket', latest.name);
			frm.refresh_field('nj_items');
			}

			let total = 0;
			frm.doc.nj_items.forEach(function(item) {
				total += parseFloat(item.pt_principal);
			});

			//set total_cost to total
				frm.set_value('total_cost', total);
				frm.refresh_field('total_cost');
	
			


		}else if(isDisplayTransferType(frm.doc.transfer_type)){
			//get the pt_principal from the Non Jewelry Items doctype
			let pt_principal = await frappe.db.get_value('Non Jewelry Items', row.item_no, 'pt_principal');
			frappe.model.set_value(cdt, cdn, 'pt_principal', pt_principal.message.pt_principal);
			frappe.model.set_value(cdt, cdn, 'last_pawn_ticket', 'Unnecessary');
			frm.refresh_field('nj_items');

			//get total price from all item_no in the table and set it to total_cost
			let total_price = 0;
			frm.doc.nj_items.forEach(function(item) {
				total_price += parseFloat(item.selling_price);
			});
			//set price to total_price
			frm.set_value('total_price', total_price);
			frm.refresh_field('total_price');
		}

		updatePawnTicketEnvelopeCounts(frm);
		},
		nj_items_remove: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		//get total pt_principal from all item_no in the table and set it to total_cost
		let total = 0;
		
		frm.doc.nj_items.forEach(function(item) {
			total += item.pt_principal;
		});
		//set total_cost to total
		frm.set_value('total_cost', total);
		frm.refresh_field('total_cost');

		updatePawnTicketEnvelopeCounts(frm);
		}

	});

frappe.ui.form.on('Transfer Items SB', {
	//upon selecting a Form Number/ last_pawn_ticket get all items inside the jewelry_items table of that Agreement to Sell. 
	// For each item, create a new row and add it to the sb_items table
	last_pawn_ticket: function (frm, cdt, cdn) {
		if (frm._adding_from_ats) return;

		const row = locals[cdt][cdn];
		const formNumber = (row && row.last_pawn_ticket || '').trim();
		if (!formNumber) return;

		const isRowEmpty = r =>
			!(r.item_no || r.type || r.karat || r.weight || r.densi || r.color || r.principal || r.selling_price);
		const reuseCurrentRow = isRowEmpty(row);

		frm._adding_from_ats = true;

		frappe.db.get_list('Jewelry List', {
			fields: ['item_no', 'type', 'karat', 'weight', 'densi', 'color'],
			filters: { parent: formNumber, parenttype: 'Agreement to Sell' },
			limit: 500
		}).then(async items => {
			if (!items || !items.length) {
				frappe.msgprint(__('No jewelry items found for Agreement to Sell {0}', [formNumber]));
				return;
			}

			const itemNos = Array.from(new Set(items.map(it => it.item_no).filter(Boolean)));
			let itemInfoByNo = new Map();
			if (itemNos.length) {
				const infoRows = await frappe.db.get_list('Jewelry Items', {
					fields: ['name', 'appraisal_value', 'selling_price', 'total_weight', 'karat', 'color', 'densi', 'type'],
					filters: { name: ['in', itemNos] },
					limit: itemNos.length
				});
				itemInfoByNo = new Map(infoRows.map(r => [r.name, r]));
			}

			const existing = new Set(
				(frm.doc.sb_items || [])
					.filter(r => !(reuseCurrentRow && r.name === cdn))
					.map(r => `${r.last_pawn_ticket || ''}::${r.item_no || ''}`)
			);

			const keyOf = it => `${formNumber}::${it.item_no || ''}`;
			const missing = items.filter(it => it.item_no && !existing.has(keyOf(it)));

			if (!missing.length) {
				frm.refresh_field('sb_items');
				return;
			}

			missing.forEach((it, idx) => {
				const target = (idx === 0 && reuseCurrentRow) ? row : frm.add_child('sb_items');
				const info = itemInfoByNo.get(it.item_no) || {};

				target.last_pawn_ticket = formNumber;
				target.item_no = it.item_no;
				target.type = it.type || info.type;
				target.karat = it.karat || info.karat;
				target.weight = it.weight || info.total_weight;
				target.densi = it.densi || info.densi;
				target.color = it.color || info.color;
				target.principal = toNumberSafe(info.appraisal_value);
				target.selling_price = toNumberSafe(info.selling_price);
			});

			frm.refresh_field('sb_items');

			//each time we add an item, add its principal to total_cost
			const totalJewelryPrincipal = (frm.doc.sb_items || []).reduce(
			(sum, child) => sum + toNumberSafe(child.principal),
			0
			);
			frm.set_value('total_cost', totalJewelryPrincipal);
			frm.refresh_field('total_cost');
			updateJewelryCounts(frm);

			
		}).catch(error => {
			console.warn('Unable to fetch Agreement to Sell items', error);
		}).finally(() => {
			frm._adding_from_ats = false;
		});
	},

	sb_items_add(frm) {
		updateJewelryCounts(frm);
	},

	before_sb_items_remove(frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		frm._sb_removed_form_map = frm._sb_removed_form_map || {};
		frm._sb_removed_form_map[cdn] = row ? row.last_pawn_ticket : null;
	},

	sb_items_remove(frm, cdt, cdn) {
		frm._sb_removed_form_map = frm._sb_removed_form_map || {};
		const removedForm = frm._sb_removed_form_map[cdn];
		delete frm._sb_removed_form_map[cdn];

		if (removedForm) {
			const before = frm.doc.sb_items ? frm.doc.sb_items.length : 0;
			const filtered = (frm.doc.sb_items || []).filter(
				item => item.last_pawn_ticket !== removedForm
			);

			if (filtered.length !== before) {
				filtered.forEach((row, idx) => {
					row.idx = idx + 1;
				});
				frm.doc.sb_items = filtered;
				frm.refresh_field('sb_items');
			}
		}

		const totalSbPrincipal = (frm.doc.sb_items || []).reduce(
			(sum, child) => sum + toNumberSafe(child.principal),
			0
		);
		frm.set_value('total_cost', totalSbPrincipal);
		frm.refresh_field('total_cost');
		updateJewelryCounts(frm);
	}

});


frappe.ui.form.on('Transfer Items J', {

	before_j_items_remove(frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		frm._j_removed_ticket_map = frm._j_removed_ticket_map || {};
		frm._j_removed_ticket_map[cdn] = row ? row.last_pawn_ticket : null;
	},

	j_items_remove: function(frm, cdt, cdn) {

		//check if all the items with the same last_pawn_ticket are removed
		frm._j_removed_ticket_map = frm._j_removed_ticket_map || {};
		const removedTicket = frm._j_removed_ticket_map[cdn];
		delete frm._j_removed_ticket_map[cdn];

		if (removedTicket) {
			const before = frm.doc.j_items ? frm.doc.j_items.length : 0;
			const filtered = (frm.doc.j_items || []).filter(
				item => item.last_pawn_ticket !== removedTicket
			);

			if (filtered.length !== before) {
				filtered.forEach((row, idx) => {
					row.idx = idx + 1;
				});
				frm.doc.j_items = filtered;
				frm.refresh_field('j_items');
			}
		}

		const toNumber = value => {
		const num = parseFloat(value);
		return Number.isFinite(num) ? num : 0;
		};
		//each time we remove an item, remove its principal to total_cost if transfer type is Pull out of Expired Sangla
		if (frm.doc.transfer_type == "Pull out of Expired Sangla") {
			const totalJewelryPrincipal = (frm.doc.j_items || []).reduce(
			(sum, child) => sum + toNumber(child.principal),
			0
			);
			
			frm.set_value('total_cost', totalJewelryPrincipal);
			frm.refresh_field('total_cost');
		} else if (isDisplayTransferType(frm.doc.transfer_type)){
			//each time we remove an item, remove its selling_price to total_price
			const totalJewelryPrice = (frm.doc.j_items || []).reduce(
			(sum, child) => sum + toNumber(child.selling_price),
			0
			);
			
			frm.set_value('total_price', totalJewelryPrice);
			frm.refresh_field('total_price');
		}

		updateJewelryCounts(frm);
		updatePawnTicketEnvelopeCounts(frm);
	},

	item_no: function (frm, cdt, cdn) {
			const row = locals[cdt][cdn];
			if (!row.item_no) { 
				return;
			} else {
				//row.last_pawn_ticket = 'Unnecessary';
				//frm.refresh_field('j_items');
				updateJewelryCounts(frm);
				recalculateJewelryTransferTotals(frm);
				if (isDisplayTransferType(frm.doc.transfer_type)){
					frm.set_df_property('total_price', 'hidden', 0);
					frm.refresh_field('total_price');
				} else if (frm.doc.transfer_type == "Pull out of Expired Sangla") {
					frm.set_value('total_price', 0);
					frm.refresh_field('total_price');
					frm.set_df_property('total_price', 'hidden', 1);
					frm.refresh_field('total_price');

				}



			
			}
	},


	last_pawn_ticket: function (frm, cdt, cdn) {

	// guard against re-entrancy (blur/refresh retriggers)
	if (frm._adding_from_pt) return;

	const row = locals[cdt][cdn];
	const pt = row.last_pawn_ticket;
	if (!pt) return;

	// helper: is the current row still “empty” (so we can reuse it)
	const isRowEmpty = r =>
		!(r.item_no || r.type || r.karat || r.weight || r.densi || r.color);

	const reuseCurrentRow = isRowEmpty(row);

	frm._adding_from_pt = true; // start guard

	frappe.db.get_list('Jewelry List', {
		fields: ['item_no', 'type', 'karat', 'weight', 'densi', 'color', 'suggested_appraisal_value'],
		filters: { parent: pt },
		limit: 500
	}).then(async items => {
		if (!items || !items.length) {
		frappe.msgprint(__('No jewelry items found for {0}', [pt]));
		return;
		}

		const toNumber = value => {
		const num = parseFloat(value);
		return Number.isFinite(num) ? num : 0;
		};

		const roundTo = (value, places = 0) => {
		const num = toNumber(value);
		if (!Number.isFinite(num)) return 0;

		if (places >= 0) {
			if (frappe.utils && typeof frappe.utils.flt === 'function') {
			return frappe.utils.flt(num, places);
			}
			return Number(num.toFixed(places));
		}

		const factor = Math.pow(10, places);
		if (frappe.utils && typeof frappe.utils.flt === 'function') {
			return frappe.utils.flt(num * factor, 0) / factor;
		}
		return Math.round(num * factor) / factor;
		};

		const roundCurrency = value => roundTo(value, 0);

		let desiredPrincipal = 0;
		let dateLoanGranted = null;
		try {
		const { message } = await frappe.db.get_value(
			'Pawn Ticket Jewelry',
			pt,
			['desired_principal', 'date_loan_granted']
		);
		if (message) {
			if (message.desired_principal !== undefined) {
			desiredPrincipal = toNumber(message.desired_principal);
			}
			dateLoanGranted = message.date_loan_granted || null;
		}
		} catch (error) {
		console.warn('Unable to fetch pawn ticket details for', pt, error);
		}

		const totalAppraisal = items.reduce(
		(sum, item) => sum + toNumber(item.suggested_appraisal_value),
		0
		);
		const principalByItem = new Map();
		items.forEach(item => {
		const appraisal = toNumber(item.suggested_appraisal_value);
		const ratio = totalAppraisal ? appraisal / totalAppraisal : 0;
		principalByItem.set(item.item_no, roundCurrency(desiredPrincipal * ratio));
		});

		//apply adjustment to the last item to fix rounding issues
		const sumPrincipal = Array.from(principalByItem.values()).reduce((sum, val) => sum + toNumber(val), 0);
		const remainder = desiredPrincipal - sumPrincipal;
		if (remainder !== 0) {
		const lastItem = items[items.length - 1];
		if (lastItem && principalByItem.has(lastItem.item_no)) {
			const adjusted = roundCurrency((principalByItem.get(lastItem.item_no) || 0) + remainder);
			principalByItem.set(lastItem.item_no, adjusted);
		} else {
			frappe.msgprint(__('Calculated principals do not match desired principal for {0}', [pt]));
		}
		}

		// Exclude the current row *only if* we plan to reuse it
		const existing = new Set((frm.doc.j_items || [])
		.filter(r => !(reuseCurrentRow && r.name === cdn))
		.map(r => `${r.last_pawn_ticket || ''}::${r.item_no || ''}`));

		const keyOf = it => `${pt}::${it.item_no || ''}`;
		const missing = items.filter(it => !existing.has(keyOf(it)));

		// pull selling prices from Jewelry Items for all items in this PT
		const itemNos = Array.from(new Set(items.map(it => it.item_no).filter(Boolean)));
		let sellingPriceByItem = new Map();
		if (itemNos.length) {
		const priceRows = await frappe.db.get_list('Jewelry Items', {
			fields: ['name', 'selling_price'],
			filters: { name: ['in', itemNos] },
			limit: itemNos.length
		});
		sellingPriceByItem = new Map(
			priceRows.map(r => [r.name, toNumber(r.selling_price)])
		);
		}

	//each time we add an item, add its principal to total_cost

		if (missing.length > 0) {
		missing.forEach((it, idx) => {
			const target = (idx === 0 && reuseCurrentRow) ? row : frm.add_child('j_items');
			target.last_pawn_ticket = pt;
			target.item_no = it.item_no;
			target.type = it.type;
			target.karat = it.karat;
			target.weight = it.weight;
			target.densi = it.densi;
			target.color = it.color;
			target.selling_price = sellingPriceByItem.has(it.item_no)
			? sellingPriceByItem.get(it.item_no)
			: 0;
			target.principal = principalByItem.get(it.item_no) || 0;
			target.date_loan_granted = dateLoanGranted;
			existing.add(keyOf(it));
		});
		}

		// Update principals for all rows linked to this pawn ticket
		(frm.doc.j_items || []).forEach(child => {
		if (child.last_pawn_ticket === pt && principalByItem.has(child.item_no)) {
			child.principal = principalByItem.get(child.item_no);
		}
		if (child.last_pawn_ticket === pt && sellingPriceByItem.has(child.item_no)) {
			child.selling_price = sellingPriceByItem.get(child.item_no);
		}
		if (child.last_pawn_ticket === pt) {
			child.date_loan_granted = dateLoanGranted;
		}
		});

		frm.refresh_field('j_items');
		updateJewelryCounts(frm);

		recalculateJewelryTransferTotals(frm);
		updatePawnTicketEnvelopeCounts(frm);
	}).finally(() => {
		// release guard after UI updates
		frm._adding_from_pt = false;
	});
	}

});

// frappe.ui.form.on('Transfer Items J', {
//   last_pawn_ticket: function (frm, cdt, cdn) {

	
//     const child = locals[cdt][cdn];
//     if (!child.last_pawn_ticket) return;

// //msgprint current value of last_pawn_ticket
// 	frappe.msgprint(`Fetching details from Pawn Ticket Jewelry: ${child.last_pawn_ticket}`);


//     // Example: populate fields in THIS row from the PT’s first matching item
//     frappe.db.get_doc('Pawn Ticket Jewelry', child.last_pawn_ticket).then(doc => {
//       const first = (doc.jewelry_items || [])[0];
//       if (!first) return;

//       child.item_no = first.item_no;
//       child.type = first.type;
//       child.karat = first.karat;
//       child.weight = first.weight;
//       child.densi = first.densi;
//       child.color = first.color;

//       frm.refresh_field('j_items');
//     });
//   }
// });
