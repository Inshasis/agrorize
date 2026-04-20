# Copyright (c) 2026, Inshasis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.accounts.utils import get_balance_on
import re

class Farmer(Document):
    def after_insert(self):
        """Auto-create Customer and Supplier after Farmer is created"""
        if not self.customer:
            self.create_customer()
        
        if not self.supplier:
            self.create_supplier()
        
        # Save to update customer and supplier links
        self.save()
    
    def create_customer(self):
        """Create Customer for seed/input sales"""
        try:
            # Check if customer already exists with same name
            existing_customer = frappe.db.exists('Customer', {
                'customer_name': self.farmer_name
            })
            
            if existing_customer:
                self.customer = existing_customer
                frappe.throw(_('Existing Customer {0} linked to Farmer').format(existing_customer))
                return
            
            # Create Customer Group if not exists
            if not frappe.db.exists('Customer Group', 'Contract Farmers'):
                cg = frappe.get_doc({
                    'doctype': 'Customer Group',
                    'customer_group_name': 'Contract Farmers',
                    'parent_customer_group': 'Commercial',
                    'is_group': 0
                })
                cg.insert(ignore_permissions=True)
            
            # Create Customer
            customer = frappe.get_doc({
                'doctype': 'Customer',
                'customer_name': self.farmer_name,
                'customer_type': 'Individual',
                'customer_group': 'Contract Farmers',
                'territory': self.territory or 'India',
                'mobile_no': self.mobile,
                'email_id': self.email
            })
            
            customer.insert(ignore_permissions=True)
            self.customer = customer.name
            
            frappe.msgprint(_('Customer {0} created').format(customer.name), indicator='green')
        
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), 'Farmer Customer Creation Error')
            frappe.throw(_('Error creating Customer: {0}').format(str(e)))
    
    def create_supplier(self):
        """Create Supplier for crop purchase"""
        try:
            # Check if supplier already exists with same name
            existing_supplier = frappe.db.exists('Supplier', {
                'supplier_name': self.farmer_name
            })
            
            if existing_supplier:
                self.supplier = existing_supplier
                frappe.throw(_('Existing Supplier {0} linked to Farmer').format(existing_supplier))
                return
            
            # Create Supplier Group if not exists
            if not frappe.db.exists('Supplier Group', 'Farmer Suppliers'):
                sg = frappe.get_doc({
                    'doctype': 'Supplier Group',
                    'supplier_group_name': 'Farmer Suppliers',
                    'parent_supplier_group': 'All Supplier Groups',
                    'is_group': 0
                })
                sg.insert(ignore_permissions=True)
            
            # Create Supplier
            supplier = frappe.get_doc({
                'doctype': 'Supplier',
                'supplier_name': self.farmer_name,
                'supplier_group': 'Farmer Suppliers',
                'supplier_type': 'Individual',
                'mobile_no': self.mobile,
                'email_id': self.email
            })
            
            supplier.insert(ignore_permissions=True)
            self.supplier = supplier.name
            
            frappe.msgprint(_('Supplier {0} created').format(supplier.name), indicator='green')
        
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), 'Farmer Supplier Creation Error')
            frappe.throw(_('Error creating Supplier: {0}').format(str(e)))
    
    def validate(self):
        validate_mobile_format(self),
        validate_email_format(self),
        validate_pan_format(self),
        validate_aadhaar_format(self)


@frappe.whitelist()
def update_farmer_status(farmer, status, remark=None):
    """Update farmer status and disable/enable linked Customer and Supplier"""
    if not farmer:
        frappe.throw("Farmer is required")
    
    if status not in ['Active', 'Inactive', 'Suspended']:
        frappe.throw("Invalid status. Must be Active, Inactive, or Suspended")
    
    farmer_doc = frappe.get_doc("Farmer", farmer)
    
    # Update farmer status
    farmer_doc.status = status
    
    # Add remark to a comment/note if provided
    if remark and status in ['Inactive', 'Suspended']:
        farmer_doc.add_comment('Comment', f'Status changed to {status}. Reason: {remark}')
    
    # Determine if customer and supplier should be disabled
    should_disable = status in ['Inactive', 'Suspended']
    
    customer_disabled = False
    supplier_disabled = False
    
    # Update Customer status
    if farmer_doc.customer:
        try:
            customer = frappe.get_doc('Customer', farmer_doc.customer)
            customer.disabled = 1 if should_disable else 0
            customer.save(ignore_permissions=True)
            customer_disabled = should_disable
            
            if should_disable:
                customer.add_comment('Comment', f'Disabled due to Farmer status: {status}. {remark or ""}')
            else:
                customer.add_comment('Comment', f'Enabled due to Farmer status: {status}')
                
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), 'Customer Status Update Error')
    
    # Update Supplier status
    if farmer_doc.supplier:
        try:
            supplier = frappe.get_doc('Supplier', farmer_doc.supplier)
            supplier.disabled = 1 if should_disable else 0
            supplier.save(ignore_permissions=True)
            supplier_disabled = should_disable
            
            if should_disable:
                supplier.add_comment('Comment', f'Disabled due to Farmer status: {status}. {remark or ""}')
            else:
                supplier.add_comment('Comment', f'Enabled due to Farmer status: {status}')
                
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), 'Supplier Status Update Error')
    
    # Save farmer document
    farmer_doc.save(ignore_permissions=True)
    
    return {
        "status": status,
        "customer_disabled": customer_disabled,
        "supplier_disabled": supplier_disabled
    }


