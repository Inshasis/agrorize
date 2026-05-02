# Copyright (c) 2026, Inshasis and contributors
# For license information, please see license.txt

"""
Farmer Contract DocType Controller
Production version with Seed Booking functionality
Fixed for Frappe v15
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_days, date_diff, nowdate, cint, now_datetime
from datetime import datetime


class FarmerContract(Document):
	"""
	Farmer Contract - Auto-calculates on every save
	Supports multiple contract items
	Validates harvest_cycle_days based on harvest_frequency
	Auto-sets end_harvest_date to last harvest date
	Includes Seed Booking functionality with auto-qty from AgroRize Setting
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
		self.validate_contract_items()
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
		Prevent duplicate active contracts for same farmer and items
		Only one active contract allowed per farmer-item combination
		"""
		if not self.farmer or not self.contract_item:
			return
		
		# Get all item codes from this contract
		item_codes = [item.item_code for item in self.contract_item if item.item_code]
		
		if not item_codes:
			return
		
		# Check for existing active contracts with same items
		for item_code in item_codes:
			filters = {
				'farmer': self.farmer,
				'status': ['in', ['Active', 'Pending Approval']],
				'docstatus': ['!=', 2]  # Exclude cancelled
			}
			
			# Exclude current document if updating
			if not self.is_new():
				filters['name'] = ['!=', self.name]
			
			# Check if any active contract has this item
			existing_contracts = frappe.get_all(
				'Farmer Contract',
				filters=filters,
				fields=['name', 'status', 'contract_date']
			)
			
			for contract in existing_contracts:
				# Check if this contract has the same item
				existing_items = frappe.get_all(
					'Contract Item',
					filters={
						'parent': contract.name,
						'item_code': item_code
					},
					fields=['item_code', 'item_name']
				)
				
				if existing_items:
					frappe.throw(_(
						"Active contract already exists for Farmer <strong>{0}</strong> and Item <strong>{1}</strong>.<br><br>"
						"Existing Contract: <strong>{2}</strong><br>"
						"Status: <strong>{3}</strong><br>"
						"Date: <strong>{4}</strong><br><br>"
						"Please complete or terminate the existing contract before creating a new one."
					).format(
						self.farmer_name or self.farmer,
						item_code,
						contract.name,
						contract.status,
						contract.contract_date
					), title=_("Duplicate Contract Not Allowed"))
	
	def validate_contract_items(self):
		"""Validate contract items table"""
		if not self.contract_item:
			frappe.throw(_("At least one contract item is required"))
		
		# Check for duplicate items
		item_codes = [item.item_code for item in self.contract_item if item.item_code]
		if len(item_codes) != len(set(item_codes)):
			frappe.throw(_("Duplicate items not allowed in contract"))
	
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
		if not self.contract_item:
			frappe.throw(_("At least one Contract Item is required"))
		
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
	
	# ==================== SEED BOOKING ====================
	
	@frappe.whitelist()
	def get_seed_booking_data(self):
		"""
		Get data for Seed Booking popup.

		Quantity is auto-calculated as:
			per_acer_plant (from AgroRize Setting) x contract_land_area

		Example:
			per_acer_plant  = 22,000
			contract_land_area = 2 acres
			default_qty     = 44,000

		The calculated qty is pre-filled in the popup; the user can
		freely increase or decrease it per row before confirming.

		Returns:
			dict: Pre-filled booking data including default_qty,
			      per_acer_plant, contract_land_area, and items list.
		"""
		# --- Fetch per_acer_plant from AgroRize Setting (Single DocType) ---
		per_acer_plant = 0
		try:
			agrorize_setting = frappe.get_single("AgroRize Setting")
			per_acer_plant = flt(agrorize_setting.per_acer_plant)
		except Exception:
			# If setting not found or field missing, default to 0 (no pre-fill)
			per_acer_plant = 0

		# --- Auto-calculate default quantity ---
		# Formula: per_acer_plant x contract_land_area
		contract_land_area = flt(self.contract_land_area)
		if per_acer_plant and contract_land_area:
			default_qty = per_acer_plant * contract_land_area
		else:
			default_qty = 0

		return {
			"customer": self.customer,
			"customer_name": self.customer_name,
			"contract_date": self.contract_date,
			"per_acer_plant": per_acer_plant,
			"contract_land_area": contract_land_area,
			"default_qty": default_qty,
			"items": [
				{
					"item_code": item.item_code,
					"item_name": item.item_name,
					"item_group": item.item_group,
					"uom": item.uom or "Nos",
					"qty": default_qty,   # Pre-filled; user can override
					"rate": 0             # User must enter rate
				}
				for item in self.contract_item
			]
		}

	@frappe.whitelist()
	def create_seed_booking(self, items_data):
		"""
		Create Single Sales Order for Seed Booking with all items
		Saves Sales Order reference to contract
		
		Args:
			items_data: JSON string with format:
				[
					{
						"item_code": "TULSI-RAMA",
						"qty": 100,
						"rate": 50,
						"uom": "Nos"
					}
				]
		
		Returns:
			dict: Created Sales Order details
		"""
		import json
		
		# Parse items data
		if isinstance(items_data, str):
			items_data = json.loads(items_data)
		
		# Validate contract is submitted
		if self.docstatus != 1:
			frappe.throw(_("Contract must be submitted before creating Seed Booking"))
		
		# Validate customer
		if not self.customer:
			frappe.throw(_("Customer is required for Seed Booking"))
		
		# Check if Sales Order already created
		if self.sales_order:
			frappe.throw(_("Seed Booking already created: {0}").format(self.sales_order))
		
		# Validate at least one item
		valid_items = [item for item in items_data if item.get('item_code') and item.get('qty') and item.get('rate')]
		if not valid_items:
			frappe.throw(_("At least one item with Qty and Rate is required"))
		
		# Get company from contract
		company = self.company or frappe.defaults.get_user_default("Company")
		
		# Create Single Sales Order with all items
		sales_order = frappe.get_doc({
			"doctype": "Sales Order",
			"customer": self.customer,
			"customer_name": self.customer_name,
			"transaction_date": nowdate(),
			"delivery_date": add_days(nowdate(), 7),  # 7 days from now
			"company": company,
			"custom_is_contract": 1,  # Mark as contract-related
			"custom_farmer": self.farmer,
			"custom_farmer_contract": self.name,
			"items": []
		})
		
		# Add all items to single Sales Order
		for item_data in valid_items:
			sales_order.append("items", {
				"item_code": item_data['item_code'],
				"qty": flt(item_data['qty']),
				"rate": flt(item_data['rate']),
				"uom": item_data.get('uom') or 'Nos',
				"delivery_date": add_days(nowdate(), 7),
				"warehouse": self._get_default_warehouse(company)
			})
		
		# Save and submit Sales Order
		sales_order.insert()
		sales_order.submit()
		
		# Save Sales Order reference to contract
		frappe.db.set_value('Farmer Contract', self.name, 'sales_order', sales_order.name)
		frappe.db.commit()
		
		# Add comment
		item_summary = ", ".join([
			f"{item['item_code']} ({item['qty']} {item.get('uom', 'Nos')})"
			for item in valid_items
		])
		self.add_comment(
			"Comment",
			_("Seed Booking created: {0} - Items: {1}").format(
				'<a href="/app/sales-order/{0}">{0}</a>'.format(sales_order.name),
				item_summary
			)
		)
		
		return {
			"success": True,
			"sales_order": sales_order.name,
			"message": _("Sales Order {0} created successfully with {1} item(s)").format(
				sales_order.name,
				len(valid_items)
			)
		}
	
	def _get_default_warehouse(self, company):
		"""Get default warehouse for company"""
		warehouse = frappe.db.get_value(
			"Stock Settings",
			None,
			"default_warehouse"
		)
		
		if not warehouse:
			# Get first warehouse for company
			warehouse = frappe.db.get_value(
				"Warehouse",
				{"company": company, "disabled": 0},
				"name"
			)
		
		return warehouse
	
	def _link_sales_order(self, sales_order_name):
		"""Link sales order to contract"""
		pass
	
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


# ==================== SCHEDULED TASKS - OPTIMIZED FOR 50K+ RECORDS ====================

def mark_delayed_harvests():
	"""
	Main scheduled task - Run daily at 1:00 AM
	Queues background jobs for marking delayed harvests in batches
	
	Strategy:
	- Processes 500 contracts per job to avoid timeout
	- Runs jobs in background queue to avoid blocking
	- Suitable for 50K+ contracts over next year
	"""
	try:
		# Get count of active contracts
		total_contracts = frappe.db.count(
			'Farmer Contract',
			filters={'docstatus': 1, 'status': 'Active'}
		)
		
		if total_contracts == 0:
			frappe.logger().info("No active contracts found for delayed harvest marking")
			return
		
		# Batch size - 500 contracts per job
		batch_size = 500
		total_batches = (total_contracts // batch_size) + (1 if total_contracts % batch_size else 0)
		
		frappe.logger().info(
			f"Queueing {total_batches} background jobs to process {total_contracts} contracts "
			f"in batches of {batch_size}"
		)
		
		# Queue background jobs for each batch
		for batch_num in range(total_batches):
			offset = batch_num * batch_size
			
			frappe.enqueue(
				method='agrorize.agrorize.doctype.farmer_contract.farmer_contract.process_delayed_harvests_batch',
				queue='long',
				timeout=900,
				is_async=True,
				job_name=f'mark_delayed_harvests_batch_{batch_num}',
				offset=offset,
				limit=batch_size,
				batch_num=batch_num + 1,
				total_batches=total_batches
			)
		
		frappe.logger().info(f"Successfully queued {total_batches} batch jobs for delayed harvest marking")
		
	except Exception as e:
		frappe.logger().error(f"Error in mark_delayed_harvests scheduler: {str(e)}")
		frappe.log_error(
			message=frappe.get_traceback(),
			title="Delayed Harvest Marking - Scheduler Error"
		)


def process_delayed_harvests_batch(offset=0, limit=500, batch_num=1, total_batches=1):
	"""
	Background job to process a batch of contracts
	Called by mark_delayed_harvests() scheduler
	FIXED FOR FRAPPE V15 - Uses proper logging methods
	
	Args:
		offset: Starting position in query
		limit: Number of records to process (default: 500)
		batch_num: Current batch number (for logging)
		total_batches: Total batches to process (for logging)
	"""
	try:
		start_time = now_datetime()
		today = getdate(nowdate())
		
		# Get batch of active contracts
		contracts = frappe.db.get_all(
			'Farmer Contract',
			filters={'docstatus': 1, 'status': 'Active'},
			fields=['name'],
			limit_start=offset,
			limit_page_length=limit,
			order_by='modified desc'
		)
		
		if not contracts:
			frappe.logger().info(f"Batch {batch_num}/{total_batches}: No contracts found at offset {offset}")
			return
		
		contracts_processed = 0
		harvests_marked_delayed = 0
		errors = []
		
		# Process each contract in this batch
		for contract in contracts:
			try:
				# Use direct SQL update for better performance
				result = frappe.db.sql("""
					UPDATE `tabCrop Harvest Schedule`
					SET harvest_status = 'Delayed',
						modified = NOW(),
						modified_by = %s
					WHERE parent = %s
						AND harvest_status = 'Planned'
						AND harvest_date < %s
						AND docstatus < 2
				""", (frappe.session.user, contract.name, today))
				
				# Get row count affected
				affected_rows = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
				
				if affected_rows > 0:
					harvests_marked_delayed += affected_rows
					contracts_processed += 1
				
			except Exception as e:
				error_msg = f"Contract {contract.name}: {str(e)}"
				errors.append(error_msg)
				frappe.logger().error(f"Error processing {error_msg}")
		
		# Commit the transaction
		frappe.db.commit()
		
		end_time = now_datetime()
		duration = (end_time - start_time).total_seconds()
		
		log_message = (
			f"Batch {batch_num}/{total_batches} completed in {duration:.2f}s\n"
			f"Contracts in batch: {len(contracts)}\n"
			f"Contracts with delayed harvests: {contracts_processed}\n"
			f"Total harvests marked delayed: {harvests_marked_delayed}\n"
			f"Errors: {len(errors)}"
		)
		
		frappe.logger().info(log_message)
		
		if errors:
			frappe.log_error(
				message="\n".join(errors[:10]),
				title=f"Delayed Harvest Batch {batch_num} - Partial Errors"
			)
		
	except Exception as e:
		frappe.logger().error(f"Critical error in batch {batch_num}: {str(e)}")
		frappe.log_error(
			message=frappe.get_traceback(),
			title=f"Delayed Harvest Batch {batch_num} - Critical Error"
		)
		frappe.db.rollback()


# ==================== UTILITY FUNCTIONS ====================

@frappe.whitelist()
def get_contract_summary(contract_name):
	"""Get contract summary for reports/dashboard"""
	doc = frappe.get_doc("Farmer Contract", contract_name)
	perf = doc.get_harvest_performance()
	
	items = [
		{
			'item_code': item.item_code,
			'item_name': item.item_name,
			'item_group': item.item_group,
			'variety': item.variety
		}
		for item in doc.contract_item
	]
	
	return {
		"contract": doc.name,
		"contract_date": doc.contract_date,
		"farmer": doc.farmer_name,
		"farmer_code": doc.farmer_code,
		"items": items,
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


@frappe.whitelist()
def get_items_by_item_group(item_group):
	"""
	Get items filtered by item group
	Used for Contract Item child table filtering
	
	Args:
		item_group: Item Group name
		
	Returns:
		list: List of items with code and name
	"""
	if not item_group:
		return []
	
	items = frappe.get_all(
		'Item',
		filters={
			'item_group': item_group,
			'disabled': 0
		},
		fields=['item_code', 'item_name', 'item_group'],
		order_by='item_name asc'
	)
	
	return items