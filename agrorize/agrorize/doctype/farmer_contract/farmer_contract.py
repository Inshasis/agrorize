# Copyright (c) 2026, Inshasis and contributors
# For license information, please see license.txt

"""
Farmer Contract DocType Controller
Handles all business logic for farmer contract management in AgroRize
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_days, date_diff, nowdate, cint


class FarmerContract(Document):
	"""
	Main controller class for Farmer Contract DocType
	Manages contract lifecycle, validations, and business logic
	"""
	
	def validate(self):
		"""Main validation method - called every time document is saved"""
		self.validate_dates()
		self.validate_farmer_links()
		self.validate_land_area()
		self.calculate_duration()
		self.validate_crop_configuration()
		self.calculate_harvest_values()
		self.calculate_totals()
		self.set_contract_status()
	
	def before_save(self):
		"""Called before saving - generates harvest schedule if needed"""
		self.generate_harvest_schedule()
	
	def before_submit(self):
		"""Called before submitting - final validations"""
		self.validate_mandatory_fields()
		self.validate_harvest_schedule()
	
	def on_submit(self):
		"""Called after successful submission"""
		self.contract_status = "Active"
		self.db_update()
		self.create_notifications()
		self.add_comment("Comment", _("Contract submitted and activated"))
	
	def on_cancel(self):
		"""Called when contract is cancelled"""
		self.contract_status = "Terminated"
		self.db_update()
		self.add_comment("Comment", _("Contract cancelled and terminated"))
	
	# ==================== VALIDATION METHODS ====================
	
	def validate_dates(self):
		"""Validate contract dates and check for overlaps"""
		if not self.start_date or not self.end_date:
			return
			
		if getdate(self.start_date) < getdate(self.contract_date):
			frappe.throw(_("Start Date cannot be before Contract Date"))
		
		if getdate(self.end_date) <= getdate(self.start_date):
			frappe.throw(_("End Date must be after Start Date"))
		
		# Check for overlapping contracts
		if self.farmer:
			overlapping = frappe.db.sql("""
				SELECT name, start_date, end_date
				FROM `tabFarmer Contract`
				WHERE farmer = %s 
				AND name != %s
				AND docstatus = 1
				AND contract_status IN ('Active', 'Pending Approval')
				AND (
					(start_date <= %s AND end_date >= %s)
					OR (start_date <= %s AND end_date >= %s)
					OR (start_date >= %s AND end_date <= %s)
				)
			""", (self.farmer, self.name or '', 
				  self.start_date, self.start_date, 
				  self.end_date, self.end_date, 
				  self.start_date, self.end_date), as_dict=1)
			
			if overlapping:
				msg = _("Warning: Overlapping contract found - {0} ({1} to {2})").format(
					overlapping[0].name, 
					overlapping[0].start_date, 
					overlapping[0].end_date
				)
				frappe.msgprint(msg, indicator='orange', alert=True)
	
	def validate_farmer_links(self):
		"""Validate farmer has Customer and Supplier links"""
		if not self.customer or not self.supplier:
			frappe.throw(_(
				"Farmer must have both Customer and Supplier linked. "
				"Please update the Farmer master before creating a contract."
			))
	
	def validate_land_area(self):
		"""Validate contract land area against farmer's total land"""
		if self.contract_land_area and self.total_land_area:
			if flt(self.contract_land_area) > flt(self.total_land_area):
				msg = _("Warning: Contract land area ({0} {1}) exceeds farmer's total land area ({2} {3})").format(
					self.contract_land_area, 
					self.land_uom or '',
					self.total_land_area,
					self.land_uom or ''
				)
				frappe.msgprint(msg, indicator='orange', alert=True)
	
	def validate_crop_configuration(self):
		"""Validate crop configuration based on cycle type"""
		if not self.crop_cycle_type:
			return
			
		if self.crop_cycle_type == "Single Harvest":
			if not self.first_harvest_date:
				frappe.throw(_("First Harvest Date is required for Single Harvest crops"))
		
		elif self.crop_cycle_type in ["Multiple Harvest", "Continuous Harvest"]:
			if not self.harvest_cycle_days:
				frappe.throw(_("Harvest Cycle Days is required for {0}").format(self.crop_cycle_type))
			
			if not self.first_harvest_date:
				frappe.throw(_("First Harvest Date is required"))
			
			if not self.total_expected_harvests:
				frappe.throw(_("Total Expected Harvests is required"))
			
			# Validate harvest schedule fits within contract period
			if self.harvest_cycle_days and self.total_expected_harvests and self.end_date:
				total_days_needed = self.harvest_cycle_days * (self.total_expected_harvests - 1)
				contract_days = date_diff(self.end_date, self.first_harvest_date)
				
				if total_days_needed > contract_days:
					frappe.throw(_(
						"Contract period is too short for {0} harvests with {1} days cycle. "
						"Need {2} days, have {3} days."
					).format(
						self.total_expected_harvests,
						self.harvest_cycle_days,
						total_days_needed,
						contract_days
					))
	
	def validate_mandatory_fields(self):
		"""Validate mandatory fields before submission"""
		if not self.primary_product:
			frappe.throw(_("Primary Product is required"))
		
		if not self.base_price_per_unit:
			frappe.throw(_("Base Price Per Unit is required"))
	
	def validate_harvest_schedule(self):
		"""Validate harvest schedule completeness"""
		if not self.crop_harvest_schedule:
			frappe.msgprint(
				_("Warning: No harvest schedule defined. Please generate or add harvest schedule."),
				indicator='orange',
				alert=True
			)
			return
		
		# Validate total scheduled quantity matches expected quantity
		total_scheduled_qty = sum([flt(h.expected_quantity) for h in self.crop_harvest_schedule])
		variance = abs(total_scheduled_qty - flt(self.expected_total_quantity))
		
		if variance > 0.01:
			msg = _(
				"Warning: Total scheduled quantity ({0} {1}) does not match expected total quantity ({2} {3}). "
				"Variance: {4} {5}"
			).format(
				total_scheduled_qty,
				self.quantity_uom or '',
				self.expected_total_quantity,
				self.quantity_uom or '',
				variance,
				self.quantity_uom or ''
			)
			frappe.msgprint(msg, indicator='orange', alert=True)
	
	# ==================== CALCULATION METHODS ====================
	
	def calculate_duration(self):
		"""Calculate total contract duration in days"""
		if self.start_date and self.end_date:
			self.total_duration_days = date_diff(self.end_date, self.start_date)
	
	def calculate_harvest_values(self):
		"""Calculate values for each harvest in schedule"""
		if not self.crop_harvest_schedule:
			return
			
		for harvest in self.crop_harvest_schedule:
			# Set rate per unit if not set
			if not harvest.rate_per_unit and self.base_price_per_unit:
				harvest.rate_per_unit = self.base_price_per_unit
			
			# Set UOM if not set
			if not harvest.uom and self.quantity_uom:
				harvest.uom = self.quantity_uom
			
			# Calculate expected value
			harvest.expected_value = flt(harvest.expected_quantity) * flt(harvest.rate_per_unit or self.base_price_per_unit)
			
			# Calculate actual value if actual quantity exists
			if harvest.actual_quantity:
				harvest.actual_value = flt(harvest.actual_quantity) * flt(harvest.rate_per_unit or self.base_price_per_unit)
				
				# Calculate variance
				harvest.variance_quantity = flt(harvest.actual_quantity) - flt(harvest.expected_quantity)
				
				if harvest.expected_quantity:
					harvest.variance_percentage = (harvest.variance_quantity / flt(harvest.expected_quantity)) * 100
	
	def calculate_totals(self):
		"""Calculate contract totals from items and harvests"""
		total_amount = 0
		total_quantity = 0
		
		# Calculate from contract items if present
		if self.contract_items:
			for item in self.contract_items:
				item.amount = flt(item.quantity) * flt(item.rate)
				total_amount += item.amount
				total_quantity += flt(item.quantity)
		
		# If no items, calculate from primary product and expected quantity
		if not self.contract_items:
			if self.expected_total_quantity and self.base_price_per_unit:
				total_amount = flt(self.expected_total_quantity) * flt(self.base_price_per_unit)
				total_quantity = flt(self.expected_total_quantity)
		
		# Set calculated values
		self.total_contract_value = total_amount
		self.total_quantity_contracted = total_quantity
		
		# Calculate expected yield per acre
		if self.contract_land_area and total_quantity:
			self.expected_yield_per_acre = total_quantity / flt(self.contract_land_area)
	
	def set_contract_status(self):
		"""Auto-update contract status based on dates"""
		if self.docstatus == 1:
			today = getdate(nowdate())
			
			if getdate(self.end_date) < today:
				self.contract_status = "Expired"
			elif getdate(self.start_date) > today:
				self.contract_status = "Pending Approval"
			elif getdate(self.start_date) <= today <= getdate(self.end_date):
				if self.contract_status not in ["Active", "On Hold"]:
					self.contract_status = "Active"
	
	# ==================== HARVEST SCHEDULE METHODS ====================
	
	def generate_harvest_schedule(self):
		"""Auto-generate harvest schedule based on crop configuration"""
		# Only generate if crop cycle type is set and schedule is empty
		if not self.crop_cycle_type or len(self.crop_harvest_schedule) > 0:
			return
		
		if self.crop_cycle_type == "Single Harvest":
			self._generate_single_harvest()
		elif self.crop_cycle_type in ["Multiple Harvest", "Continuous Harvest"]:
			self._generate_multiple_harvest()
	
	def _generate_single_harvest(self):
		"""Generate single harvest schedule"""
		if not self.first_harvest_date or not self.expected_total_quantity:
			return
		
		self.append("crop_harvest_schedule", {
			"harvest_number": 1,
			"harvest_date": self.first_harvest_date,
			"expected_quantity": self.expected_total_quantity,
			"uom": self.quantity_uom,
			"harvest_status": "Planned",
			"rate_per_unit": self.base_price_per_unit,
			"expected_value": flt(self.expected_total_quantity) * flt(self.base_price_per_unit),
			"actual_quantity": 0
		})
	
	def _generate_multiple_harvest(self):
		"""Generate multiple harvest schedule"""
		if not self.harvest_cycle_days or not self.first_harvest_date or not self.total_expected_harvests:
			return
		
		if not self.expected_total_quantity:
			return
		
		# Calculate quantity per harvest
		qty_per_harvest = flt(self.expected_total_quantity) / flt(self.total_expected_harvests)
		current_date = getdate(self.first_harvest_date)
		
		for i in range(cint(self.total_expected_harvests)):
			# Check if harvest date is within contract period
			if self.end_date and current_date > getdate(self.end_date):
				break
			
			self.append("crop_harvest_schedule", {
				"harvest_number": i + 1,
				"harvest_date": current_date,
				"expected_quantity": qty_per_harvest,
				"uom": self.quantity_uom,
				"harvest_status": "Planned",
				"rate_per_unit": self.base_price_per_unit,
				"expected_value": qty_per_harvest * flt(self.base_price_per_unit),
				"actual_quantity": 0
			})
			
			# Add days for next harvest
			current_date = add_days(current_date, self.harvest_cycle_days)
	
	# ==================== WHITELISTED METHODS ====================
	
	@frappe.whitelist()
	def update_harvest_actual(self, harvest_number, actual_date, actual_quantity, 
							  quality_grade=None, quality_status=None, remarks=None):
		"""Update actual harvest data for a specific harvest"""
		harvest_number = cint(harvest_number)
		
		for harvest in self.crop_harvest_schedule:
			if harvest.harvest_number == harvest_number:
				harvest.actual_harvest_date = actual_date
				harvest.actual_quantity = flt(actual_quantity)
				harvest.harvest_status = "Completed"
				
				if quality_grade:
					harvest.quality_grade = quality_grade
				
				if quality_status:
					harvest.quality_status = quality_status
				else:
					harvest.quality_status = "Pending"
				
				if remarks:
					harvest.remarks = remarks
				
				# Calculate variance
				harvest.variance_quantity = flt(actual_quantity) - flt(harvest.expected_quantity)
				
				if harvest.expected_quantity:
					harvest.variance_percentage = (harvest.variance_quantity / flt(harvest.expected_quantity)) * 100
				
				# Calculate actual value
				harvest.actual_value = flt(actual_quantity) * flt(harvest.rate_per_unit or self.base_price_per_unit)
				
				# Recalculate totals
				self.calculate_totals()
				self.save()
				
				self.add_comment("Comment", _(
					"Harvest #{0} updated - Actual: {1} {2}, Variance: {3:.2f}%"
				).format(
					harvest_number,
					actual_quantity,
					self.quantity_uom,
					harvest.variance_percentage
				))
				
				return harvest.as_dict()
		
		frappe.throw(_("Harvest #{0} not found").format(harvest_number))
	
	@frappe.whitelist()
	def extend_contract(self, new_end_date, amendment_reason=None):
		"""Extend contract end date"""
		if getdate(new_end_date) <= getdate(self.end_date):
			frappe.throw(_("New End Date must be after current End Date ({0})").format(self.end_date))
		
		old_end_date = self.end_date
		self.end_date = new_end_date
		self.calculate_duration()
		
		comment_text = _("Contract extended from {0} to {1}").format(old_end_date, new_end_date)
		if amendment_reason:
			comment_text += _("<br>Reason: {0}").format(amendment_reason)
		
		self.add_comment("Comment", comment_text)
		self.save()
		
		frappe.msgprint(_("Contract extended successfully to {0}").format(new_end_date))
		return self
	
	@frappe.whitelist()
	def hold_contract(self, reason=None):
		"""Put contract on hold"""
		if self.contract_status != "Active":
			frappe.throw(_("Only Active contracts can be put on hold"))
		
		self.contract_status = "On Hold"
		
		comment_text = _("Contract put on hold")
		if reason:
			comment_text += _("<br>Reason: {0}").format(reason)
		
		self.add_comment("Comment", comment_text)
		self.save()
		
		frappe.msgprint(_("Contract has been put on hold"))
		return self
	
	@frappe.whitelist()
	def activate_contract(self):
		"""Activate a held contract"""
		if self.contract_status != "On Hold":
			frappe.throw(_("Only contracts On Hold can be activated"))
		
		self.contract_status = "Active"
		self.add_comment("Comment", _("Contract reactivated"))
		self.save()
		
		frappe.msgprint(_("Contract has been activated"))
		return self
	
	@frappe.whitelist()
	def get_harvest_performance(self):
		"""Get harvest performance metrics"""
		total_planned = 0
		total_actual = 0
		completed_harvests = 0
		pending_harvests = 0
		delayed_harvests = 0
		
		today = getdate(nowdate())
		
		for harvest in self.crop_harvest_schedule:
			total_planned += flt(harvest.expected_quantity)
			total_actual += flt(harvest.actual_quantity)
			
			if harvest.harvest_status == "Completed":
				completed_harvests += 1
			elif harvest.harvest_status == "Delayed":
				delayed_harvests += 1
			elif getdate(harvest.harvest_date) < today and harvest.harvest_status == "Planned":
				delayed_harvests += 1
				pending_harvests += 1
			else:
				pending_harvests += 1
		
		total_harvests = len(self.crop_harvest_schedule)
		fulfillment_pct = (total_actual / total_planned * 100) if total_planned else 0
		on_time_pct = (completed_harvests / total_harvests * 100) if total_harvests else 0
		
		return {
			"total_planned_quantity": total_planned,
			"total_actual_quantity": total_actual,
			"fulfillment_percentage": fulfillment_pct,
			"total_harvests": total_harvests,
			"completed_harvests": completed_harvests,
			"pending_harvests": pending_harvests,
			"delayed_harvests": delayed_harvests,
			"on_time_percentage": on_time_pct
		}
	
	@frappe.whitelist()
	def get_upcoming_harvests(self, days=30):
		"""Get upcoming harvests within specified days"""
		today = getdate(nowdate())
		end_date = add_days(today, cint(days))
		
		upcoming = []
		
		for harvest in self.crop_harvest_schedule:
			if (harvest.harvest_status in ["Planned", "In Progress"] and 
				today <= getdate(harvest.harvest_date) <= end_date):
				
				upcoming.append({
					"harvest_number": harvest.harvest_number,
					"harvest_date": harvest.harvest_date,
					"expected_quantity": harvest.expected_quantity,
					"uom": harvest.uom,
					"days_until_harvest": date_diff(harvest.harvest_date, today)
				})
		
		return upcoming
	
	@frappe.whitelist()
	def regenerate_harvest_schedule(self):
		"""Regenerate harvest schedule - clears and generates new"""
		if self.docstatus == 1:
			frappe.throw(_("Cannot regenerate schedule for submitted contracts"))
		
		self.crop_harvest_schedule = []
		self.generate_harvest_schedule()
		self.calculate_harvest_values()
		self.calculate_totals()
		self.save()
		
		frappe.msgprint(_("Harvest schedule regenerated successfully"))
		return self
	
	def create_notifications(self):
		"""Send notifications when contract is activated"""
		if self.email:
			subject = _("Contract Activated - {0}").format(self.name)
			
			message = _("""
				<p>Dear {0},</p>
				<p>Your contract <strong>{1}</strong> has been activated successfully.</p>
				<h4>Contract Details:</h4>
				<ul>
					<li>Contract Period: {2} to {3}</li>
					<li>Product: {4}</li>
					<li>Expected Quantity: {5} {6}</li>
					<li>Contract Value: {7}</li>
					<li>Total Harvests: {8}</li>
				</ul>
				<p>Thank you for your partnership!</p>
			""").format(
				self.farmer_name,
				self.name,
				self.start_date,
				self.end_date,
				self.primary_product,
				self.expected_total_quantity,
				self.quantity_uom,
				frappe.utils.fmt_money(self.total_contract_value, 
									   currency=frappe.defaults.get_global_default("currency")),
				len(self.crop_harvest_schedule)
			)
			
			frappe.sendmail(
				recipients=[self.email],
				subject=subject,
				message=message
			)


