import frappe

def remove_custom_fields():
    custom_fields = frappe.get_all(
        "Custom Field",
        filters={"module": "AgroRize"},
        pluck="name"
    )

    for field in custom_fields:
        frappe.delete_doc("Custom Field", field)