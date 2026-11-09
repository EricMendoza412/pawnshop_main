# Non-Jewelry Sangla: ERPNext User Guide

Draft for owner review • 7 November 2026 • English

This guide follows the Non-Jewelry loan from customer selection and appraisal through renewal, redemption, expiry, transfer, and resale. It describes the checked-in Pawnshop Management application. Live settings, permissions, database-stored scripts, and workflow configurations have not been inspected. Screen positions and some action labels must be confirmed in the live site.

**How to read this draft:** “System behavior” means behavior found in the source files; it is not a claim that the live installation was tested. “Proposed procedure—confirm” identifies an operational instruction that needs the owner's confirmation. “Live configuration—confirm” identifies a missing screen, workflow, or integration detail. Screenshot markers are placeholders for real ERPNext screenshots, not generated mockups.

## Page 1 — Start here: documents, access, and responsibilities

### Understand the records

| Record | What it represents |
| --- | --- |
| Customer and primary Contact | The pawner's identity, birthday, contact details, and ID records. |
| Pawn Ticket Non Jewelry | A particular loan, including its customer, dates, principal, interest, and linked items. |
| Non Jewelry Items | The individual gadget, its specifications, appraisal, appraisers, accessories, condition, and later custody/sale information. |
| Non Jewelry Batch | The inventory grouping identified by the loan's Inventory Tracking No. The application creates this when a new inventory group is submitted. |
| Provisional Receipt (PR) | Renewal, redemption, interest payment, amortization, and other receipts. |
| Transfer Tracker | A movement of items between locations, with release, witness, rover, and receiving information. |
| Installment Agreement Form | A customer's installment purchase of a resale gadget; this is separate from repayment of a pawn loan. |
| Cash Position Report (CPR) | The branch's daily cashier cash reconciliation. Submission creates a transaction log and inventory count record. |

**Do not confuse the three identifiers.** Pawn Ticket identifies the loan document, Inventory Tracking No identifies the inventory group, and Item No identifies the individual gadget. A renewal creates a new pawn ticket while retaining the existing inventory tracking number and item links.

### Log in and open the module

1. Log in using your assigned ERPNext account at the authorized branch station.
2. Open **Pawnshop Management** from the workspace/sidebar navigation. The repository defines this workspace; confirm its exact position on the live screen.
3. Under its shortcuts, use **New Pawn Ticket Non Jewelry** for a new sangla or **New Provisional Receipt** for payment-related transactions.
4. To find existing records, use **Non Jewelry Pawn Ticket**, **Provisional Receipt**, or **Non Jewelry Items** in the workspace lists.

The application checks the request IP against **Branch IP Addressing**. Selected operational role profiles are prevented from logging in when no branch mapping is found. New forms also use this mapping to fill the branch. If the branch is missing or incorrect, stop and ask the system administrator to check the mapping. Do not transact under another branch merely to complete the form.

**[Screenshot S01: Pawnshop Management workspace; mark New Pawn Ticket Non Jewelry, New Provisional Receipt, Non Jewelry Items, Gadget Tracker, and End of Day Reports.]**

### Know which responsibilities are configured separately

The application distinguishes account roles/role profiles from a branch's operational assignments. The registered Vault Custodian is read from the Branch record. A Pawnshop Cashier assignment uses **Branch Role Assignment**: an authorized Supervisor or Operations Manager creates it, and the assigned user accepts it using **Accept Role** on its assignment date. The branch cashier fields are cleared by the daily scheduled job. Confirm the day's assignment before preparing a CPR.

The repository does not establish every live permission or every approval step for new loans. A missing button can therefore indicate a permission or assignment issue. Refer it to the responsible manager; do not use someone else's account.

**Proposed procedure—confirm:** the main appraiser encodes and assesses the gadget, the assistant checks the physical gadget against the entry, the authorized cashier handles cash, and the custodian controls storage and release. Confirm who approves/submits each document and whether the same staff member may perform more than one task.

## Page 2 — Create a new Non-Jewelry pawn ticket

### Step 1: Open the new form and check the automatic details

Click **New Pawn Ticket Non Jewelry**. On a new form, the system sets **Date Loan Granted** to today's application date and resolves **Branch** from the request IP. When the branch is set, it reads that branch's **Pawnshop Naming Series** and **Branch IP Addressing** records to display the proposed pawn ticket and inventory tracking numbers.

The dates are calculated as follows:

| Field | System behavior | Your checkpoint |
| --- | --- | --- |
| Date Loan Granted | Today's date on a new form. | Check that the date is correct before proceeding. |
| Maturity Date | Date Loan Granted + Non Jewelry Maturity Period (Days). | Check the displayed date against the agreed term. |
| Expiry Date | Date Loan Granted + Non Jewelry Expiry Period (Days). | Check and explain the exact date to the customer. |
| Branch | Branch IP Addressing match. | Verify the actual transacting branch. |
| Pawn Ticket | Branch code + branch B-series counter + `B`. | Confirm the final saved number, including any conflict message. |
| Inventory Tracking No | Branch code + inventory counter + `NJ`. | Use the same number when matching the item and inventory stub. |

