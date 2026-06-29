(function () {
	const ROLE = "Vault Custodian";
	const VC_LABELS = [
		"Vault Custodian Reports",
		"VC Count Report",
		"VC Turnover Lists (J, NJ, SB)",
		"VC Agreement to Sell List",
		"VC Tracker (Gadget)",
		"VC Tracker (Jewelry)",
		"Transaction Log Preview",
		"Transfer Tracker",
		"VC Turnover Checklist",
		"Daily New J-Sangla",
		"New Sangla Today (J)",
		"Renewed PT Today (J)",
		"Redeemed PT Today (J)",
		"Jewelry Inventory A",
		"Jewelry Inventory B",
		"Non Jewelry Inventory",
	];
	const VC_ROUTES = [
		"Vault Custodian Reports",
		"vault-custodian-reports",
		"VC Count Consolidated",
		"VC Turnover List",
		"VC Report",
		"Vault Custodian Non Jewelry Report",
		"Vault Custodian Jewelry Report A",
		"Vault Custodian Jewelry Report B",
		"VC Agreement to Sell List",
		"New Sangla today (J)",
		"Renewed PT today (J)",
		"Redeemed PT today (J)",
		"Daily New J-Sangla",
		"J End of Day Report",
		"NJ End of the Day Repor",
		"VC Turnover Checklist",
		"Transfer Tracker",
	];

	let hasVaultCustodianAccess = true;
	let matchesBranchFilterRoleProfile = false;

	function loadBranchRoles() {
		if (!frappe.session || frappe.session.user === "Guest") return;

		frappe.call({
			method: "pawnshop_management.operations_access_control.access_control.get_active_branch_roles",
			callback(response) {
				const roles = response.message || {};
				hasVaultCustodianAccess = Boolean(roles[ROLE]);
				matchesBranchFilterRoleProfile = Boolean(roles.matches_branch_filter_role_profile);
				applyVisibility();
			},
		});
	}

	function textMatches(element, values) {
		const text = (element.innerText || element.textContent || "").trim();
		return values.some(value => text === value || text.includes(value));
	}

	function hideClosestNavigationItem(element) {
		const container = element.closest(".ce-block, .shortcut-widget-box, .widget, .link-item, .desk-sidebar-item, a");
		if (container) {
			container.dataset.branchRoleHidden = "1";
			container.style.display = "none";
		}
	}

	function routeMatches(href) {
		return VC_ROUTES.some(route => {
			const slug = route.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
			return href.includes(encodeURIComponent(route)) || href.includes(route) || href.includes(slug);
		});
	}

	function applyVisibility() {
		if (hasVaultCustodianAccess || !matchesBranchFilterRoleProfile) {
			document.querySelectorAll("[data-branch-role-hidden='1']").forEach(element => {
				element.style.display = "";
				delete element.dataset.branchRoleHidden;
			});
			return;
		}

		document.querySelectorAll("a, .widget, .shortcut-widget-box, .ce-block, .link-item").forEach(element => {
			const href = element.getAttribute && (element.getAttribute("href") || "");
			if (routeMatches(href) || textMatches(element, VC_LABELS)) {
				hideClosestNavigationItem(element);
			}
		});

		const route = frappe.get_route ? frappe.get_route().join("/") : "";
		if (routeMatches(route)) {
			frappe.set_route("workspace", "Pawnshop Management");
		}
	}

	if (frappe.ready) {
		frappe.ready(loadBranchRoles);
	} else {
		setTimeout(loadBranchRoles, 0);
	}
	frappe.router.on("change", () => {
		loadBranchRoles();
		setTimeout(applyVisibility, 300);
	});

	const observer = new MutationObserver(() => applyVisibility());
	observer.observe(document.documentElement, { childList: true, subtree: true });
})();
