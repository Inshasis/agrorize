# Copyright (c) 2026, hidayatali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

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
                frappe.msgprint(_('Existing Customer {0} linked to Farmer').format(existing_customer))
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
                frappe.msgprint(_('Existing Supplier {0} linked to Farmer').format(existing_supplier))
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
        """Calculate balances from transactions"""
        self.calculate_balances()
    
    def calculate_balances(self):
        """Calculate total receivable, payable, and net balance"""
        if not self.customer and not self.supplier:
            return
        
        # Total Seed Purchase (Sales Invoices - Submitted)
        if self.customer:
            total_sales = frappe.db.sql("""
                SELECT 
                    COALESCE(SUM(outstanding_amount), 0) as outstanding,
                    COALESCE(SUM(grand_total), 0) as total
                FROM `tabSales Invoice`
                WHERE customer = %s AND docstatus = 1
            """, self.customer, as_dict=1)[0]
            
            self.total_seed_purchase = total_sales.total
            self.total_receivable = total_sales.outstanding
        
        # Total Crop Sold (Purchase Invoices - Submitted)
        if self.supplier:
            total_purchase = frappe.db.sql("""
                SELECT 
                    COALESCE(SUM(outstanding_amount), 0) as outstanding,
                    COALESCE(SUM(grand_total), 0) as total
                FROM `tabPurchase Invoice`
                WHERE supplier = %s AND docstatus = 1
            """, self.supplier, as_dict=1)[0]
            
            self.total_crop_sold = total_purchase.total
            self.total_payable = total_purchase.outstanding
        
        # Net Balance
        # Positive = We owe farmer (payable > receivable)
        # Negative = Farmer owes us (receivable > payable)
        self.net_balance = self.total_payable - self.total_receivable