Both maturity and expiry are counted from **Date Loan Granted**. Expiry is not calculated by adding the expiry period to the maturity date. The checked-in defaults are 30 days for each NJ period, so the two dates can be the same. The live settings may differ.

For example, with both NJ periods set to 30, a loan granted on 7 November 2026 has maturity and expiry dates of 7 December 2026. This is calendar-day addition, not “the same date next month.”

**[Screenshot S02: New ticket header showing dates, branch, Pawn Ticket, and Inventory Tracking No.]**

**[Screenshot S03: Pawnshop Management Settings showing Gadget Interest Rate and the two NJ period fields; caption the actual values and screenshot date.]**

### Step 2: Select the correct customer

In **Search Customer by name or tracker**, type part of the customer's name or their tracker, then choose the correct result from the dropdown. The system fetches **Customer's Full Name** and uses the customer's primary Contact to populate **Customer Birthday** and display ID information.

Check the full name, tracker, birthday, and displayed ID against the person transacting. Similar names are not sufficient to identify a customer. Selecting a disabled Customer causes the browser to display **“This customer record is disabled”** and clear the selection.

The form also retrieves the latest original Jewelry and Non-Jewelry loan dates for that customer, both in the branch and across the accessible records. These are reference information, not an automatic approval decision.

**[Screenshot S04: Customer search results and populated customer details, using a demonstration customer.]**

### Step 3: Inspect the customer's ID

The ID image comes from the customer's primary Contact. The system initially selects the ID matching the Contact's default image, or the first ID row if no match exists. If there is more than one ID, use **Customer ID Picture** to choose another. Click the image to enlarge it.

The screen can display **“Selected customer ID has expired”**, **“All customer IDs have expired”**, **“No primary contact set”**, **“No IDs found for this contact”**, or **“No ID picture set for selected ID.”** An ID expiring today is not flagged as expired by this helper; it flags dates before today. Missing expiry dates are also not flagged as expired. These display rules do not themselves establish whether the ID is acceptable.

**Proposed procedure—confirm:** resolve missing, expired, unreadable, or mismatched identity records using the company's customer-verification procedure before approving the loan. The reviewed pawn-ticket code displays expiry warnings; it does not automatically reject the ticket solely because all IDs are expired.

If the customer is not registered, use the company's approved registration process. The project contains Customer/Contact customizations but does not establish the complete registration and ID-upload workflow. Ensure the Customer is linked to the intended primary Contact, with a valid birthday, mobile number, and ID records. Missing birthdays can also prevent later interest calculations.

**[Screenshot S05: ID selector, enlarged ID view, and a sample expiry warning; obscure personal data.]**

### Step 4: Link or create the gadget

In the **Non Jewelry Item(s)** table, click **Item No**. Select the existing item belonging to the current branch and inventory batch. If the item has not yet been created, use the Link field's create-new option for **Non Jewelry Items**, if your live permissions expose it.

The ticket filters item selection using the branch's current inventory counter and branch. Do not select a similarly described gadget from another inventory group.

The browser hides **Add Item** on refresh and when an item row is added. This suggests a single-item form flow, although the underlying table and server code can hold multiple rows. **Live configuration—confirm:** the exact first-row/create-new interaction and whether multiple gadgets may be included in one NJ ticket. Do not work around a hidden button.

**[Screenshot S06: Item No Link field and the create-new Non Jewelry Items option.]**

Continue with Page 3 to create and verify the item. After saving it, return to the ticket and ensure the saved Item No is selected.

## Page 3 — Encode and appraise the gadget

### Step 1: Confirm item identification and appraiser

On a new **Non Jewelry Items** form, the system fills Branch from the request IP and builds Item No from the branch code, inventory counter, `NJ`, and item counter. For example, an illustrative inventory group `1-500NJ` may contain item `1-500NJ-1`. These numbers are examples, not live counter values.

**Main Appraiser** is a read-only User link whose default is the current user. Verify the displayed appraiser before saving. The form separately fetches the appraiser's first name into **Main Appraiser Name**.

### Step 2: Enter specifications in order

Select **Type**, **Brand**, and **Model**, then enter the remaining details from the actual gadget. The item form currently offers Cellphone, Tablet, Laptop, and Camera. A Motorcycle value exists in some master/filter code, but it is not an available Type in the checked-in NJ item form.