# ==================== SCHEDULED TASKS ====================

def auto_update_contract_status():
	"""Scheduled task to auto-update contract statuses - Run daily"""
	contracts = frappe.get_all("Farmer Contract",
							   filters={
								   "docstatus": 1,
								   "contract_status": ["in", ["Active", "Pending Approval"]]
							   },
							   fields=["name", "start_date", "end_date", "contract_status"])
	
	today = getdate(nowdate())
	updated_count = 0
	
	for contract in contracts:
		doc = frappe.get_doc("Farmer Contract", contract.name)
		old_status = doc.contract_status
		doc.set_contract_status()
		
		if doc.contract_status != old_status:
			doc.db_set('contract_status', doc.contract_status, update_modified=False)
			doc.add_comment("Comment", _("Status auto-updated from {0} to {1}").format(
				old_status, doc.contract_status
			))
			updated_count += 1
			
			# Send expiry notification
			if doc.contract_status == "Expired" and doc.email:
				subject = _("Contract Expired - {0}").format(doc.name)
				message = _("""
					<p>Dear {0},</p>
					<p>Your contract <strong>{1}</strong> has expired as of {2}.</p>
					<p>Please contact us if you wish to renew the contract.</p>
				""").format(doc.farmer_name, doc.name, doc.end_date)
				
				frappe.sendmail(
					recipients=[doc.email],
					subject=subject,
					message=message
				)
	
	if updated_count > 0:
		frappe.logger().info(f"Auto-updated {updated_count} contract statuses")


