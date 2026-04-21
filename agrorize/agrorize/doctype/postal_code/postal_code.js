// Copyright (c) 2026, Inshasis and contributors
// For license information, please see license.txt

frappe.ui.form.on('Postal Code', {
    // Convert to uppercase when form loads
    refresh: function(frm) {
        convert_to_uppercase(frm);
    },
    
    // Convert Post to uppercase
    post: function(frm) {
        if (frm.doc.post) {
            frm.set_value('post', frm.doc.post.toUpperCase());
        }
    },
    
    // Convert Taluka to uppercase
    taluka: function(frm) {
        if (frm.doc.taluka) {
            frm.set_value('taluka', frm.doc.taluka.toUpperCase());
        }
    },
    
    // Convert District to uppercase
    district: function(frm) {
        if (frm.doc.district) {
            frm.set_value('district', frm.doc.district.toUpperCase());
        }
    },
    
    // Convert State to uppercase
    state: function(frm) {
        if (frm.doc.state) {
            frm.set_value('state', frm.doc.state.toUpperCase());
        }
    },
    
    validate: function(frm) {
        convert_to_uppercase(frm);
    }
});

// Helper function to convert all fields to uppercase
function convert_to_uppercase(frm) {
    let fields_to_convert = ['post', 'taluka', 'district', 'state'];
    
    fields_to_convert.forEach(function(field) {
        if (frm.doc[field]) {
            frm.set_value(field, frm.doc[field].toUpperCase());
        }
    });
}