| Item type | Details and form behavior |
| --- | --- |
| Cellphone | Enter Model Number, RAM, Internal Memory, Color, condition, network lock status, and actual accessories. |
| Tablet | Enter those applicable details and **Internet Connection Capability (Tablets Only)**: Wifi Only or Wifi with Cellular Data. |
| Non-Apple laptop | Model is relabeled **Processor & Generation** and Model Number becomes **Model Name**. Select actual RAM, storage, and disk type. The browser rejects the specified “Not Shown” values for RAM/storage and an empty or “Not Shown” disk type. |
| Apple laptop | The interface sets Disk Type to **Not Shown** and makes it read-only. Verify other specifications rather than assuming the Windows-laptop behavior applies. |
| Camera | Model Number is set to `N/A` and hidden; several memory/accessory controls are hidden. Confirm the live camera entry procedure and any hidden mandatory fields. |

Brand choices are filtered by Type. Model choices are filtered to **Accepted** models matching Type and usually Brand; non-Apple laptops instead use the accepted laptop model records with a blank Brand. If the correct model is absent, request master-data review. Do not substitute a different model to obtain a price.

**[Screenshot S07: Completed cellphone item with identification, specifications, condition, accessories, and appraisers.]**

**[Screenshot S08: Non-Apple laptop fields and Tablet internet capability field.]**

### Step 3: Record condition and accessories accurately

Choose **Category/Item Condition**: Maximum, Minimum, or Defective. Use the company's physical inspection criteria; the source files do not define the full inspection checklist for these categories.

Record the accessories actually received. Depending on type, the form includes Charger, Case, Box, Earphones, Pin, Manual, Sim Card, SD Card, Others, and other accessory fields. Some are hidden for particular types. Enter defects, missing parts, and relevant observations in **Comments**.

**Important:** the new-form script checks **Charger** by default, and selecting Cellphone or Tablet also checks it. Confirm physical receipt and untick it when no charger is included. A default checkmark is not evidence that an accessory was received.

### Step 4: Review the automatic appraisal

The system takes the selected condition's value from **Models** and applies these adjustments:

1. Start with the model's Maximum, Minimum, or Defective appraisal value.
2. If Charger is unticked, subtract PHP 300 unless the model's **No Charger No Less 300** option is checked.
3. If **Not Openline** is checked, multiply the adjusted value by 85% and round to the nearest PHP 100. In this network-lock branch, a negative result is set to zero.

Changing Model, Category, Charger, Not Openline, or Esim only triggers appraisal calculation. **Appraisal Value** is read-only in the normal form.

Example only: a condition value of PHP 10,000 becomes PHP 9,700 without a charger when the deduction applies. If it is also Not Openline, PHP 9,700 × 85% = PHP 8,245, rounded to PHP 8,200.

The reviewed script does not increase appraisal directly when RAM, storage, or battery-health values change. Accurate model and condition selection still matter. Escalate an unexpected, zero, negative, or missing appraisal instead of treating it as an approved offer.

**[Screenshot S09: The corresponding accepted Models record and item Appraisal Value; show an approved demonstration of charger/network adjustments.]**

### Step 5: Apply Apple-specific checks

For Apple cellphones, **Esim only** becomes available. Checking it removes Maximum from the condition options and changes an existing Maximum selection to Minimum. It opens the **eSIM-only iPhone – Appraisal Codigo** reference image. The server also rejects Esim only on a non-Apple cellphone/non-cellphone and converts Maximum to Minimum when Esim only is selected.

The code does not apply a separate numeric eSIM deduction beyond the condition/appraisal logic. Use the displayed guide and approved inspection criteria.

For Apple cellphones and tablets, record **BH% in 3utools** and **BH% in Device Settings**. When both are populated and their absolute difference is at least five percentage points, the system displays **“Battery health discrepancy reached 5%, item must be rejected.”**

This is a warning message in the reviewed browser script, not a server-enforced rejection. **Proposed procedure—confirm:** stop acceptance and refer the item for rejection/review when this warning appears. Never interpret successful saving as clearance of the warning.

**[Screenshot S10: Esim only controls and the appraisal guide.]**

**[Screenshot S11: Battery-health fields and the discrepancy message.]**

### Step 6: Select the assistant after encoding

Fill Brand, Model, Model Number/Model Name, and Color before selecting **Assistant Appraiser**. Otherwise the browser clears the assistant selection and asks you to complete those fields.

The dropdown includes users with the listed role profiles: Appraiser, Senior Appraiser, Junior Appraiser, Operations Supervisor, Appraiser/Cashier, Cashier, Vault Custodian, Operations Manager, and Area Manager. This confirms that a Cashier can be selected; the filter is by role profile, not proof of today's operational assignment.

After selection, the system asks the assistant to verify the encoded information against the actual gadget and click Save once confirmed. The browser prevents saving without an assistant. After the first save, only Administrator can change Assistant Appraiser under the server check.

**Proposed procedure—confirm:** the named assistant personally checks the gadget and the entry before saving. The reviewed NJ code does not require a distinct assistant login or enforce that main and assistant are different users; do not describe it as electronic dual approval.

### Step 7: Save and return to the ticket

After the physical check, save the item and return to the originating pawn ticket. Select the saved Item No if it was not inserted automatically. Type, Brand, Model, Model Number, Appraisal Value, and Main Appraiser are fetched into the ticket row.

