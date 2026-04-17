# Copyright (c) 2026, Inshasis and contributors
# For license information, please see license.txt

"""
Farmer Contract DocType Controller
Final production version with end_harvest_date calculation
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_days, date_diff, nowdate, cint


class FarmerContract(Document):
	"""
	Farmer Contract - Auto-calculates on every save
	Validates harvest_cycle_days based on harvest_frequency
	Auto-sets end_harvest_date to last harvest date
	"""
	
	# Harvest frequency mapping (max days allowed)
	FREQUENCY_DAYS = {
		"Weekly": 7,
		"Bi-Weekly": 15,
		"Monthly": 31,
		"Quarterly": 93,
		"Half Yearly": 186,
		"Yearly": 365
	}
	
	def validate(self):
		"""Called every time document is saved"""
		self.validate_farmer_links()
		self.validate_land_area()
		self.validate_duplicate_contract()
		self.validate_crop_configuration()
		self.validate_harvest_frequency()
		self.calculate_totals()
		self.regenerate_harvest_schedule_on_save()
		self.set_end_harvest_date()
	
	def before_submit(self):
		"""Final validations before submission"""
		self.validate_mandatory_fields()
		self.validate_harvest_schedule()
	
	def on_submit(self):
		"""Called after submission"""
		self.status = "Active"
		self.db_update()
		self.add_comment("Comment", _("Contract activated"))
	
	def on_cancel(self):
		"""Called when cancelled"""
		self.status = "Terminated"
		self.db_update()
		self.add_comment("Comment", _("Contract cancelled"))
	
	# ==================== VALIDATIONS ====================
	
	def validate_farmer_links(self):
		"""Validate farmer has Customer and Supplier"""
		if not self.customer or not self.supplier:
			frappe.throw(_("Farmer must have Customer and Supplier linked"))
	
	def validate_land_area(self):
		"""Validate land area"""
		if self.contract_land_area and self.total_land_area:
			if flt(self.contract_land_area) > flt(self.total_land_area):
				pass  # Silent validation, no popup warning
	
	def validate_duplicate_contract(self):
		"""
		Prevent duplicate active contracts for same farmer and product
		Only one active contract allowed per farmer-product combination
		"""
		if not self.farmer or not self.product:
			return
		
		# Check for existing active contracts
		filters = {
			'farmer': self.farmer,
			'product': self.product,
			'status': ['in', ['Active', 'Pending Approval']],
			'docstatus': ['!=', 2]  # Exclude cancelled
		}
		
		# Exclude current document if updating
		if not self.is_new():
			filters['name'] = ['!=', self.name]
		
		existing = frappe.get_all(
			'Farmer Contract',
			filters=filters,
			fields=['name', 'status', 'contract_date']
		)
		
		if existing:
			existing_contract = existing[0]
			frappe.throw(_(
				"Active contract already exists for Farmer <strong>{0}</strong> and Product <strong>{1}</strong>.<br><br>"
				"Existing Contract: <strong>{2}</strong><br>"
				"Status: <strong>{3}</strong><br>"
				"Date: <strong>{4}</strong><br><br>"
				"Please complete or terminate the existing contract before creating a new one."
			).format(
				self.farmer_name or self.farmer,
				self.product,
				existing_contract.name,
				existing_contract.status,
				existing_contract.contract_date
			), title=_("Duplicate Contract Not Allowed"))
	
	def validate_crop_configuration(self):
		"""Validate crop settings"""
		if not self.crop_cycle_type:
			return
			
		if self.crop_cycle_type == "Single Harvest":
			if not self.first_harvest_date:
				frappe.throw(_("First Harvest Date required"))
		
		elif self.crop_cycle_type == "Continuous Harvest":
			if not self.harvest_cycle_days:
				frappe.throw(_("Harvest Cycle Days required"))
			
			if not self.first_harvest_date:
				frappe.throw(_("First Harvest Date required"))
			
			if not self.total_expected_harvests:
				frappe.throw(_("Total Expected Harvests required"))
			
			if not self.harvest_frequency:
				frappe.throw(_("Harvest Frequency required"))
	
	def validate_harvest_frequency(self):
		"""
		Validate harvest_cycle_days based on harvest_frequency
		
		Rules:
		- Weekly: max 7 days
		- Bi-Weekly: max 15 days
		- Monthly: max 31 days
		- Quarterly: max 93 days (3 months)
		- Half Yearly: max 186 days (6 months)
		- Yearly: max 365 days
		"""
		if not self.harvest_frequency or not self.harvest_cycle_days:
			return
		
		if self.crop_cycle_type != "Continuous Harvest":
			return
		
		max_days = self.FREQUENCY_DAYS.get(self.harvest_frequency)
		
		if not max_days:
			return
		
		if cint(self.harvest_cycle_days) > max_days:
			frappe.throw(_(
				"Harvest Cycle Days cannot exceed {0} days for {1} frequency"
			).format(max_days, self.harvest_frequency))
		
		if cint(self.harvest_cycle_days) < 1:
			frappe.throw(_("Harvest Cycle Days must be at least 1 day"))
	
	def validate_mandatory_fields(self):
		"""Validate mandatory fields before submission"""
		if not self.product:
			frappe.throw(_("Primary Product is required"))
		
		if not self.base_price:
			frappe.throw(_("Base Price is required"))
	
	def validate_harvest_schedule(self):
		"""Validate harvest schedule exists"""
		if not self.crop_harvest_schedule:
			pass  # Silent validation, no popup
	
	# ==================== CALCULATIONS ====================
	
	def calculate_totals(self):
		"""
		AUTO-CALCULATE on every save:
		1. total_quantity (assumes Tonne, converts to KG)
		2. total_contract_value (total_quantity * base_price)
		3. expected_yield_per_acre
		
		Example:
		- expected_total_quantity: 8.1 (Tonne)
		- total_quantity: 8100 KG (8.1 * 1000)
		- base_price: 50 per KG
		- total_contract_value: 405,000 (8100 * 50)
		- contract_land_area: 5 Acre
		- expected_yield_per_acre: 1.62 (8.1 / 5)
		"""
		# Convert Tonne to KG
		if self.expected_total_quantity:
			self.total_quantity = flt(self.expected_total_quantity) * 1000
		
		# Calculate contract value (KG * Price per KG)
		if self.total_quantity and self.base_price:
			self.total_contract_value = flt(self.total_quantity) * flt(self.base_price)
		
		# Calculate yield per acre
		if self.contract_land_area and self.expected_total_quantity:
			self.expected_yield_per_acre = flt(self.expected_total_quantity) / flt(self.contract_land_area)
	
	def set_end_harvest_date(self):
		"""
		AUTO-SET: end_harvest_date to last harvest date
		Called after harvest schedule is generated
		
		Example:
		- 6 harvests generated
		- Last harvest: 2027-11-15
		- end_harvest_date = 2027-11-15
		"""
		if not self.crop_harvest_schedule:
			self.end_harvest_date = None
			return
		
		# Get last harvest date
		last_harvest = self.crop_harvest_schedule[-1]
		self.end_harvest_date = last_harvest.harvest_date
	
	# ==================== HARVEST SCHEDULE ====================
	
	def regenerate_harvest_schedule_on_save(self):
		"""
		REGENERATE harvest schedule on EVERY SAVE
		Clears existing and creates new based on:
		- total_expected_harvests (team fills)
		- harvest_cycle_days (team fills, validated by frequency)
		- expected_total_quantity (team fills)
		"""
		if not self.crop_cycle_type:
			return
		
		# Clear existing schedule
		self.crop_harvest_schedule = []
		
		# Generate new schedule
		if self.crop_cycle_type == "Single Harvest":
			self._generate_single_harvest()
		elif self.crop_cycle_type == "Continuous Harvest":
			self._generate_continuous_harvest()
	
	def _generate_single_harvest(self):
		"""
		Generate single harvest
		All quantity in one harvest
		"""
		if not self.first_harvest_date or not self.expected_total_quantity:
			return
		
		self.append("crop_harvest_schedule", {
			"harvest_date": self.first_harvest_date,
			"expected_quantity": self.expected_total_quantity,
			"harvest_status": "Planned",
			"actual_quantity": 0
		})
	
	def _generate_continuous_harvest(self):
		"""
		Generate continuous harvests
		Divides total quantity equally across harvests
		
		Example:
		- expected_total_quantity: 8.1 Tonne
		- total_expected_harvests: 6 (team fills)
		- harvest_cycle_days: 7 (team fills - Weekly)
		- Per harvest: 8.1 / 6 = 1.35 Tonne
		- Dates: First + (7 days * harvest number)
		"""
		if not self.harvest_cycle_days or not self.first_harvest_date:
			return
		
		if not self.expected_total_quantity or not self.total_expected_harvests:
			return
		
		# Quantity per harvest
		num_harvests = cint(self.total_expected_harvests)
		qty_per_harvest = flt(self.expected_total_quantity) / num_harvests
		current_date = getdate(self.first_harvest_date)
		
		for i in range(num_harvests):
			self.append("crop_harvest_schedule", {
				"harvest_date": current_date,
				"expected_quantity": qty_per_harvest,
				"harvest_status": "Planned",
				"actual_quantity": 0
			})
			
			# Next harvest date
			current_date = add_days(current_date, self.harvest_cycle_days)
	
	# ==================== API METHODS ====================
	
	@frappe.whitelist()
	def update_harvest_actual(self, harvest_date, actual_quantity, remarks=None):
		"""
		Update actual harvest data
		
		Args:
			harvest_date: Date of harvest
			actual_quantity: Actual quantity harvested
			remarks: Optional notes
		"""
		for harvest in self.crop_harvest_schedule:
			if str(harvest.harvest_date) == str(harvest_date):
				harvest.actual_quantity = flt(actual_quantity)
				harvest.harvest_status = "Completed"
				harvest.actual_harvest_date = frappe.utils.nowdate()
				if remarks:
					harvest.remark = remarks
				
				self.save()
				
				self.add_comment("Comment", _(
					"Harvest completed on {0}: {1} Tonne"
				).format(harvest_date, actual_quantity))
				
				return harvest.as_dict()
		
		frappe.throw(_("Harvest on {0} not found").format(harvest_date))
	
	@frappe.whitelist()
	def hold_contract(self, reason=None):
		"""Put contract on hold"""
		if self.status != "Active":
			frappe.throw(_("Only Active contracts can be held"))
		
		self.status = "On Hold"
		
		comment = _("Put on hold")
		if reason:
			comment += _("<br>Reason: {0}").format(reason)
		
		self.add_comment("Comment", comment)
		self.save()
		
		return self
	
	@frappe.whitelist()
	def activate_contract(self):
		"""Activate held contract"""
		if self.status != "On Hold":
			frappe.throw(_("Only held contracts can be activated"))
		
		self.status = "Active"
		self.add_comment("Comment", _("Reactivated"))
		self.save()
		
		return self
	
	@frappe.whitelist()
	def complete_contract(self):
		"""Mark contract as completed"""
		if self.status != "Active":
			frappe.throw(_("Only Active contracts can be completed"))
		
		self.status = "Completed"
		self.add_comment("Comment", _("Contract completed"))
		self.save()
		
		return self
	
	@frappe.whitelist()
	def get_harvest_performance(self):
		"""
		Get harvest performance metrics
		
		Returns:
			dict: Performance data
		"""
		total_planned = 0
		total_actual = 0
		completed = 0
		pending = 0
		delayed = 0
		
		today = getdate(nowdate())
		
		for harvest in self.crop_harvest_schedule:
			total_planned += flt(harvest.expected_quantity)
			total_actual += flt(harvest.actual_quantity)
			
			if harvest.harvest_status == "Completed":
				completed += 1
			elif harvest.harvest_status == "Delayed":
				delayed += 1
			elif getdate(harvest.harvest_date) < today and harvest.harvest_status == "Planned":
				delayed += 1
				pending += 1
			else:
				pending += 1
		
		total = len(self.crop_harvest_schedule)
		
		return {
			"total_planned": total_planned,
			"total_actual": total_actual,
			"fulfillment_pct": (total_actual / total_planned * 100) if total_planned else 0,
			"total_harvests": total,
			"completed": completed,
			"pending": pending,
			"delayed": delayed,
			"on_time_pct": (completed / total * 100) if total else 0
		}
	
	@frappe.whitelist()
	def get_upcoming_harvests(self, days=30):
		"""Get upcoming harvests within specified days"""
		today = getdate(nowdate())
		end = add_days(today, cint(days))
		
		upcoming = []
		
		for harvest in self.crop_harvest_schedule:
			if (harvest.harvest_status in ["Planned", "In Progress"] and 
				today <= getdate(harvest.harvest_date) <= end):
				
				upcoming.append({
					"harvest_date": harvest.harvest_date,
					"expected_quantity": harvest.expected_quantity,
					"days_until": date_diff(harvest.harvest_date, today)
				})
		
		return upcoming


# ==================== SCHEDULED TASKS ====================

def mark_delayed_harvests():
	"""
	Scheduled task - Run daily
	Marks harvests as delayed if past due date
	"""
	today = getdate(nowdate())
	
	contracts = frappe.get_all(
		"Farmer Contract",
		filters={"docstatus": 1, "status": "Active"},
		fields=["name"]
	)
	
	for contract in contracts:
		doc = frappe.get_doc("Farmer Contract", contract.name)
		modified = False
		
		for harvest in doc.crop_harvest_schedule:
			if harvest.harvest_status == "Planned" and getdate(harvest.harvest_date) < today:
				harvest.harvest_status = "Delayed"
				modified = True
		
		if modified:
			doc.save(ignore_permissions=True)


# ==================== UTILITY FUNCTIONS ====================

@frappe.whitelist()
def get_contract_summary(contract_name):
	"""Get contract summary for reports/dashboard"""
	doc = frappe.get_doc("Farmer Contract", contract_name)
	perf = doc.get_harvest_performance()
	
	return {
		"contract": doc.name,
		"contract_date": doc.contract_date,
		"farmer": doc.farmer_name,
		"farmer_code": doc.farmer_code,
		"product": doc.product,
		"status": doc.status,
		"first_harvest_date": doc.first_harvest_date,
		"end_harvest_date": doc.end_harvest_date,
		"expected_qty": doc.expected_total_quantity,
		"total_qty_kg": doc.total_quantity,
		"total_value": doc.total_contract_value,
		"land_area": doc.contract_land_area,
		"yield_per_acre": doc.expected_yield_per_acre,
		"total_harvests": len(doc.crop_harvest_schedule),
		"harvest_frequency": doc.harvest_frequency,
		"harvest_cycle_days": doc.harvest_cycle_days,
		"performance": perf
	}


@frappe.whitelist()
def get_max_harvest_days(frequency):
	"""
	Get maximum allowed harvest cycle days for a frequency
	Used for frontend validation
	
	Args:
		frequency: Harvest frequency (Weekly, Bi-Weekly, etc.)
		
	Returns:
		int: Maximum days allowed
	"""
	frequency_map = {
		"Weekly": 7,
		"Bi-Weekly": 15,
		"Monthly": 31,
		"Quarterly": 93,
		"Half Yearly": 186,
		"Yearly": 365
	}
	
	return frequency_map.get(frequency, 365)