@frappe.whitelist()
def update_farmer_balance(farmer):
    """Update farmer balance from linked Customer and Supplier accounts"""
    if not farmer:
        frappe.throw("Farmer is required")

    farmer_doc = frappe.get_doc("Farmer", farmer)

    if not farmer_doc.customer and not farmer_doc.supplier:
        frappe.throw("Customer or Supplier must be linked")

    # Get balances
    customer_balance = 0.0
    supplier_balance = 0.0

    if farmer_doc.customer:
        customer_balance = get_balance_on(
            party_type="Customer",
            party=farmer_doc.customer
        ) or 0.0

    if farmer_doc.supplier:
        supplier_balance = abs(get_balance_on(
            party_type="Supplier",
            party=farmer_doc.supplier
        ) or 0.0)

    # Net Balance
    net_balance = customer_balance - supplier_balance

    # Update Farmer
    frappe.db.set_value(
        "Farmer",
        farmer,
        {
            "total_receivable": customer_balance,
            "total_payable": supplier_balance,
            "net_balance": net_balance
        }
    )

    return {
        "receivable": customer_balance,
        "payable": supplier_balance,
        "net": net_balance
    }


# Basic Detail Validation Functions
def validate_mobile_format(self):
    """Validate mobile number format"""
    if self.mobile:
        mobile = self.mobile.strip()
        
        # Remove any non-digit characters
        mobile = re.sub(r'\D', '', mobile)
        
        if len(mobile) < 10:
            frappe.throw(_('Mobile number must be at least 10 digits'))
        
        if len(mobile) > 15:
            frappe.throw(_('Mobile number cannot exceed 15 digits'))
        
        self.mobile = mobile
        return True
    return True


def validate_email_format(self):
    """Validate email address format"""
    if self.email:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, self.email):
            frappe.throw(_('Please enter a valid email address'))
    return True


def validate_pan_format(self):
    """Validate PAN number format"""
    if self.pan_number:
        pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        if not re.match(pan_pattern, self.pan_number):
            frappe.throw(_('PAN format should be: ABCDE1234F (5 letters, 4 digits, 1 letter)'))
    return True


def validate_aadhaar_format(self):
    """Validate Aadhaar number format"""
    if self.aadhaar_number:
        # Remove spaces and hyphens
        aadhaar = self.aadhaar_number.replace(' ', '').replace('-', '')
        
        if not re.match(r'^\d{12}$', aadhaar):
            frappe.throw(_('Aadhaar number must be 12 digits'))
    return True

# # Copyright (c) 2026, Inshasis and contributors
# # For license information, please see license.txt

# import frappe
# from frappe.model.document import Document
# from frappe import _
# from erpnext.accounts.utils import get_balance_on
# import re

# class Farmer(Document):
#     def after_insert(self):
#         """Auto-create Customer and Supplier after Farmer is created"""
#         if not self.customer:
#             self.create_customer()
        
#         if not self.supplier:
#             self.create_supplier()
        
#         # Save to update customer and supplier links
#         self.save()
    
#     def create_customer(self):
#         """Create Customer for seed/input sales"""
#         try:
#             # Check if customer already exists with same name
#             existing_customer = frappe.db.exists('Customer', {
#                 'customer_name': self.farmer_name
#             })
            
#             if existing_customer:
#                 self.customer = existing_customer
#                 frappe.throw(_('Existing Customer {0} linked to Farmer').format(existing_customer))
#                 return
            
#             # Create Customer Group if not exists
#             if not frappe.db.exists('Customer Group', 'Contract Farmers'):
#                 cg = frappe.get_doc({
#                     'doctype': 'Customer Group',
#                     'customer_group_name': 'Contract Farmers',
#                     'parent_customer_group': 'Commercial',
#                     'is_group': 0
#                 })
#                 cg.insert(ignore_permissions=True)
            
#             # Create Customer
#             customer = frappe.get_doc({
#                 'doctype': 'Customer',
#                 'customer_name': self.farmer_name,
#                 'customer_type': 'Individual',
#                 'customer_group': 'Contract Farmers',
#                 'territory': self.territory or 'India',
#                 'mobile_no': self.mobile,
#                 'email_id': self.email
#             })
            