**Do not casually edit an item linked to an existing loan.** Saving an existing item can reject/cancel its most recently modified linked Active or Expired pawn ticket and create a submitted amendment. Corrections belong with an authorized reviewer; see Page 10.

## Page 4 — Complete the loan, print, and store the item

### Step 1: Check the principal and net proceeds

When the row appraisal changes, the form sets **Desired Principal** to the total row appraisal. Before the first save, it can be reduced to the agreed principal. The browser checks that it is positive and does not exceed the total appraisal.

The new-loan calculations are:

| Amount | Calculation |
| --- | --- |
| Interest | Desired Principal × Gadget Interest Rate ÷ 100. |
| Net Proceeds | Desired Principal − Interest. |
| Interest rate used | The Gadget Interest Rate used by the form. |

Example only: with an agreed principal of PHP 10,000 and a configured rate of 7%, Interest is PHP 700 and Net Proceeds is PHP 9,300. The checked-in rate default is 7%; inspect the live setting before using any example as a quotation.

Confirm the customer, item, condition, accessories, appraisers, dates, branch, principal, interest, and net proceeds before saving. The system makes customer selection, item table, and principal read-only on a saved draft in the normal form.

### Step 2: Save and complete the authorized approval/submission

Save the ticket. Resolve any duplicate-name, appraisal, or required-field message before continuing. Pawn ticket names are checked across Jewelry and Non-Jewelry tickets, so a B-series conflict can originate in either document type.

Complete the live site's authorized submission/approval action. **Live configuration—confirm:** the exact action names, intermediate states, approver roles, and when the ticket becomes Active are not fully exported in this repository. A saved draft is not proof that the loan has been submitted.

On submission, the application creates a **Non Jewelry Batch** if that Inventory Tracking No does not already exist and copies the ticket's item rows into it. The branch inventory counter advances and the item counter resets through the batch controller.

### Step 3: Print and verify

Open the ticket's print view and select the branch-approved format. Checked-in formats include **NCB-NJ**, **NCB-NJ ( GTC )**, and **Inventory Stub Non Jewelry**. Confirm the live format names, branch selection, paper, alignment, and required number of copies.

Compare the printed customer, loan dates, principal, interest, net proceeds, gadget description, and accessories with the saved document. The ticket format also depends on customer address/contact records. Missing data or an incorrect date layout must be resolved before issuing the printout.

**Printing checkpoint:** the checked-in NCB NJ template has fixed rate/term text that may not match arbitrary settings. The review register describes this limitation. If the displayed loan terms and printed text differ, stop and escalate.

**[Screenshot S12: Submitted ticket and print preview of the branch-approved pawn ticket and inventory stub.]**

### Step 4: Complete cash and custody handover

**Proposed procedure—confirm:** explain the agreed principal, deducted interest, net proceeds, maturity, expiry, and payment options to the customer; obtain the required signatures; release only the approved net proceeds after the required approval and cash checks; then label/package the gadget and accessories using the Inventory Tracking No and Item No and hand them to the custodian against the inventory stub.

The inventory stub contains main/assisting appraiser signature lines. The source does not establish the exact customer-signature, cash-release, storage-location, or physical handover procedure. Confirm these before publishing them as mandatory company policy.

## Page 5 — Renew or pay an existing loan

### Common receipt entry sequence

1. Open **Pawnshop Management → New Provisional Receipt**.
2. Verify Branch and **Date Issued**, which defaults to today.
3. Select **Transaction Type** first. The form then reveals **Document Type**.
4. Select **Pawn Ticket Non Jewelry** as Document Type.
5. Select **Pawn Ticket No**. For ordinary loan transactions, the selector uses the current branch and states Active, Returned, or Expired. This filter does not by itself establish permission to accept an expired loan.
6. Verify the fetched Pawner Name, Inventory Tracking No, Principal Amount, dates, Monthly Interest, and Items. Transaction type, document type, and ticket selection are locked as the selection flow progresses. If you chose the wrong transaction, abandon the unsaved entry and start a fresh correct form.
7. Wait for the computation to finish. Review the **Computation** message and the final Total Amount. Submitted prior Interest Payment and Amortization receipts for that ticket are used for the displayed payment history.
8. Select Mode of Payment and complete the applicable details. Verify receipt of funds through the approved process, save, and complete the authorized submission action.
9. Reopen/check the receipt and related ticket to verify the expected result before releasing documents or property.

**[Screenshot S13: PR selection order and populated NJ receipt.]**

**[Screenshot S14: Computation message and final payment breakdown.]**

### Renewal

Select **Renewal** when extending the loan without an additional principal reduction. The system calculates accrued interest, shows advance interest, deducts recorded prior interest payments in the total, and proposes the next B-series **New Pawn Ticket No**.

