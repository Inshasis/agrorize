# Copyright (c) 2026, Inshasis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import re

class PostalCode(Document):
    def validate(self):
        self.convert_to_titlecase()
    
    def convert_to_titlecase(self):
        fields_to_convert = ['post', 'taluka', 'district', 'state']
        
        for field in fields_to_convert:
            if self.get(field):
                value = self.get(field).title()
                self.set(field, value)
    
    def before_save(self):
        self.convert_to_titlecase()


# Alternative advanced title case function (if needed for special cases)
def advanced_title_case(text):
    if not text:
        return text

    return ' '.join(word.capitalize() for word in text.lower().split())