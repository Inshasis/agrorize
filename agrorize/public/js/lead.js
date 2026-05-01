// Auto-populate Sales Person based on logged-in user
frappe.ui.form.on("Lead", {
	onload: function (frm) {
		// Only set if new document and sales person is empty
		if (frm.is_new() && !frm.doc.custom_sales_person) {
			frappe.call({
				method: "agrorize.agrorize.utils.get_sales_person_from_user",
				args: {
					user: frappe.session.user,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("custom_sales_person", r.message);
					}
				},
			});
		}

		// Set up village filter based on postal code on form load
        if (frm.doc.custom_postal_code) {
            frm.set_query('custom_village', function() {
                return {
                    filters: {
                        'postal_code': frm.doc.custom_postal_code
                    }
                };
            });
        }
	},
});


frappe.ui.form.on("Lead", {
	refresh: function (frm) {
		// Show "Create Farmer" or "View Farmer" button only when status is "Converted"
		if (frm.doc.status === "Converted" && !frm.doc.__islocal) {
			// Check if Farmer already exists by matching mobile field
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Farmer",
					filters: { mobile: frm.doc.mobile_no },
					fields: ["name", "farmer_name"],
					limit: 1,
				},
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						// Farmer already exists — show View button
						frm.add_custom_button(__("View Farmer"), () => {
							frappe.set_route("Form", "Farmer", r.message[0].name);
						});
					} else {
						// No Farmer found — show Create button
						frm.add_custom_button(__("Create Farmer"), () => {
							create_farmer_from_lead(frm);
						}).addClass("btn-primary");
					}
				},
			});
		}
	},
});

function create_farmer_from_lead(frm) {
	frappe.call({
		method: "agrorize.agrorize.doctype.lead.create_farmer_from_lead",
		args: {
			lead_name: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Creating Farmer..."),
		callback: function (r) {
			if (r.message) {
				frappe.show_alert(
					{
						message: __("Farmer {0} created successfully", [r.message.farmer_name]),
						indicator: "green",
					},
					5,
				);
				// Refresh the form so the View button appears instead of Create
				frm.reload_doc();
				// Ask user if they want to open the Farmer
				frappe.confirm(
					__("Farmer created successfully. Do you want to open it?"),
					function () {
						frappe.set_route("Form", "Farmer", r.message.name);
					},
				);
			}
		},
		error: function (r) {
			frappe.msgprint({
				title: __("Error"),
				indicator: "red",
				message: r.message,
			});
		},
	});
}