On successful submission of a non-amended renewal PR, the server creates and submits a new NJ pawn ticket. Its Date Loan Granted is the receipt's Date Issued; maturity and expiry use the current configured periods. It retains the customer and inventory links, records **Old Pawn Ticket** and **Created by PR**, and ordinarily retains the existing principal, interest, net proceeds, and stored interest rate. The old ticket becomes **Renewed**.

Verify all three links: the PR's new ticket number, the new ticket's old ticket number, and the new ticket's Created by PR. Print the new ticket using the approved procedure. A renewal ticket's Net Proceeds field is not evidence that another cash loan should be released.

If creation/submission of the new ticket fails, the PR shows **Pawn Ticket Creation Failed**. Do not tell the customer renewal is complete until the receipt and new ticket are verified.

### Renewal w/ Amortization

Select **Renewal w/ Amortization** when renewing and reducing principal at the same time. Enter **(+) Additional Amortization**, which must be positive in the browser validation.

The form recalculates advance interest on the reduced principal using the ticket's stored NJ interest rate, with a legacy 7% fallback in the described missing/zero-rate case. On submission, the new principal is the old principal minus this additional amortization; the new ticket's interest is the PR's advance interest. Dates and links follow the renewal process.

**Proposed procedure—confirm:** keep the reduction below the outstanding principal for a renewal; use the approved redemption process for full payoff. The reviewed validation does not consistently enforce an upper bound, so check the result rather than relying on the field to reject an overpayment.

### Amortization without renewal

Select **Amortization** for a principal-only reduction under the approved timing policy. Enter Additional Amortization and check Total Amount. A successful non-amended PR directly reduces the existing ticket's principal and recalculates its interest and net proceeds; it does not create a new pawn ticket or change the loan dates.

The displayed **Total Amortizations** is historical information. The ticket's current Principal Amount has already been reduced by submitted amortizations; do not subtract that history a second time when quoting a payoff.

**Boundary requiring confirmation:** the browser message says amortization is not allowed “on or after” maturity, but its condition only checks dates after maturity. The server controller does not repeat that general date restriction. Until policy is confirmed, refer maturity-day cases to the authorized reviewer.

### Interest Payment

Select **Interest Payment** only where the approved process permits it. Enter **Interest to pay (Input number of Months)**; the form calculates Total Amount as that quantity × Monthly Interest. Verify the result and payment mode before submission.

The reviewed PR submission code does not create a new ticket or move maturity/expiry dates for an Interest Payment. Do not describe this transaction as a renewal. Its browser timing logic prevents it on or before maturity, although the displayed message says “before.” Confirm whether this option is used for NJ loans and its exact allowed timing.

### Payment modes

| Mode | Details to verify |
| --- | --- |
| Cash | Receipt total and cash actually collected. |
| Bank Transfer | Bank selection and confirmation that the transfer was received. |
| GCash | Gcash Reference# and confirmed receipt of funds. |
| Cash & GCash | Cash + Gcash must equal Total Amount; Gcash Reference# is required by the form. |
| Cash & Bank Transfer | Cash + Bank Payment must equal Total Amount; select Bank. |
| GCash & Bank Transfer | Gcash + Bank Payment must equal Total Amount; select Bank and enter Gcash Reference#. |

The bank options in the form are BPI, BDO, and East West. Changing payment mode clears the split amounts, so recheck the breakdown afterward. The source records payment information; it does not establish automatic confirmation of actual bank/e-wallet settlement.

## Page 6 — Redeem and release the gadget

1. Use the common PR sequence and choose **Redemption → Pawn Ticket Non Jewelry → Pawn Ticket No**.
2. Verify that this is the customer's current loan, not an older Renewed or Rejected ticket.
3. Check the current principal, accrued interest, prior interest payments, and any short-term discount. Let the calculation complete before quoting the amount.
4. Select the correct payment mode, fill required references/breakdowns, and verify payment.
5. Save and complete the authorized submission. The PR server marks the ticket **Redeemed**, records its change-status date, and marks the linked NJ items **Redeemed**.
6. Verify the saved receipt, ticket, and item identifiers before the physical release.

The Branch's currently registered **Vault Custodian is prohibited from creating a Redemption PR**. This is enforced in the browser and on the server when the PR is new. Use the properly authorized transacting user; custody duties and receipt entry are separated by this check.

**Proposed procedure—confirm:** the custodian retrieves the matching item, the releasing staff and customer verify its identity, condition, and accessories against the records, the customer acknowledges receipt, and staff retain the required evidence. Confirm the policy for representatives, lost tickets, disputed identity, or missing accessories. These exceptions are not established in the reviewed code.

Do not assume a batch status has also changed just because the PR succeeded: the direct redemption path updates the ticket and items, while batch propagation differs across update paths. An inconsistent batch requires review, not a second redemption.

**[Screenshot S15: Submitted Redemption PR, Redeemed ticket, and matching item record.]**

## Page 7 — Monitor maturity, expiry, and customer reminders

Open **Gadget Tracker** in the workspace. Its underlying report is named **NJ End of the Day Repor**. Select **Active** or **Expired** in the work flow filter. Privileged users have a branch selector; ordinary branch users use the IP-derived branch in this report.