def send_harvest_reminders():
	"""Send reminders for upcoming harvests - Run daily"""
	reminder_days = 7
	target_date = add_days(nowdate(), reminder_days)
	
	contracts = frappe.get_all("Farmer Contract",
							   filters={"docstatus": 1, "contract_status": "Active"},
							   fields=["name", "farmer_name", "email", "mobile_no"])
	
	sent_count = 0
	
	for contract in contracts:
		doc = frappe.get_doc("Farmer Contract", contract.name)
		
		for harvest in doc.crop_harvest_schedule:
			if (harvest.harvest_status == "Planned" and 
				getdate(harvest.harvest_date) == target_date):
				
				if doc.email:
					subject = _("Harvest Reminder - {0}").format(doc.name)
					message = _("""
						<p>Dear {0},</p>
						<p>This is a reminder that <strong>Harvest #{1}</strong> is scheduled for {2}.</p>
						<p><strong>Expected Quantity:</strong> {3} {4}</p>
						<p>Please prepare accordingly.</p>
					""").format(
						doc.farmer_name,
						harvest.harvest_number,
						harvest.harvest_date,
						harvest.expected_quantity,
						harvest.uom
					)
					
					frappe.sendmail(
						recipients=[doc.email],
						subject=subject,
						message=message
					)
					sent_count += 1
	
	if sent_count > 0:
		frappe.logger().info(f"Sent {sent_count} harvest reminders")


