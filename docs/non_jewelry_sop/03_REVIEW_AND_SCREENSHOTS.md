# Owner Review Register and Screenshot Plan

Prepared 7 November 2026. This is an internal review appendix, not an assertion that the operational draft has been approved. The user authorized an independent best-understanding draft and will confirm assumptions afterward. No approval is required merely to read or revise this draft.

## Decisions to confirm when convenient

| ID | Decision or missing evidence | Working treatment in the draft |
| --- | --- | --- |
| R01 | Exact new-ticket workflow: save, review, submit, Active state, and authorized roles. | Describe authorized submission without inventing action names. Capture live Workflow records and screens. |
| R02 | Who encodes, physically inspects, assists, approves, pays out, stores, and releases. | Proposed separation of responsibilities; only specific code-enforced restrictions are presented as implemented. |
| R03 | Whether one ticket may contain multiple NJ gadgets. | Ordinary form hides Add Item; document a single-item flow pending confirmation. Review duplicate-row and shared-principal handling before permitting multiple items. |
| R04 | Customer creation, ID-upload application, accepted identification, expiry exceptions, and contact/address maintenance. | Explain existing Customer/Contact dependencies; leave onboarding and acceptance policy to the approved company process. |
| R05 | Physical testing checklist and category definitions for Maximum, Minimum, and Defective. | Use configured categories but do not invent device acceptance criteria. Include the existing eSIM guide as a reference. |
| R06 | Battery discrepancy rejection and whether main/assistant must be different people. | Flag the warning and recommend review; distinguish the prompt from hard enforcement or independent approval. |
| R07 | Live NJ maturity/expiry days and rate; business meaning of maturity versus expiry. | Defaults are examples only. Both dates derive from loan-granted date. |
| R08 | Expiry at 03:00 on the date versus end-of-day; exceptions and overdue catch-up. | Document exact code behavior, mark business acceptance unresolved. |
| R09 | Allowed NJ Interest Payment/Amortization timing and maturity-day treatment. | Document the mismatched message/condition; refer boundary cases for approval. |
| R10 | Accrued-interest, early-redemption discount, holiday/senior, and manager-discount policy. | Describe implemented computation, not legal entitlement or newly approved fees. Verify examples in an authorized test site. |
| R11 | Renewal when the configured gadget rate changes; legacy zero/missing-rate tickets. | Preserve code behavior and flag inconsistent 7% fallback/printed-rate treatment. |
| R12 | Payment receipt verification, screenshots/reference evidence, split payment conventions, and change-mode authority. | Electronic settlement verification is a proposed staff step, not automated confirmation. |
| R13 | Branch print formats, paper stock, alignment, copies, signatures, and issue sequence. | Name the exported formats; require comparison of printed and stored terms. |
| R14 | Lost-ticket redemption, authorized representatives, death/incapacity, or disputed ownership. | No invented exception procedure; refer to the approved policy. |
| R15 | Eligible pullout dates, treatment of Active/Returned tickets, transport documentation, receiving roles/actions. | Require approved pullout list and physical reconciliation; date-range output alone is not approval. |
| R16 | Subastado reappraisal-to-For Sale action, selling-price approval, and complete Gadgets For Sale report. | Use only established fields/behaviors; verify live workflow/report scripts. |
| R17 | Actual sale interface, external application, payment/receipt creation, Sold update, returns/refunds, and commission policy. | Mark integration boundary; do not use jewelry Agreement to Sell as NJ resale. |
| R18 | Installment down-payment collection and payment-table updater; Under Installment/Sold transitions. | Form exists but full updater is not in its controller. Locate the production scripts/integration before writing exact collection buttons. |
| R19 | Whether embedded installment terms are current: 25% deposit, PHP 100 minimum, 60/90/120 days versus 2/3/4 months, two-day grace, refund/default policy. | Quote/paraphrase as embedded template statements, not confirmed enforcement. |
| R20 | Supported cancellation/reversal/amendment process for each PR type and item corrections. | Escalate saved corrections; do not promise automatic rollback of linked documents. |
| R21 | Daily closing cutoff, handling cash zero/shortage, inventory count responsibilities, and custodian handover. | Proposed reconciliation procedure around verified CPR/turnover behavior. |
| R22 | SMS timing, wording, dual reminders when dates coincide, retry and delivery monitoring. | State request versus delivery distinction; do not promise one SMS per ticket or guaranteed receipt. |
| R23 | Final Google Sites navigation and how to merge with the existing SOP. | Preserve existing useful content; add ERPNext pages under the appropriate lifecycle sections after review. |

