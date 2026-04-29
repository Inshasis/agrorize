app_name = "agrorize"
app_title = "AgroRize"
app_publisher = "hidayatali"
app_description = "Agrorize - Contract Farming"
app_email = "hidayat@agrorize.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "agrorize",
# 		"logo": "/assets/agrorize/logo.png",
# 		"title": "AgroRize",
# 		"route": "/agrorize",
# 		"has_permission": "agrorize.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/agrorize/css/agrorize.css"
# app_include_js = "/assets/agrorize/js/agrorize.js"

# include js, css files in header of web template
# web_include_css = "/assets/agrorize/css/agrorize.css"
# web_include_js = "/assets/agrorize/js/agrorize.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "agrorize/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Lead" : "public/js/lead.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "agrorize/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "agrorize.utils.jinja_methods",
# 	"filters": "agrorize.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "agrorize.install.before_install"
# after_install = "agrorize.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "agrorize.uninstall.before_uninstall"
# after_uninstall = "agrorize.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "agrorize.utils.before_app_install"
# after_app_install = "agrorize.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "agrorize.utils.before_app_uninstall"
# after_app_uninstall = "agrorize.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "agrorize.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------


scheduler_events = {
    # Daily cron job at 1:00 AM
    # Marks delayed harvests for active contracts
    "cron": {
        "0 1 * * *": [
            "agrorize.agrorize.doctype.farmer_contract.farmer_contract.mark_delayed_harvests"
        ]
    }
}
# scheduler_events = {
# 	"all": [
# 		"agrorize.tasks.all"
# 	],
# 	"daily": [
# 		"agrorize.tasks.daily"
# 	],
# 	"hourly": [
# 		"agrorize.tasks.hourly"
# 	],
# 	"weekly": [
# 		"agrorize.tasks.weekly"
# 	],
# 	"monthly": [
# 		"agrorize.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "agrorize.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "agrorize.event.get_events"
# }
api_methods = [
    "agrorize.agrorize.api.lead.create_farmer_from_lead"
]
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "agrorize.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["agrorize.utils.before_request"]
# after_request = ["agrorize.utils.after_request"]

# Job Events
# ----------
# before_job = ["agrorize.utils.before_job"]
# after_job = ["agrorize.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"agrorize.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# Fixtures
# --------
# Export fixtures to version control
fixtures = [
    {
        "dt": "Farmer Document Type",
        "filters": []
    },
    {
        "dt": "Custom HTML Block",
        "filters": []
    },
    {
        "dt": "Item Group",
        "filters": [
            ["name", "in", ["Seeds","Tulsi Crops"]]
        ]
    },
    {
        "dt": "Custom Field",
        "filters": [
            ["module", "=", "AgroRize"]
        ]
    }
]

before_uninstall = "agrorize.uninstall.remove_custom_fields"


# bench --site agro export-fixtures --app agrorize
# bench --site agro execute agrorize.agrorize.doctype.farmer_contract.farmer_contract.mark_delayed_harvests