def mark_delayed_harvests():
	"""Mark harvests as delayed if past due date - Run daily"""
	today = getdate(nowdate())
	
	contracts = frappe.get_all("Farmer Contract",
							   filters={"docstatus": 1, "contract_status": "Active"},
							   fields=["name"])
	
	updated_count = 0
	
	for contract in contracts:
		doc = frappe.get_doc("Farmer Contract", contract.name)
		modified = False
		
		for harvest in doc.crop_harvest_schedule:
			if (harvest.harvest_status == "Planned" and 
				getdate(harvest.harvest_date) < today):
				
				harvest.harvest_status = "Delayed"
				modified = True
		
		if modified:
			doc.save(ignore_permissions=True)
			doc.add_comment("Comment", _("Auto-marked delayed harvests"))
			updated_count += 1
	
	if updated_count > 0:
		frappe.logger().info(f"Marked delayed harvests in {updated_count} contracts")


# ==================== UTILITY FUNCTIONS ====================

@frappe.whitelist()
def get_contract_summary(contract_name):
	"""Get contract summary for dashboard/reports"""
	doc = frappe.get_doc("Farmer Contract", contract_name)
	performance = doc.get_harvest_performance()
	days_remaining = date_diff(doc.end_date, nowdate())
	
	return {
		"contract": doc.name,
		"farmer": doc.farmer_name,
		"farmer_code": doc.farmer_code,
		"product": doc.primary_product,
		"status": doc.contract_status,
		"start_date": doc.start_date,
		"end_date": doc.end_date,
		"days_remaining": days_remaining,
		"total_value": doc.total_contract_value,
		"expected_quantity": doc.expected_total_quantity,
		"land_area": doc.contract_land_area,
		"land_uom": doc.land_uom,
		"yield_per_acre": doc.expected_yield_per_acre,
		"performance": performance
	}
