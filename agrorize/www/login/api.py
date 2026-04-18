import frappe

@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()

        return {
            "status": "success"
        }

    except frappe.exceptions.AuthenticationError:
        return {
            "status": "error",
            "message": "Invalid email or password"
        }