Review ticket number, customer, contact number, inventory number, item description, principal, loan/maturity/expiry dates, status, comments, and the two texted flags. Correct source-record problems through the authorized process rather than editing a report output.

The 03:00 cron job selects Active NJ tickets whose expiry date equals the application's current date, marks them **Expired**, marks their items **Collected**, and marks the batch **Expired**. This happens on the expiry date, not automatically after the close of that business day. The job's schedule and deployment timezone must be checked in the live system. Missed past expiry dates are not selected by this equality-based job on a later day.

**Collected is a system state, not proof of a physical collection.** Physically reconcile the items and use the approved transfer process before moving them.

At 09:00, the daily SMS job considers Active/Expired tickets with maturity or expiry from today through two days ahead and an unset corresponding texted flag. Manual **Maturity Date SMS** or **Expiry Date SMS** buttons are exposed to the relevant custodian/Administrator when the date is today or within the preceding five days and the flag is unset.

Use **SMS Log** to inspect the request and delivery result. The flags are updated by delivered-status processing; a sent-request message is not the same as confirmed delivery. Customer mobile details and branch contact details must be maintained. When maturity and expiry are the same date, both reminder purposes may qualify; confirm the desired messaging policy.

**[Screenshot S16: Gadget Tracker with Active/Expired filters.]**

**[Screenshot S17: SMS controls and a sample SMS Log with request versus delivery status.]**

## Page 8 — Pull out expired items and transfer custody

Use **Transfer Tracker** from the authorized custodian workspace or the document search. The server checks custodian access for the origin, with the implemented system-manager exception. The actual live receiving transition and Subastado permissions must be confirmed.

1. Create a new Transfer Tracker and verify Date of Transfer, Origin, Released By, and Transfer No.
2. Select **Item type: Non Jewelry Items**.
3. Select **Transfer Type: Pull out of Expired Sangla**. For normal branch users, the form sets Destination to **Subastado NJ**.
4. Select the approved **From Date Loan Granted** and **To Date Loan Granted** when using automatic population. These are loan-granted dates, not expiry dates.
5. Check each NJ item, Last Pawn Ticket, principal, and accessories against the physical items and approved pullout list. The automatic date-range query includes submitted Active, Expired, and Returned tickets. Its results are not an eligibility approval to pull out every row.
6. Select **Witnessed By** and **Rover**. The form prompts for their password confirmation. The named person should perform their own confirmation; do not record passwords in the manual or handover paperwork. Both fields are required before submission.
7. Review/print the transfer document using the approved live workflow, save, and submit through the authorized action. Confirm the resulting **For Receiving** state.
8. In For Receiving, NJ items become **In Transit**. For this pullout type, the linked tickets become **Pulled Out** and receive a change-status date.
9. At the destination, the authorized receiver checks the actual items and completes the live receiving action. When the submitted tracker reaches **Complete**, the code updates the NJ item location, principal upon pullout, received date, and state to **Unprocessed**. It also records the tracker's Received By and Date Received.

**Proposed procedure—confirm:** signatures, packaging, transportation, discrepancy handling, and the receiver's approval should be completed against the physical item count. Never mark a transfer complete merely to clear the pending list.

For **Transfer of Display Items**, choose the correct destination and items at the origin location. On completion, NJ items move to the destination and return to For Sale, or Reserved when their saved pre-transfer state was Reserved. A transfer is not a sale.

**[Screenshot S18: NJ pullout form, date range, item rows, and witness/rover fields.]**

**[Screenshot S19: For Receiving and Complete transfer records with matching item location/status.]**

## Page 9 — Reappraise, reserve, sell, or place on installment

### Reappraisal at Subastado

Open the received **Non Jewelry Items** record. Verify Current Location, Date Received by Subastado, and Principal upon Pull out. For an Unprocessed item, the form exposes **Subastado Category** and **Subastado Comment** to the relevant Subastado member NJ role. Choose the observed category rather than leaving `-Select-`.

Changing between original Maximum and Subastado Defective, or original Defective and Subastado Maximum, ticks **W/ Audit Finding** and displays a discrepancy message. Other category combinations clear that checkbox in this event handler. It is not a complete automatic quality audit.

**Live configuration—confirm:** the action that authorizes For Sale, the role that sets Selling Price, and any automation filling Date Reappraised. Those transitions are not fully defined in the checked-in files. Follow the live authorized workflow and verify the resulting selling price/location/status.

### Reservation

When the configured item workflow offers **Reserve**, selecting it opens **Reserve Buyer**. Enter **Name of Customer** and optionally **Initial Comment**. After the action, the form adds a Reserved Buyers row with customer name, reservation date/time, comment, and the logged-in reserving user.

A scheduled 03:00 job returns Reserved items to **For Sale** when the latest reservation row is at least 48 hours old. This occurs at the next daily run after the threshold, not exactly at the 48th hour. Confirm the business reservation promise and any extension procedure.

