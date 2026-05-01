# Copyright (c) 2026, Inshasis and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def create_farmer_from_lead(lead_name):
	"""
	Create Farmer from Converted Lead
	Auto-creates Customer and Supplier via hooks
	Returns: Farmer document dict
	"""
	try:
		# Get Lead
		lead = frappe.get_doc("Lead", lead_name)

		# Validate Lead status
		if lead.status != "Converted":
			frappe.throw(_("Lead must be in Converted status to create Farmer"))

		# Check if Farmer already exists by mobile (Farmer field: 'mobile')
		existing = frappe.db.get_value("Farmer", {"mobile": lead.mobile_no}, "name")
		if existing:
			frappe.throw(_("Farmer {0} already exists for this Lead").format(existing))

		# Create Farmer
		farmer = frappe.get_doc({
			"doctype": "Farmer",

			# Basic Info from Lead
			"farmer_name": lead.lead_name,
			"mobile": lead.mobile_no,          # Farmer field is 'mobile', Lead field is 'mobile_no'
			"email": lead.email_id,

			# Land Details from Lead custom fields
			"total_land_area": lead.get("custom_land_area", 0),
			"land_unit": lead.get("custom_land_unit", "Acre"),
			"postal_code": lead.get("custom_postal_code"),
			"village": lead.get("custom_village"),
			"taluka": lead.get("custom_taluka"),
			"district": lead.get("custom_district"),
			"soil_type": lead.get("custom_soil_type"),
			"irrigation_type": lead.get("custom_irrigation_type"),

			# Sales & Location
			"sales_person": lead.get("custom_sales_person"),
			"company": lead.company,
			"status": "Active",
		})

		# Insert Farmer (auto-creates Customer and Supplier via hooks)
		farmer.insert(ignore_permissions=True)
		frappe.db.commit()

		return {
			"name": farmer.name,
			"farmer_name": farmer.farmer_name,
			"customer": farmer.get("customer"),
			"supplier": farmer.get("supplier"),
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Create Farmer from Lead Error")
		frappe.throw(_("Error creating Farmer: {0}").format(str(e)))