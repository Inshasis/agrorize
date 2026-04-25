// Copyright (c) 2026, Inshasis and contributors
// For license information, please see license.txt

frappe.ui.form.on('Farmer', {
    onload: function(frm) {
        // Set up village filter based on postal code on form load
        if (frm.doc.postal_code) {
            frm.set_query('village', function() {
                return {
                    filters: {
                        'postal_code': frm.doc.postal_code
                    }
                };
            });
        }
    },
    validate:function(frm){
        validate_email_format(frm);
    },

    refresh(frm) {
        // Avoid adding duplicate buttons on every refresh
        if (!frm.custom_balance_btn_added) {
            frm.add_custom_button(__('Update Balance'), () => {
                // Prevent call if doc not saved
                if (frm.is_new()) {
                    frappe.msgprint(__('Please save the document first'));
                    return;
                }

                frappe.call({
                    method: 'agrorize.agrorize.doctype.farmer.farmer.update_farmer_balance',
                    args: {
                        farmer: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __('Calculating balance...'),
                }).then(r => {
                    if (r.message) {
                        // Reload only when needed
                        frm.reload_doc();

                        frappe.show_alert({
                            message: __('Balance Updated'),
                            indicator: 'green'
                        });
                    }
                });
            });
        }
        
        // Add Manage Status button
        if (!frm.is_new()) {
            frm.add_custom_button(__('Manage Status'), () => {
                show_status_dialog(frm);
            });
        }
        
        // Show enhanced balance summary
        show_enhanced_balance_summary(frm);
        
        // Add validation indicators
        add_mobile_validation_indicator(frm);
        add_pan_number_validation_indicator(frm);
        add_aadhaar_number_validation_indicator(frm);
    },
    
    mobile: function(frm) {
        add_mobile_validation_indicator(frm);
    },
    
    farmer_name: function(frm) {
        // Update customer and supplier names if they exist
        if (frm.doc.customer || frm.doc.supplier) {
            frappe.msgprint(__('Farmer name will be updated in linked Customer and Supplier on save'));
        }
    },
    
    pan_number: function(frm) {
        if (frm.doc.pan_number) {
            frm.set_value('pan_number', frm.doc.pan_number.toUpperCase());
            add_pan_number_validation_indicator(frm);
        }
    },
    
    aadhaar_number: function(frm) {
        add_aadhaar_number_validation_indicator(frm);
    },
    
    postal_code: function(frm) {
        // Filter village based on selected postal code
        if (frm.doc.postal_code) {
            frm.set_query('village', function() {
                return {
                    filters: {
                        'postal_code': frm.doc.postal_code
                    }
                };
            });
            
            // Clear village if postal code changes
            if (frm.doc.village) {
                frappe.msgprint({
                    title: __('Postal Code Changed'),
                    message: __('Village field will be filtered based on new postal code. Please reselect village.'),
                    indicator: 'blue'
                });
                frm.set_value('village', '');
            }
        } else {
            // Remove filter if postal code is cleared
            frm.set_query('village', function() {
                return {};
            });
        }
    },
    
    village: function(frm) {
        // Auto-fill postal code when village is selected (if village has postal code)
        if (frm.doc.village && !frm.doc.postal_code) {
            frappe.db.get_value('Village', frm.doc.village, 'postal_code', (r) => {
                if (r && r.postal_code) {
                    frm.set_value('postal_code', r.postal_code);
                }
            });
        }
    }
});

function show_enhanced_balance_summary(frm) {
    if (!frm.doc.__islocal && (frm.doc.total_payable || frm.doc.total_receivable)) {
        let net_balance = frm.doc.net_balance || 0;
        let total_payable = frm.doc.total_payable || 0;
        let total_receivable = frm.doc.total_receivable || 0;
        
        let balance_html = `
            <style>
                /* Hide the close-message div specifically */
                .close-message,
                div.close-message {
                    display: none !important;
                    visibility: hidden !important;
                    opacity: 0 !important;
                    width: 0 !important;
                    height: 0 !important;
                    position: absolute !important;
                    left: -9999px !important;
                }
                
                /* Aggressively hide ALL close buttons */
                .form-message .close,
                .form-message .btn-close,
                .form-message button.close,
                .form-message .indicator-pill-right,
                .intro-area .close,
                .intro-area .btn-close,
                .intro-area button.close,
                .intro-area .indicator-pill-right,
                .alert .close,
                .alert .btn-close,
                .alert button.close,
                .alert .indicator-pill-right,
                button[data-dismiss],
                button[aria-label="Close"],
                .close[aria-label="Close"] {
                    display: none !important;
                    visibility: hidden !important;
                    opacity: 0 !important;
                    width: 0 !important;
                    height: 0 !important;
                    position: absolute !important;
                    left: -9999px !important;
                }
                
                /* Force transparent on parent containers */
                .form-message,
                .intro-area,
                .alert-info {
                    background: transparent !important;
                    background-color: transparent !important;
                    position: relative !important;
                }
                
                .farmer-balance-container {
                    padding: 16px !important;
                    background: #ffffff !important;
                    background-color: #ffffff !important;
                    border: 1px solid #e5e7eb !important;
                    border-radius: 8px !important;
                    margin-bottom: 16px !important;
                    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
                }
                
                .balance-header {
                    color: #111827 !important;
                    font-size: 14px !important;
                    font-weight: 600 !important;
                    margin-bottom: 16px !important;
                    display: flex !important;
                    align-items: center !important;
                    gap: 8px !important;
                }
                
                .balance-header svg {
                    width: 18px !important;
                    height: 18px !important;
                    fill: #111827 !important;
                }
                
                .balance-cards {
                    display: grid !important;
                    grid-template-columns: repeat(3, 1fr) !important;
                    gap: 12px !important;
                    margin-bottom: 12px !important;
                }
                
                .balance-card {
                    background: #fafafa !important;
                    border: 1px solid #e5e7eb !important;
                    border-radius: 6px !important;
                    padding: 14px !important;
                    transition: all 0.15s ease !important;
                    position: relative !important;
                }
                
                .balance-card:hover {
                    background: #ffffff !important;
                    border-color: #d1d5db !important;
                    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06) !important;
                }
                
                .card-label {
                    font-size: 10px !important;
                    color: #6b7280 !important;
                    font-weight: 500 !important;
                    margin-bottom: 8px !important;
                    text-transform: uppercase !important;
                    letter-spacing: 0.5px !important;
                    line-height: 1.2 !important;
                }
                
                .card-amount {
                    font-size: 20px !important;
                    font-weight: 700 !important;
                    color: #111827 !important;
                    display: flex !important;
                    align-items: baseline !important;
                    gap: 3px !important;
                    margin-bottom: 6px !important;
                }
                
                .card-currency {
                    font-size: 14px !important;
                    font-weight: 600 !important;
                    color: #6b7280 !important;
                }
                
                .card-badge {
                    display: inline-block !important;
                    padding: 3px 8px !important;
                    background: #ffffff !important;
                    border: 1px solid #e5e7eb !important;
                    color: #374151 !important;
                    font-size: 9px !important;
                    font-weight: 600 !important;
                    border-radius: 3px !important;
                    text-transform: uppercase !important;
                    letter-spacing: 0.3px !important;
                }
                
                .quick-actions {
                    display: grid !important;
                    grid-template-columns: repeat(4, 1fr) !important;
                    gap: 10px !important;
                    padding-top: 12px !important;
                    border-top: 1px solid #e5e7eb !important;
                }
                
                .action-btn {
                    background: #fafafa !important;
                    border: 1px solid #e5e7eb !important;
                    border-radius: 6px !important;
                    padding: 12px 8px !important;
                    text-align: center !important;
                    cursor: pointer !important;
                    transition: all 0.15s ease !important;
                    text-decoration: none !important;
                    display: flex !important;
                    flex-direction: column !important;
                    align-items: center !important;
                    gap: 6px !important;
                }
                
                .action-btn:hover {
                    border-color: #111827 !important;
                    background: #ffffff !important;
                    transform: translateY(-1px) !important;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08) !important;
                }
                
                .action-btn svg {
                    width: 18px !important;
                    height: 18px !important;
                    fill: #111827 !important;
                }
                
                .action-btn-label {
                    font-size: 11px !important;
                    font-weight: 600 !important;
                    color: #111827 !important;
                    line-height: 1.2 !important;
                }
                
                @media (max-width: 768px) {
                    .balance-cards {
                        grid-template-columns: 1fr !important;
                    }
                    
                    .quick-actions {
                        grid-template-columns: repeat(2, 1fr) !important;
                    }
                }
            </style>
            
            <div class="farmer-balance-container">
                <div class="balance-header">
                    <span>Account Summary</span>
                </div>
                
                <div class="balance-cards">
                    <div class="balance-card">
                        <div class="card-label">We Owe (Payable)</div>
                        <div class="card-amount">
                            <span class="card-currency">₹</span>
                            <span>${format_number(total_payable, null, 2)}</span>
                        </div>
                        <div class="card-badge">Liability</div>
                    </div>
                    
                    <div class="balance-card">
                        <div class="card-label">Farmer Owes (Receivable)</div>
                        <div class="card-amount">
                            <span class="card-currency">₹</span>
                            <span>${format_number(total_receivable, null, 2)}</span>
                        </div>
                        <div class="card-badge">Asset</div>
                    </div>
                    
                    <div class="balance-card">
                        <div class="card-label">Net Balance</div>
                        <div class="card-amount">
                            <span class="card-currency">₹</span>
                            <span>${format_number(Math.abs(net_balance), null, 2)}</span>
                        </div>
                        <div class="card-badge">${net_balance >= 0 ? 'Receivable' : 'Payable'}</div>
                    </div>
                </div>
                
                <div class="quick-actions">
                    ${frm.doc.customer ? `
                    <div class="action-btn" onclick="frappe.set_route('Form', 'Customer', '${frm.doc.customer}')">
                        <svg viewBox="0 0 24 24">
                            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                        </svg>
                        <div class="action-btn-label">View Customer</div>
                    </div>
                    ` : ''}
                    
                    ${frm.doc.supplier ? `
                    <div class="action-btn" onclick="frappe.set_route('Form', 'Supplier', '${frm.doc.supplier}')">
                        <svg viewBox="0 0 24 24">
                            <path d="M20 6h-2.18c.11-.31.18-.65.18-1 0-1.66-1.34-3-3-3-1.05 0-1.96.54-2.5 1.35l-.5.67-.5-.68C10.96 2.54 10.05 2 9 2 7.34 2 6 3.34 6 5c0 .35.07.69.18 1H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-5-2c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zM9 4c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm11 15H4v-2h16v2zm0-5H4V8h5.08L7 10.83 8.62 12 11 8.76l1-1.36 1 1.36L15.38 12 17 10.83 14.92 8H20v6z"/>
                        </svg>
                        <div class="action-btn-label">View Supplier</div>
                    </div>
                    ` : ''}
                    
                    ${frm.doc.customer ? `
                    <div class="action-btn" onclick="frappe.route_options = {'customer': '${frm.doc.customer}'}; frappe.set_route('List', 'Sales Invoice');">
                        <svg viewBox="0 0 24 24">
                            <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                        </svg>
                        <div class="action-btn-label">Sales Invoices</div>
                    </div>
                    ` : ''}
                    
                    ${frm.doc.supplier ? `
                    <div class="action-btn" onclick="frappe.route_options = {'supplier': '${frm.doc.supplier}'}; frappe.set_route('List', 'Purchase Invoice');">
                        <svg viewBox="0 0 24 24">
                            <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM8 14H6v-2h2v2zm0-3H6V9h2v2zm0-3H6V6h2v2zm7 6h-5v-2h5v2zm3-3h-8V9h8v2zm0-3h-8V6h8v2z"/>
                        </svg>
                        <div class="action-btn-label">Purchase Invoices</div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        frm.set_intro(balance_html, true);
        
        // Force remove close button after rendering
        setTimeout(() => {
            const introArea = frm.$wrapper.find('.form-message, .intro-area, .alert');
            // Remove the close-message div specifically
            introArea.find('.close-message').remove();
            // Remove other close buttons
            introArea.find('.close, .btn-close, button[data-dismiss], button[aria-label="Close"]').remove();
            introArea.css('position', 'relative');
        }, 100);
    }
}

function show_status_dialog(frm) {
    let current_status = frm.doc.status || 'Active';
    
    let d = new frappe.ui.Dialog({
        title: __('Manage Farmer Status'),
        fields: [
            {
                fieldname: 'status',
                fieldtype: 'Select',
                label: __('Status'),
                options: ['Active', 'Inactive', 'Suspended'],
                default: current_status,
                reqd: 1,
                onchange: function() {
                    let status = d.get_value('status');
                    let remark_field = d.fields_dict.remark;
                    
                    // Show/hide remark field based on status
                    if (status === 'Inactive' || status === 'Suspended') {
                        remark_field.df.hidden = 0;
                        remark_field.df.reqd = 1;
                        remark_field.refresh();
                    } else {
                        remark_field.df.hidden = 1;
                        remark_field.df.reqd = 0;
                        remark_field.refresh();
                        d.set_value('remark', '');
                    }
                }
            },
            {
                fieldname: 'remark',
                fieldtype: 'Small Text',
                label: __('Remark'),
                description: __('Please provide reason for status change'),
                hidden: (current_status === 'Active' ? 1 : 0),
                reqd: (current_status === 'Inactive' || current_status === 'Suspended' ? 1 : 0)
            },
            {
                fieldname: 'info_section',
                fieldtype: 'Section Break',
                label: __('Linked Records')
            },
            {
                fieldname: 'info_html',
                fieldtype: 'HTML',
                options: `
                    <div style="padding: 10px; background: #f8f9fa; border-radius: 6px; margin-bottom: 10px;">
                        <p style="margin: 0; color: #6c757d; font-size: 13px;">
                            <strong>Note:</strong> Changing status to <strong>Inactive</strong> or <strong>Suspended</strong> 
                            will automatically disable the linked Customer and Supplier records.
                        </p>
                    </div>
                `
            }
        ],
        primary_action_label: __('Update Status'),
        primary_action(values) {
            update_farmer_status(frm, values.status, values.remark);
            d.hide();
        }
    });
    
    d.show();
}

function update_farmer_status(frm, new_status, remark) {
    frappe.call({
        method: 'agrorize.agrorize.doctype.farmer.farmer.update_farmer_status',
        args: {
            farmer: frm.doc.name,
            status: new_status,
            remark: remark || ''
        },
        freeze: true,
        freeze_message: __('Updating status...'),
        callback: function(r) {
            if (r.message) {
                frm.reload_doc();
                
                let indicator_color = new_status === 'Active' ? 'green' : 
                                     new_status === 'Inactive' ? 'red' : 'orange';
                
                frappe.show_alert({
                    message: __('Status updated to {0}', [new_status]),
                    indicator: indicator_color
                }, 5);
                
                if (r.message.customer_disabled || r.message.supplier_disabled) {
                    let msg = __('Linked records updated:');
                    if (r.message.customer_disabled) {
                        msg += '<br>• Customer disabled';
                    }
                    if (r.message.supplier_disabled) {
                        msg += '<br>• Supplier disabled';
                    }
                    frappe.msgprint({
                        title: __('Status Updated'),
                        message: msg,
                        indicator: 'blue'
                    });
                }
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to update status'),
                indicator: 'red'
            });
        }
    });
}