**[Screenshot S20: Subastado assessment fields, Reserve Buyer dialog, and Reserved Buyers history.]**

### Outright sale and returns

The workspace links **Gadgets for Sale**. The repository includes a migration that changes its location exclusions, but the complete live report script is stored outside the exported report files. **Subastado Sales Commissions** stores buyer, receipt, payment, item, seller, delivery, and return information. The reviewed controller calculates commissions; it does not establish the complete sale-entry, inventory-Sold update, or return workflow.

**Proposed procedure—confirm:** select the approved available item, verify its location and price, record buyer and payment through the actual sales interface, confirm payment, issue the correct sales document, and verify that inventory and cash records reflect the sale before releasing the item. Confirm which application/screen performs these actions and the exact return/refund process.

Do not use **Agreement to Sell** as the assumed NJ resale form. Its checked-in implementation uses Jewelry Items and Jewelry Batch. A PR of type Others can reference Subastado Sales Commissions, but that alone does not establish a complete sales workflow or justify recording the same collection twice.

### Installment purchase

1. Open **New NJ Installment Form** in Pawnshop Management.
2. Verify Start Date and Branch, then select Customer Tracking No. The form fetches the customer's name and primary Contact mobile number.
3. Select Item No. The new-form selector offers For Sale or Reserved items at the mapped branch location.
4. Verify the fetched item specifications, accessories, Total Price, and Cost. Total Price comes from the item's Selling Price.
5. Check Due Date. The client sets 60 days for PHP 4,000–9,999, 90 days for PHP 10,000–19,999, and 120 days for PHP 20,000 or above. Below PHP 4,000 it displays a notice and clears price/down payment. Confirm how fractional-peso boundary amounts are handled before using them.
6. Complete the approved collection/approval process. Down Payment, Down Payment Receipt, Payments, Outstanding Balance, and Date Fully Paid are read-only in the exported form; their complete update mechanism was not found in its controller.
7. Verify the recorded payment and agreement before printing. The form hides its print controls when Down Payment is zero.

The embedded agreement text states: at least 25% initial deposit; at least PHP 100 for an installment payment; release after full prepayment; two days after the full-payment due date before default; a signed instruction-slip photo for remote down payments; and forfeiture of the 25% deposit with return of other payments on default. These are statements in the template, not verified automatic enforcement or newly established policy. The owner must confirm that they are current.

The **Close** workflow action calls a helper that sets the linked item to For Sale. It is not proof of full payment or automatic refund. Confirm when Close is appropriate and how collection, refund, default, item release, and Under Installment/Sold statuses are updated.

**[Screenshot S21: Installment form, price/due date, payment history, and approved agreement printout.]**

## Page 10 — Correct errors without losing the transaction trail

### Wrong entry before saving

Correct the customer, item, principal, and accessories before the first ticket save. If the selection flow has locked an incorrect PR choice, restart the unsaved receipt. Avoid creating multiple parallel new tickets from the same branch counter.

### Incorrect saved item

Refer the correction to an authorized reviewer. The item controller searches for the most recently modified linked pawn ticket. If it is Active or Expired, saving the item rejects/cancels that ticket and creates a submitted amendment using the same inventory links and preserved loan amounts. This behavior is broader than a price edit.

Verify the replacement ticket, date/amounts, receipt links where applicable, and printed documentation. Do not assume that changing the item's appraisal automatically renegotiates or changes the loan principal. Only Administrator can change Assistant Appraiser after the item is saved.

### Printing Error NJ

For an Active ticket with Date Loan Granted equal to today, designated managerial/support roles can see **Printing Error NJ**. It asks whether to transfer the ticket to the next available pawn ticket.

Use this only for the approved paper/printing-error procedure. The helper rejects/cancels the old ticket, records **Transferred to PT**, creates and submits a replacement using the next ticket number, preserves the contractual dates and amounts, and updates a matching renewal PR's new-ticket reference.

Check both old and replacement records and the associated PR. This is a document replacement, not simply a reprint. Do not repeat the action after a timeout until someone verifies which records were created.

### Change Mode of Payment

For a submitted PR dated today, the form can offer **Change Mode of Payment** to Area Manager, Operations Manager, or Support Team when no submitted CPR exists for the branch today. The dialog cancels and amends the PR; it does not merely edit a display label.

**Proposed procedure—confirm:** restrict this to the authorized correction process with supporting payment evidence. Afterward, inspect the original and amended receipt and any affected loan. Cancellation/reversal behavior is not fully established by the exported controller, particularly where an earlier PR directly changed principal or status. Do not cancel receipts as a generic way to undo a loan transaction.

**[Screenshot S22: Printing Error NJ and resulting old/new links.]**

**[Screenshot S23: Change Mode of Payment dialog and amended receipt trail.]**

## Page 11 — Reconcile cash, inventory, and custodian handover