## Implementation findings that affect training or acceptance

These are source-level observations requiring focused validation, not fixes already performed. A live database script or customization may alter behavior, so confirm on the intended deployment.

| ID | Observation | Why the manual calls it out |
| --- | --- | --- |
| F01 | Saving an NJ item finds its latest modified linked ticket; Active/Expired links cause rejection/cancellation and an amendment even without a material appraisal change check. | Staff must not assume saved item edits are harmless. The new ticket preserves loan principal rather than recalculating it from the changed appraisal. |
| F02 | Principal/appraisal limit, assistant presence, laptop checks, and most payment split checks are client-side only in the reviewed handlers. | Do not claim imports/API calls have equivalent protection. |
| F03 | Expiry routine uses expiry_date=today and Active; does not select all overdue Active tickets or explicitly set change_status_date. | Missed runs and reporting dates need reconciliation; the state changes on the date, not after it. |
| F04 | PR directly updates ticket/items without always updating batches; renewal does not explicitly reset item/batch states. | A successful receipt does not guarantee every related state is synchronized. Especially inspect renewals after expiry. |
| F05 | Several mutation paths commit intermediate changes; the PR has no custom on_cancel reversal method in its exported controller. | After a failure/cancellation, verify records before repeating a transaction. |
| F06 | Interest helper requires a parseable birthday, uses current host date for age, and multiplies by int(interest). | Missing birthday, retroactive age, decimal truncation, and string conversion are review cases. |
| F07 | No explicit general clamp on accrued months/total; custom maturity–expiry periods feed a days/30 base into a monthly calculation. | Check negative totals and nonstandard terms before approving quotations. |
| F08 | Amortization message says “on or after,” condition checks “after”; Interest Payment is blocked on maturity although its message says “before.” | Training must not invent a resolved boundary policy. |
| F09 | Amortization lacks consistent server upper bounds; mixed-mode fields can overwrite Additional Amortization. | Validate that a principal reduction and final total are sensible, positive, and not double-counted. |
| F10 | Selecting Manager's discount subtracts one monthly-interest amount; no corresponding approval enforcement was established in the PR controller. | The option's “With Approval” label is not proof of an approval record. |
| F11 | Item and batch counter hooks contain cross-doctype existence checks; numbering is read before save. | Do not promise consecutive, collision-free allocation under concurrent/repeated saves. |
| F12 | Pullout date-range API includes Active and Returned tickets, and copies full ticket principal onto each item row. | Confirm eligibility and multi-item cost aggregation. |
| F13 | The NCB NJ print template prints 7% for stored rate 0 or 7 and 10% otherwise, plus a literal 30 term. It assumes a particular formatted-date structure and address naming. | Arbitrary rates/terms or date/address settings can yield a misleading print even when form values are correct. Inspect the branch-specific variant too. |
| F14 | Reservation reversion runs daily after 48 hours; not an exact two-day timer. | Do not promise release at the precise reservation anniversary. |
| F15 | Installment controller is empty; payment updater and full sale workflow are not established. Close sets the item For Sale from a browser hook. | Do not claim deposit/default/settlement automation solely from the agreement text. |
| F16 | Whole-peso price comparisons leave fractional gaps around 9,999/10,000 and 19,999/20,000; due dates use days while template says months. | Confirm approved pricing and term convention. |
| F17 | Branch list filtering has a customer-name search exception and can return no extra condition without a branch; permissions vary by live configuration. | Do not describe IP filtering as complete branch isolation. |
| F18 | CPR's loan query caps results at 500; some history queries lack explicit full pagination. Denomination inputs are amounts. | Reconcile high-volume days and train users on amount entry. |
| F19 | The NJ loan journal-entry code is commented out. | No claim of automatic general-ledger posting based on that block. |
| F20 | Turnover counts query Company Used while a transfer path writes Company used. | Check company-use inventory counts and actual stored statuses. |
| F21 | Both daily reminder purposes may qualify; flag is tied to delivery, not merely accepted request. | Check wording, duplicate prevention, and pending-delivery retries. |
| F22 | New forms normally default Charger=true; identity and battery warnings do not block all saves. | Staff still need physical verification and approved exception handling. |

## Screenshot capture plan

Use a demonstration customer and item wherever possible. Show actual field labels and values necessary to understand the step. Mask unrelated customer names, IDs, mobile numbers, addresses, account references, and balances. Never include passwords, integration credentials, or API keys. Screenshots should reflect the same tested workflow/version as the final text.

