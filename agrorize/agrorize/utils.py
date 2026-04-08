import frappe

@frappe.whitelist()
def get_sales_person_from_user(user=None):
    if not user:
        user = frappe.session.user
    
    # Skip for Administrator
    if user == 'Administrator':
        return None
    
    try:
        # Get Employee linked to this User
        employee = frappe.db.get_value('Employee', {'user_id': user}, 'name')
        
        if not employee:
            frappe.msgprint(f'No Employee linked to user {user}. Please contact administrator.')
            return None
        
        # Get Sales Person linked to this Employee
        sales_person = frappe.db.get_value('Sales Person', {'employee': employee}, 'name')
        
        if not sales_person:
            frappe.msgprint(f'No Sales Person linked to Employee {employee}. Please contact administrator.')
            return None
        
        return sales_person
    
    except Exception as e:
        frappe.log_error(f'Error in get_sales_person_from_user: {str(e)}')
        return None