### Cash Position Report

1. Ensure all intended daily transactions and payment corrections are complete.
2. The registered Pawnshop Cashier, or Administrator, opens **New Cash Position Report**. The server checks the branch's Pawnshop Cashier field when creating the record.
3. Wait until the report finishes loading. Verify date, branch, beginning balance, collections, loan payouts, electronic payment adjustments, and cash to/from vault.
4. Count the cash and enter the **peso amount per denomination**, not the number of pieces. The script sums the entered currency amounts directly. For example, ten PHP 1,000 bills must be entered as PHP 10,000 in 1000 Php Bills.
5. Review Total Cash, Ending Balance, and Shortage/Overage. Shortage/Overage = counted Total Cash − computed Ending Balance.
6. Resolve differences through the approved process. The browser rejects zero Total Cash; it does not establish an automatic zero-discrepancy approval requirement.
7. Save and submit only after loading and checks succeed. If new/modified transactions or changed fund-transfer totals are reported, reload and reconcile again.
8. On successful submission, the server creates the Pawnshop Transaction Log and Inventory Count. An existing Inventory Count for the same branch/date blocks submission and directs staff to IT.
9. Follow the form's reminder to refresh and print the **Pawnshop Transaction Log**. Verify it against the receipts, payout documents, and physical records.

For NJ payouts the report is designed to count original submitted loans and to avoid treating a renewal as a fresh cash disbursement. Submitted amortization history can be used to recover the original payout basis. High-volume and unusual correction cases require reconciliation; do not assume every total is immune to configuration or data problems.

**[Screenshot S24: Loaded CPR, cash denomination amounts, and shortage/overage.]**

**[Screenshot S25: Generated Transaction Log and NJ inventory count report.]**

### Inventory and custodian handover

Use the authorized **Non Jewelry Inventory**, **VC Count Report**, and **VC Turnover Lists (J, NJ, SB)** views to compare system balances with physical custody. The NJ Inventory report reads Inventory Count history; Gadget Tracker reads pawn tickets. These views answer different questions and need not use the same row grouping.

When changing the registered custodian, use **VC Turnover Checklist**. The checked-in workflow is **Draft → Submit → For Acceptance → Accept Turnover → Accepted**. The intended receiver must be entered; only that Received By user can accept. Acceptance updates the branch's registered Vault Custodian. A System Manager can reject a pending handover through the defined workflow.

**Proposed procedure—confirm:** the outgoing and incoming custodians jointly check physical cash, gadgets, documents, items in transit, reserved/under-installment stock, and exceptions before acceptance. Automatic counts do not replace a physical count. Confirm company-used item classifications and other exceptional statuses where the implementation uses inconsistent capitalization.

**[Screenshot S26: VC Turnover Checklist, NJ inventory section, Received By, and Accept Turnover action.]**

## Page 12 — Troubleshooting and daily checkpoints

| Symptom/message | Action |
| --- | --- |
| Branch missing or wrong | Stop; verify station/network and Branch IP Addressing with IT. |
| Customer disabled or identity mismatch | Select the correct authorized Customer or request record review. |
| Missing ID/contact/birthday | Resolve the Customer–Contact link and source data; do not invent a birthday to make a computation run. |
| Correct model not offered | Request an accepted master record; do not choose another model. |
| Assistant Appraiser cleared | Complete Brand, Model, Model Number/Name, and Color first. |
| Battery discrepancy warning | Refer for rejection/review under the confirmed inspection procedure. |
| Desired Principal exceeds total or is zero | Correct the agreed positive principal within the reviewed appraisal. |
| Duplicate pawn ticket number | Refresh and have counters/parallel entries checked; do not manually reuse a number. |
| Payment breakdown does not match total | Re-enter the split after the final calculation/payment-mode selection. |
| Unexpected or negative interest/total | Stop the quotation and obtain calculation review. |
| Vault Custodian redemption restriction | Use the authorized redemption transactor; retain custody separation. |
| Pawn Ticket Creation Failed / Document Modified | Refresh and inspect receipt/new-ticket existence before retrying. |
| Expired item still appears Active after a missed job | Ask IT to reconcile; the scheduled equality filter does not automatically catch up all past dates. |
| Printed term/rate differs from screen | Stop issuance; verify the approved print format and settings. |
| Transfer list contains an apparently ineligible ticket | Verify contractual dates and authorization; the date-range population includes Active/Returned states. |
| CPR says transactions changed | Reload and reconcile again before submission. |
| Duplicate Inventory Count blocks CPR | Refer to IT; do not delete a record merely to bypass the check. |

Before each new loan, verify identity, item condition, accessories, appraisers, dates, and amounts. Before a payment, verify the current ticket, transaction type, computation, and received funds. Before releasing or moving an item, verify its exact Item No and custody documentation. Before closing the day, reconcile receipts, payouts, cash, transaction log, and physical inventory.

These final physical-control steps remain proposed operating procedures until confirmed by the owner.