| Marker | Capture | Suggested caption |
| --- | --- | --- |
| S01 | Pawnshop Management workspace with relevant shortcuts/lists. | Start a new NJ loan or payment transaction here. |
| S02 | New pawn ticket header, dates, branch, and identifiers. | Verify the automatic branch and dates before encoding. |
| S03 | Settings with live NJ days and gadget rate. | Loan terms are based on these configured values as of [date]. |
| S04 | Customer Link search and populated details. | Select the exact customer, then check the fetched details. |
| S05 | Multiple-ID selector, image zoom, and expiry warning. | Inspect the selected ID; a warning is not an approval. |
| S06 | Item No dropdown and create-new action. | Create or select the item for this inventory group. |
| S07 | Completed normal NJ item form. | Record the actual gadget, accessories, and appraisers. |
| S08 | Laptop and tablet conditional fields. | Required specifications differ by item type. |
| S09 | Model pricing and example item adjustments. | Review model-based appraisal and deductions. |
| S10 | eSIM-only checkbox and existing guide image. | eSIM-only Apple cellphones cannot use Maximum. |
| S11 | Battery-health fields and discrepancy warning. | Refer discrepancies meeting the threshold for review. |
| S12 | Submitted ticket and both print previews. | Compare printed terms, item details, and amounts with the saved record. |
| S13 | PR transaction type → document type → ticket. | Select receipt purpose before choosing the pawn ticket. |
| S14 | Computation dialog and final receipt breakdown. | Wait for calculation and verify the amount to collect. |
| S15 | Redemption receipt, ticket, and item status. | Confirm all references before physical release. |
| S16 | Gadget Tracker and Active/Expired filter. | Monitor current loans and their reminder status. |
| S17 | SMS button/log, request and delivery statuses. | Request success and delivered confirmation are different. |
| S18 | NJ pullout tracker with loan-date range and items. | Review eligibility and physical count before dispatch. |
| S19 | Transfer For Receiving/Complete and item location. | Record dispatch and actual receipt as separate steps. |
| S20 | Subastado assessment and reservation history. | Record reassessment and reservation accountability. |
| S21 | Installment agreement, recorded payments, due date, print. | Verify the actual collection mechanism and current agreement terms. |
| S22 | Print-error replacement and Transferred to PT link. | A printing-error transfer replaces the document. |
| S23 | Change Mode of Payment and amended PR. | Payment correction retains an original/amended trail. |
| S24 | CPR amounts by denomination and discrepancy. | Enter currency totals per denomination, not piece counts. |
| S25 | Generated log and NJ Inventory Count. | Reconcile daily documents and system inventory. |
| S26 | Custodian turnover with Received By and acceptance. | The receiver accepts responsibility through the configured action. |

## Suggested acceptance walkthrough after owner review

Run these only in an authorized test environment or approved controlled demonstration. The documentation task did not perform them or generate their transactions.

1. Create a standard new NJ ticket; verify IP branch, numbering, dates, customer ID, item selection, appraisers, appraisal, principal, interest, save/approval, print, and batch.
2. Repeat with no charger, model exemption, Not Openline, Apple eSIM, and battery discrepancy. Confirm which outcomes block versus warn.
3. Verify disabled/missing-contact/expired-ID customer handling and a valid birthday required for PR computation.
4. Exercise ordinary renewal, renewal with amortization, standalone amortization, interest payment, and redemption using current and expired tickets. Reconcile ticket/item/batch states and receipt links.
5. Check maturity-day, month-end, holiday/Sunday, senior, early-redemption, changed-settings, decimal-interest, and over-amortization cases with approved expected amounts.
6. Try all supported payment modes and corrections; confirm the intended external settlement evidence and cancellation effects.
7. Demonstrate expiry, missed-run recovery procedure, SMS request/delivery, pullout eligibility, transfer witness/rover/receiver, and reconciliation of physical stock.
8. Demonstrate the actual Subastado sale, return, installment payment/default/release integration and document the previously missing screens.
9. Produce a CPR and compare cash denominations, receipts, payouts, sales, log, and inventory. Verify a controlled high-volume/pagination case if relevant.
10. Perform a custodian handover and verify access before and after acceptance.

Record each result, tester, date, software revision, and approved deviation. Update the manual to the observed and approved workflow rather than silently changing text to match assumptions.
