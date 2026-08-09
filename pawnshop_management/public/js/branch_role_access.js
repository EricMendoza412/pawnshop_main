(function () {
	const ROLE = "Vault Custodian";
	const VC_LABELS = [
		"Vault Custodian Reports",
		"VC Count Report",
		"VC Turnover Lists (J, NJ, SB)",
		"VC Agreement to Sell List",
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
		"Vault Custodian Non Jewelry Report",
		"Vault Custodian Jewelry Report A",
		"Vault Custodian Jewelry Report B",
		"VC Agreement to Sell List",
		"New Sangla today (J)",
		"Renewed PT today (J)",
		"Redeemed PT today (J)",
		"Daily New J-Sangla",
		"VC Turnover Checklist",
		"Transfer Tracker",
	];

	let hasVaultCustodianAccess = true;
	let matchesBranchFilterRoleProfile = false;
	let fundTransferAccess = { has_any_access: true, fx_cashier: true, remittance_cashier: true };

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
		frappe.call({
			method: "pawnshop_management.operations_access_control.access_control.get_fund_transfer_access",
			callback(response) {
				fundTransferAccess = response.message || {};
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
			applyFundTransferVisibility();
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

		applyFundTransferVisibility();
	}

	function setNavigationVisibility(labels, visible, marker) {
		document.querySelectorAll("a, .widget, .shortcut-widget-box, .ce-block, .link-item, .desk-sidebar-item").forEach(element => {
			if (!textMatches(element, labels)) return;
			const container = element.closest(".ce-block, .shortcut-widget-box, .widget, .link-item, .desk-sidebar-item, a");
			if (!container) return;
			if (visible) {
				if (container.dataset[marker] === "1") {
					container.style.display = "";
					delete container.dataset[marker];
				}
			} else {
				container.dataset[marker] = "1";
				container.style.display = "none";
			}
		});
	}

	function applyFundTransferVisibility() {
		setNavigationVisibility(["Foreign Exchange"], Boolean(fundTransferAccess.fx_cashier), "fundTransferFxHidden");
		setNavigationVisibility(["Remittance"], Boolean(fundTransferAccess.remittance_cashier), "fundTransferRemitHidden");
		setNavigationVisibility(["Fund Transfer", "New Fund Transfer"], Boolean(fundTransferAccess.has_any_access), "fundTransferLinkHidden");

		const route = frappe.get_route ? frappe.get_route().join("/") : "";
		if (
			(routeMatchesWorkspace(route, "Foreign Exchange") && !fundTransferAccess.fx_cashier)
			|| (routeMatchesWorkspace(route, "Remittance") && !fundTransferAccess.remittance_cashier)
		) {
			frappe.set_route("workspace", "Pawnshop Management");
		}
	}

	function routeMatchesWorkspace(route, workspace) {
		const slug = workspace.toLowerCase().replace(/[^a-z0-9]+/g, "-");
		return route.includes(workspace) || route.toLowerCase().includes(slug);
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
