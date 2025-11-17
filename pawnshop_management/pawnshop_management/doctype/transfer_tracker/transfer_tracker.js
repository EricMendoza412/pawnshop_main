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

const updateJewelryCounts = frm => {
	//update total_count as well as individual counts based on j_items table
	if (!frm || !frm.doc) return;

	const counts = getEmptyJewelryCounts();

	if (frm.doc.item_type === 'Jewelry Items') {
		(frm.doc.j_items || []).forEach(row => {
			const type = (row.type || '').trim();
			const fieldname = JEWELRY_TYPE_FIELD_MAP[type];
			if (fieldname) {
				counts[fieldname] += 1;
			}
		});
	}

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

frappe.ui.form.on('Transfer Tracker', {
	refresh(frm) {
		updateJewelryCounts(frm);
	},

	onload: function(frm) {
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
						if (frappe.user.has_role("Subastado member") && frappe.session.user != "Administrator") {	
							frm.set_value('origin', 'Subastado NJ');
						}else{
							frm.set_value('origin', records[0].name);
						}
						
						frm.refresh_field('origin');

					})
				}
			})

		// If user has role Subastado member, Transfer Type should be Transfer of Display Items and should be read only
		if (frappe.user.has_role("Subastado member") && frappe.session.user != "Administrator") {
			frm.set_value('transfer_type', 'Transfer of Display Items');
			frm.set_df_property('transfer_type', 'read_only', 1);
			frm.refresh_field('transfer_type');
		}	
		

		//Put name of current user in the field released_by
		frm.set_value('released_by', frappe.session.user);
		frm.refresh_field('released_by');
		//Disable save button until witnessed_by and rover is filled out
		frm.disable_save();
		//Hide nj_items table until transfer_type is filled out
		frm.set_df_property('nj_items', 'hidden', 1);
		frm.refresh_field('nj_items');
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
			}else{
			// make j items table appear
			frm.set_df_property('j_items', 'hidden', 0);
			frm.refresh_field('j_items');
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
		
		}



	},

	origin: function(frm) {

		frappe.db.get_value("Pawnshop Naming Series", frm.doc.origin, "nj_transfer_form")
		.then(r => {
			let current_form = r.message.nj_transfer_form;
			frappe.db.get_value("Branch IP Addressing", frm.doc.origin, "branch_code")
				.then(r => {
					let branchCode = r.message.branch_code;
					if (frappe.user.has_role("Subastado member") && frappe.session.user != "Administrator") {
					current_form = "SCG-"+ current_form	
					}else{
					current_form = branchCode + "-"+ current_form	
					}
						frm.set_value('transfer_no', current_form );
						frm.refresh_field('transfer_no');
				})
		})
	},

	witnessed_by: function(frm){
		if (frm.doc.witnessed_by != null) {
			//ask for password
			frappe.prompt({
				label: 'Password',
				fieldname: 'password',
				fieldtype: 'Password'
			}, (password) => {
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
			})
		}
	},
	rover: function(frm){
		if (frm.doc.rover != null) {
			//ask for password
			frappe.prompt({
				label: 'Password',
				fieldname: 'password',
				fieldtype: 'Password'
			}, (password) => {
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
		}

	},

	transfer_type: function(frm){
		if (frm.doc.transfer_type == "Pull out of Expired Sangla") {
				//Set Destination to Subastado NJ and make it read only
				
				if(frm.doc.item_type == "Non Jewelry Items"){
					frm.set_value('destination', 'Subastado NJ');
					//Set filter for NJ items table based on the origin except if user is a Subastado member
					frm.set_query('item_no', 'nj_items', function(){
						return {
							filters: {
								workflow_State: 'Collected',
								branch: frm.doc.origin
							}
						}
					})
				}else{
					frm.set_value('destination', 'Subastado J');
					//Set filter for NJ items table based on the origin except if user is a Subastado member
					frm.set_query('last_pawn_ticket', 'j_items', function(){
						return {
							filters: {
								workflow_State: ['in',['Active', 'Expired']],
								branch: frm.doc.origin
							}
						}
					})
				}

				frm.set_df_property('destination', 'read_only', 1);
				frm.refresh_field('destination');

						
		}else if (frm.doc.transfer_type == "Transfer of Display Items") {
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
				}

		}
	},

	j_items_add(frm) {
		updateJewelryCounts(frm);
	},

	j_items_remove(frm) {
		updateJewelryCounts(frm);
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


		}else if(frm.doc.transfer_type == "Transfer of Display Items"){
			//get the pt_principal from the Non Jewelry Items doctype
			let pt_principal = await frappe.db.get_value('Non Jewelry Items', row.item_no, 'pt_principal');
			frappe.model.set_value(cdt, cdn, 'pt_principal', pt_principal.message.pt_principal);
			frappe.model.set_value(cdt, cdn, 'last_pawn_ticket', 'Unnecessary');
			frm.refresh_field('nj_items');

			//get total pt_principal from all item_no in the table and set it to total_cost
			let total = 0;
			frm.doc.nj_items.forEach(function(item) {
				total += parseFloat(item.pt_principal);
			});
			//set total_cost to total
			frm.set_value('total_cost', total);
			frm.refresh_field('total_cost');
		}
		
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
	}

});

// Child doctype handler (replace 'Transfer Tracker Item' with your child doctype name)
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
    //each time we remove an item, remove its principal to total_cost
    const totalJewelryPrincipal = (frm.doc.j_items || []).reduce(
      (sum, child) => sum + toNumber(child.principal),
      0
    );

    frm.set_value('total_cost', totalJewelryPrincipal);
    frm.refresh_field('total_cost');
    updateJewelryCounts(frm);
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
    try {
      const { message } = await frappe.db.get_value('Pawn Ticket Jewelry', pt, 'desired_principal');
      if (message && message.desired_principal !== undefined) {
        desiredPrincipal = toNumber(message.desired_principal);
      }
    } catch (error) {
      console.warn('Unable to fetch desired_principal for', pt, error);
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
        target.principal = principalByItem.get(it.item_no) || 0;
        existing.add(keyOf(it));
      });
    }

    // Update principals for all rows linked to this pawn ticket
    (frm.doc.j_items || []).forEach(child => {
      if (child.last_pawn_ticket === pt && principalByItem.has(child.item_no)) {
        child.principal = principalByItem.get(child.item_no);
      }
    });

    frm.refresh_field('j_items');
    updateJewelryCounts(frm);

    //each time we add an item, add its principal to total_cost
    const totalJewelryPrincipal = (frm.doc.j_items || []).reduce(
      (sum, child) => sum + toNumber(child.principal),
      0
    );

    frm.set_value('total_cost', totalJewelryPrincipal);
    frm.refresh_field('total_cost');
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
