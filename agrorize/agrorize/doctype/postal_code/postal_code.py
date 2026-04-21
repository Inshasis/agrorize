# Copyright (c) 2026, Inshasis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class PostalCode(Document):
    def validate(self):
        self.convert_to_uppercase()
    
    def before_save(self):
        self.convert_to_uppercase()
    
    def convert_to_uppercase(self):
        fields_to_convert = ['post', 'taluka', 'district', 'state']
        
        for field in fields_to_convert:
            if self.get(field):
                self.set(field, self.get(field).upper())
    
    