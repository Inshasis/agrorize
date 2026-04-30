frappe.ui.form.on('Customer', {
    refresh: function(frm) {

        // Hide sections
        frm.set_df_property('internal_customer_section', 'hidden', 1);

        // Hide fields
        frm.set_df_property('prospect_name', 'hidden', 1);
        frm.set_df_property('opportunity_name', 'hidden', 1);
        frm.set_df_property('lead_name', 'hidden', 1);
		frm.set_df_property('account_manager', 'hidden', 1);
    }
});