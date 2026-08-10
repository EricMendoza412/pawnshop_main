import frappe


# Exclusive boundary: records created on or before 2026-08-08 are eligible.
LEGACY_CUTOFF = "2026-08-09 00:00:00"


def execute():
	"""Classify pre-overhaul rows without submitting them or affecting the CIV ledger."""
	if not frappe.db.exists("DocType", "Fund Transfer"):
		return

	frappe.db.sql(
		"""
		update `tabFund Transfer`
		set status = 'Imported Historical',
			source_system = 'Migration',
			business_date = coalesce(business_date, date(date_of_transfer), date(creation)),
			transfer_type = case
				when (ifnull(vc_to_cm, 0) > 0) + (ifnull(cm_to_vc, 0) > 0)
					+ (ifnull(vc_to_wu_cashier, 0) > 0) + (ifnull(wu_cashier_to_vc, 0) > 0)
					+ (ifnull(vc_to_fx_cashier, 0) > 0) + (ifnull(fx_cashier_to_vc, 0) > 0)
					+ (ifnull(vc_to_ps_cashier, 0) > 0) + (ifnull(ps_cashier_to_vc, 0) > 0) = 1
				then case
					when ifnull(vc_to_cm, 0) > 0 then 'Vault to Cash Manager'
					when ifnull(cm_to_vc, 0) > 0 then 'Cash Manager to Vault'
					when ifnull(vc_to_wu_cashier, 0) > 0 then 'Vault to Remittance'
					when ifnull(wu_cashier_to_vc, 0) > 0 then 'Remittance to Vault'
					when ifnull(vc_to_fx_cashier, 0) > 0 then 'Vault to ForEx'
					when ifnull(fx_cashier_to_vc, 0) > 0 then 'ForEx to Vault'
					when ifnull(vc_to_ps_cashier, 0) > 0 then 'Vault to Pawnshop (-NCB)'
					when ifnull(ps_cashier_to_vc, 0) > 0 then 'Pawnshop (-NCB) to Vault'
				end
				else transfer_type
			end,
			amount = case
				when (ifnull(vc_to_cm, 0) > 0) + (ifnull(cm_to_vc, 0) > 0)
					+ (ifnull(vc_to_wu_cashier, 0) > 0) + (ifnull(wu_cashier_to_vc, 0) > 0)
					+ (ifnull(vc_to_fx_cashier, 0) > 0) + (ifnull(fx_cashier_to_vc, 0) > 0)
					+ (ifnull(vc_to_ps_cashier, 0) > 0) + (ifnull(ps_cashier_to_vc, 0) > 0) = 1
				then greatest(ifnull(vc_to_cm, 0), ifnull(cm_to_vc, 0),
					ifnull(vc_to_wu_cashier, 0), ifnull(wu_cashier_to_vc, 0),
					ifnull(vc_to_fx_cashier, 0), ifnull(fx_cashier_to_vc, 0),
					ifnull(vc_to_ps_cashier, 0), ifnull(ps_cashier_to_vc, 0))
				else amount
			end
		where creation < %s
			and docstatus = 0
			and status = 'Draft'
			and ifnull(initiated_by, '') = ''
			and ifnull(authorized_by, '') = ''
			and ifnull(expected_authorizer, '') = ''
			and ifnull(source_system, '') in ('', 'ERPNext')
		""",
		LEGACY_CUTOFF,
	)