#             customer.insert(ignore_permissions=True)
#             self.customer = customer.name
            
#             frappe.msgprint(_('Customer {0} created').format(customer.name), indicator='green')
        
#         except Exception as e:
#             frappe.log_error(frappe.get_traceback(), 'Farmer Customer Creation Error')
#             frappe.throw(_('Error creating Customer: {0}').format(str(e)))
    
#     def create_supplier(self):
#         """Create Supplier for crop purchase"""
#         try:
#             # Check if supplier already exists with same name
#             existing_supplier = frappe.db.exists('Supplier', {
#                 'supplier_name': self.farmer_name
#             })
            
#             if existing_supplier:
#                 self.supplier = existing_supplier
#                 frappe.throw(_('Existing Supplier {0} linked to Farmer').format(existing_supplier))
#                 return
            
#             # Create Supplier Group if not exists
#             if not frappe.db.exists('Supplier Group', 'Farmer Suppliers'):
#                 sg = frappe.get_doc({
#                     'doctype': 'Supplier Group',
#                     'supplier_group_name': 'Farmer Suppliers',
#                     'parent_supplier_group': 'All Supplier Groups',
#                     'is_group': 0
#                 })
#                 sg.insert(ignore_permissions=True)
            
#             # Create Supplier
#             supplier = frappe.get_doc({
#                 'doctype': 'Supplier',
#                 'supplier_name': self.farmer_name,
#                 'supplier_group': 'Farmer Suppliers',
#                 'supplier_type': 'Individual',
#                 'mobile_no': self.mobile,
#                 'email_id': self.email
#             })
            
#             supplier.insert(ignore_permissions=True)
#             self.supplier = supplier.name
            
#             frappe.msgprint(_('Supplier {0} created').format(supplier.name), indicator='green')
        
#         except Exception as e:
#             frappe.log_error(frappe.get_traceback(), 'Farmer Supplier Creation Error')
#             frappe.throw(_('Error creating Supplier: {0}').format(str(e)))
    
#     def validate(self):
#         validate_mobile_format(self),
#         validate_email_format(self),
#         validate_pan_format(self),
#         validate_aadhaar_format(self)


# @frappe.whitelist()
# def update_farmer_balance(farmer):
#     """Update farmer balance from linked Customer and Supplier accounts"""
#     if not farmer:
#         frappe.throw("Farmer is required")

#     farmer_doc = frappe.get_doc("Farmer", farmer)

#     if not farmer_doc.customer and not farmer_doc.supplier:
#         frappe.throw("Customer or Supplier must be linked")

#     # Get balances
#     customer_balance = 0.0
#     supplier_balance = 0.0

#     if farmer_doc.customer:
#         customer_balance = get_balance_on(
#             party_type="Customer",
#             party=farmer_doc.customer
#         ) or 0.0

#     if farmer_doc.supplier:
#         supplier_balance = abs(get_balance_on(
#             party_type="Supplier",
#             party=farmer_doc.supplier
#         ) or 0.0)

#     # Net Balance
#     net_balance = customer_balance - supplier_balance

#     # Update Farmer
#     frappe.db.set_value(
#         "Farmer",
#         farmer,
#         {
#             "total_receivable": customer_balance,
#             "total_payable": supplier_balance,
#             "net_balance": net_balance
#         }
#     )

#     return {
#         "receivable": customer_balance,
#         "payable": supplier_balance,
#         "net": net_balance
#     }


# # Basic Detail Validation Functions
# def validate_mobile_format(self):
#     """Validate mobile number format"""
#     if self.mobile:
#         mobile = self.mobile.strip()
        
#         # Remove any non-digit characters
#         mobile = re.sub(r'\D', '', mobile)
        
#         if len(mobile) < 10:
#             frappe.throw(_('Mobile number must be at least 10 digits'))
        
#         if len(mobile) > 15:
#             frappe.throw(_('Mobile number cannot exceed 15 digits'))
        
#         self.mobile = mobile
#         return True
#     return True


# def validate_email_format(self):
#     """Validate email address format"""
#     if self.email:
#         email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
#         if not re.match(email_pattern, self.email):
#             frappe.throw(_('Please enter a valid email address'))
#     return True


# def validate_pan_format(self):
#     """Validate PAN number format"""
#     if self.pan_number:
#         pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
#         if not re.match(pan_pattern, self.pan_number):
#             frappe.throw(_('PAN format should be: ABCDE1234F (5 letters, 4 digits, 1 letter)'))
#     return True


# def validate_aadhaar_format(self):
#     """Validate Aadhaar number format"""
#     if self.aadhaar_number:
#         # Remove spaces and hyphens
#         aadhaar = self.aadhaar_number.replace(' ', '').replace('-', '')
        
#         if not re.match(r'^\d{12}$', aadhaar):
#             frappe.throw(_('Aadhaar number must be 12 digits'))
#     return True