function add_mobile_validation_indicator(frm) {
    if (frm.doc.mobile) {
        let is_valid = /^\d{10,15}$/.test(frm.doc.mobile);
        let indicator_html = is_valid 
            ? '<span class="indicator green">Valid Mobile Number</span>'
            : '<span class="indicator red">Invalid Mobile Number</span>';
        
        frm.set_df_property('mobile', 'description', indicator_html);
    }
}

function add_pan_number_validation_indicator(frm) {
    if (frm.doc.pan_number) {
        let pan_pattern = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
        let is_valid = pan_pattern.test(frm.doc.pan_number);
        
        let indicator_html = is_valid 
            ? '<span class="indicator green">Valid PAN Number</span>'
            : '<span class="indicator red">Invalid PAN Number (Format: ABCDE1234F)</span>';
        
        frm.set_df_property('pan_number', 'description', indicator_html);
    } else {
        frm.set_df_property('pan_number', 'description', '');
    }
}

function add_aadhaar_number_validation_indicator(frm) {
    if (frm.doc.aadhaar_number) {
        let aadhaar = frm.doc.aadhaar_number.replace(/\s/g, '').replace(/-/g, '');
        let aadhaar_pattern = /^\d{12}$/;
        let is_valid = aadhaar_pattern.test(aadhaar);
        
        let indicator_html = is_valid 
            ? '<span class="indicator green">Valid Aadhaar Number</span>'
            : '<span class="indicator red">Invalid Aadhaar Number (Must be 12 digits)</span>';
        
        frm.set_df_property('aadhaar_number', 'description', indicator_html);
    } else {
        frm.set_df_property('aadhaar_number', 'description', '');
    }
}

function validate_email_format(frm) {
    if (frm.doc.email) {
        let email_pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!email_pattern.test(frm.doc.email)) {
            frappe.throw(__('Please enter a valid email address'));
        }
    }
}

function format_currency(amount) {
    return format_number(amount, null, 2);
}