// Copyright (c) 2026, Inshasis and contributors
// For license information, please see license.txt

// Convert Post, Taluka, District, and State to Title Case on save

frappe.ui.form.on('Postal Code', {
    // Convert to title case when form loads
    refresh: function(frm) {
        convert_to_titlecase(frm);
    },
    
    // Convert Post to title case
    post: function(frm) {
        if (frm.doc.post) {
            frm.set_value('post', toTitleCase(frm.doc.post));
        }
    },
    
    // Convert Taluka to title case
    taluka: function(frm) {
        if (frm.doc.taluka) {
            frm.set_value('taluka', toTitleCase(frm.doc.taluka));
        }
    },
    
    // Convert District to title case
    district: function(frm) {
        if (frm.doc.district) {
            frm.set_value('district', toTitleCase(frm.doc.district));
        }
    },
    
    // Convert State to title case
    state: function(frm) {
        if (frm.doc.state) {
            frm.set_value('state', toTitleCase(frm.doc.state));
        }
    },
    
    // Before save validation - ensure all fields are in title case
    validate: function(frm) {
        convert_to_titlecase(frm);
    }
});

// Helper function to convert text to Title Case
function toTitleCase(str) {
    if (!str) return str;
    
    return str.toLowerCase().split(' ').map(function(word) {
        return word.charAt(0).toUpperCase() + word.slice(1);
    }).join(' ');
}

// Helper function to convert all fields to title case
function convert_to_titlecase(frm) {
    let fields_to_convert = ['post', 'taluka', 'district', 'state'];
    
    fields_to_convert.forEach(function(field) {
        if (frm.doc[field]) {
            frm.set_value(field, toTitleCase(frm.doc[field]));
        }
    });
}