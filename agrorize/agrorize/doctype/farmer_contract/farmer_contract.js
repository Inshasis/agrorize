// Copyright (c) 2026, Inshasis and contributors
// For license information, please see license.txt

frappe.ui.form.on('Farmer Contract', {
	refresh: function(frm) {
		if (frm.doc.status) {
			frm.page.set_indicator(frm.doc.status, get_status_color(frm.doc.status));
		}
		
		add_custom_styles();
		add_status_buttons(frm);
		
		if (frm.doc.docstatus === 1 && frm.doc.crop_harvest_schedule) {
			add_harvest_buttons(frm);
		}
		
		show_contract_summary_card(frm);

		//Farmer Filter - Active Only
		frm.set_query('farmer', function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });
	},

	onload: function(frm) {
        //Farmer Filter - Active Only
        frm.fields_dict['farmer'].get_query = function(doc) {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        };
    },
	
	status: function(frm) {
		if (frm.doc.status) {
			frm.page.set_indicator(frm.doc.status, get_status_color(frm.doc.status));
		}
	},
	
	harvest_frequency: function(frm) {
		if (frm.doc.harvest_frequency) {
			frappe.call({
				method: 'agrorize.agrorize.doctype.farmer_contract.farmer_contract.get_max_harvest_days',
				args: {frequency: frm.doc.harvest_frequency},
				callback: function(r) {
					if (r.message) {
						frm.set_df_property('harvest_cycle_days', 'description', 
							'Maximum ' + r.message + ' days allowed for ' + frm.doc.harvest_frequency);
					}
				}
			});
		}
	}
});

// ==================== CUSTOM STYLES (SaaS Clean) ====================

function add_custom_styles() {
	if (!$('#farmer-contract-saas-styles').length) {
		$('head').append(`
			<style id="farmer-contract-saas-styles">
				/* Clean SaaS Dialog */
				.fc-saas-dialog .modal-content {
					border-radius: 8px;
					border: 1px solid #e5e7eb;
				}
				
				.fc-saas-dialog .modal-header {
					background: #fff;
					border-bottom: 1px solid #e5e7eb;
					padding: 12px 20px;
				}
				
				.fc-saas-dialog .modal-header h4 {
					color: #111827;
					font-weight: 600;
					font-size: 14px;
					margin: 0;
				}
				
				.fc-saas-dialog .modal-body {
					padding: 16px 20px;
				}
				
				/* Compact Stats */
				.fc-stats-compact {
					display: grid;
					grid-template-columns: repeat(4, 1fr);
					gap: 10px;
					margin: 12px 0;
				}
				
				.fc-stat-item {
					padding: 10px;
					background: #f9fafb;
					border-radius: 4px;
					border: 1px solid #e5e7eb;
				}
				
				.fc-stat-label {
					font-size: 10px;
					color: #6b7280;
					text-transform: uppercase;
					letter-spacing: 0.3px;
					margin-bottom: 3px;
				}
				
				.fc-stat-value {
					font-size: 16px;
					font-weight: 600;
					color: #111827;
				}
				
				.fc-stat-unit {
					font-size: 11px;
					color: #6b7280;
					font-weight: 400;
				}
				
				/* Progress Bar Compact */
				.fc-progress-compact {
					margin: 12px 0;
				}
				
				.fc-progress-bar-compact {
					height: 8px;
					background: #e5e7eb;
					border-radius: 4px;
					overflow: hidden;
				}
				
				.fc-progress-fill-compact {
					height: 100%;
					background: #111827;
					transition: width 0.5s ease;
				}
				
				.fc-progress-text {
					display: flex;
					justify-content: space-between;
					font-size: 10px;
					color: #6b7280;
					margin-top: 3px;
				}
				
				/* Harvest Entry Form */
				.fc-harvest-entry {
					background: #f9fafb;
					padding: 12px;
					border-radius: 4px;
					border: 1px solid #e5e7eb;
					margin: 10px 0;
				}
				
				.fc-harvest-header {
					display: flex;
					justify-content: space-between;
					align-items: center;
					margin-bottom: 10px;
					padding-bottom: 10px;
					border-bottom: 1px solid #e5e7eb;
				}
				
				.fc-harvest-number {
					font-size: 12px;
					font-weight: 600;
					color: #111827;
				}
				
				.fc-harvest-date {
					font-size: 11px;
					color: #6b7280;
				}
				
				.fc-harvest-fields {
					display: grid;
					grid-template-columns: 1fr 1fr;
					gap: 10px;
				}
				
				.fc-field-group {
					margin-bottom: 0;
				}
				
				.fc-field-label {
					font-size: 11px;
					color: #374151;
					font-weight: 500;
					margin-bottom: 3px;
				}
				
				.fc-field-input {
					width: 100%;
					padding: 6px 10px;
					border: 1px solid #d1d5db;
					border-radius: 4px;
					font-size: 12px;
				}
				
				.fc-field-input:focus {
					outline: none;
					border-color: #111827;
				}
				
				/* Table Clean */
				.fc-table-clean {
					width: 100%;
					font-size: 12px;
					border-collapse: collapse;
				}
				
				.fc-table-clean tr {
					border-bottom: 1px solid #e5e7eb;
				}
				
				.fc-table-clean tr:last-child {
					border-bottom: none;
				}
				
				.fc-table-clean td {
					padding: 8px 10px;
				}
				
				.fc-table-clean td:first-child {
					color: #6b7280;
					width: 35%;
				}
				
				.fc-table-clean td:last-child {
					color: #111827;
					font-weight: 500;
				}
				
				/* Section Header */
				.fc-section-header {
					font-size: 11px;
					font-weight: 600;
					color: #111827;
					margin: 12px 0 6px 0;
					text-transform: uppercase;
					letter-spacing: 0.3px;
				}
				
				/* Alert Compact */
				.fc-alert-compact {
					padding: 8px 10px;
					border-radius: 4px;
					font-size: 11px;
					margin: 10px 0;
					border-left: 3px solid;
				}
				
				.fc-alert-warning {
					background: #fffbeb;
					border-color: #f59e0b;
					color: #92400e;
				}
				
				.fc-alert-info {
					background: #eff6ff;
					border-color: #3b82f6;
					color: #1e40af;
				}
			</style>
		`);
	}
}

// ==================== CONTRACT SUMMARY ====================

function show_contract_summary_card(frm) {
	if (frm.doc.docstatus !== 1) return;
	
	let completed = 0;
	if (frm.doc.crop_harvest_schedule) {
		completed = frm.doc.crop_harvest_schedule.filter(h => h.harvest_status === 'Completed').length;
	}
	let progress = frm.doc.crop_harvest_schedule ? (completed / frm.doc.crop_harvest_schedule.length) * 100 : 0;
	
	let html = `
		<div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 16px; margin-bottom: 16px;">
			<div class="fc-stats-compact">
				<div class="fc-stat-item">
					<div class="fc-stat-label">Contract Value</div>
					<div class="fc-stat-value">${format_currency(frm.doc.total_contract_value, frm.doc.currency).split('.')[0]}</div>
				</div>
				<div class="fc-stat-item">
					<div class="fc-stat-label">Expected</div>
					<div class="fc-stat-value">${frm.doc.expected_total_quantity}<span class="fc-stat-unit">T</span></div>
				</div>
				<div class="fc-stat-item">
					<div class="fc-stat-label">Land</div>
					<div class="fc-stat-value">${frm.doc.contract_land_area}<span class="fc-stat-unit">${frm.doc.land_measurement}</span></div>
				</div>
				<div class="fc-stat-item">
					<div class="fc-stat-label">Progress</div>
					<div class="fc-stat-value">${completed}/${frm.doc.crop_harvest_schedule ? frm.doc.crop_harvest_schedule.length : 0}</div>
				</div>
			</div>
			<div class="fc-progress-compact">
				<div class="fc-progress-bar-compact">
					<div class="fc-progress-fill-compact" style="width: ${progress}%"></div>
				</div>
				<div class="fc-progress-text">
					<span>Completion</span>
					<span><strong>${progress.toFixed(0)}%</strong></span>
				</div>
			</div>
		</div>
	`;
	
	frm.dashboard.add_section(html);
}

// ==================== BUTTONS ====================

function add_status_buttons(frm) {
	if (frm.doc.docstatus !== 1) return;
	
	if (frm.doc.status === 'Active') {
		frm.add_custom_button(__('Put On Hold'), function() {
			show_hold_dialog(frm);
		}, __('Status Actions'));
		
		frm.add_custom_button(__('Mark Completed'), function() {
			show_complete_dialog(frm);
		}, __('Status Actions'));
	}
	
	if (frm.doc.status === 'On Hold') {
		frm.add_custom_button(__('Activate'), function() {
			show_activate_dialog(frm);
		}, __('Status Actions'));
	}
	
	if (frm.doc.status === 'Pending Approval') {
		frm.add_custom_button(__('Approve & Activate'), function() {
			show_approve_dialog(frm);
		}, __('Status Actions'));
	}
}

function add_harvest_buttons(frm) {
	frm.add_custom_button(__('Performance'), function() {
		show_performance_dialog(frm);
	}, __('Harvest Management'));
	
	if (frm.doc.status === 'Active') {
		frm.add_custom_button(__('Record Harvest'), function() {
			show_record_harvest_dialog(frm);
		}, __('Harvest Management'));
	}
	
	frm.add_custom_button(__('View Schedule'), function() {
		show_schedule_dialog(frm);
	}, __('Harvest Management'));
}

// ==================== DIALOGS ====================

function show_hold_dialog(frm) {
	frappe.prompt([
		{
			label: __('Reason for Holding'),
			fieldname: 'reason',
			fieldtype: 'Small Text',
			reqd: 1
		}
	],
	function(values) {
		frappe.call({
			method: 'hold_contract',
			doc: frm.doc,
			args: {reason: values.reason},
			freeze: true,
			freeze_message: __('Updating...'),
			callback: function(r) {
				if (!r.exc) {
					frm.reload_doc();
					frappe.show_alert({message: __('Contract put on hold'), indicator: 'orange'}, 5);
				}
			}
		});
	},
	__('Put On Hold'),
	__('Confirm'));
}

function show_complete_dialog(frm) {
	frappe.confirm(
		__('Mark contract as completed? This cannot be undone.'),
		function() {
			frappe.call({
				method: 'complete_contract',
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Completing...'),
				callback: function(r) {
					if (!r.exc) {
						frm.reload_doc();
						frappe.show_alert({message: __('Contract completed'), indicator: 'green'}, 5);
					}
				}
			});
		}
	);
}

function show_activate_dialog(frm) {
	frappe.confirm(
		__('Activate this contract?'),
		function() {
			frappe.call({
				method: 'activate_contract',
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Activating...'),
				callback: function(r) {
					if (!r.exc) {
						frm.reload_doc();
						frappe.show_alert({message: __('Contract activated'), indicator: 'green'}, 5);
					}
				}
			});
		}
	);
}

function show_approve_dialog(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Approve Contract'),
		fields: [
			{
				fieldtype: 'HTML',
				options: `
					<table class="fc-table-clean">
						<tr><td>Farmer</td><td>${frm.doc.farmer_name}</td></tr>
						<tr><td>Product</td><td>${frm.doc.product}</td></tr>
						<tr><td>Land</td><td>${frm.doc.contract_land_area} ${frm.doc.land_measurement}</td></tr>
						<tr><td>Value</td><td>${format_currency(frm.doc.total_contract_value)}</td></tr>
					</table>
				`
			},
			{
				label: __('Notes'),
				fieldname: 'notes',
				fieldtype: 'Small Text'
			}
		],
		primary_action_label: __('Approve'),
		primary_action(values) {
			frm.set_value('status', 'Active');
			frm.save().then(() => {
				d.hide();
				frappe.show_alert({message: __('Contract approved'), indicator: 'green'}, 5);
			});
		}
	});
	
	d.$wrapper.find('.modal-dialog').addClass('fc-saas-dialog');
	d.show();
}

// ==================== PERFORMANCE DIALOG ====================

function show_performance_dialog(frm) {
	frappe.call({
		method: 'get_harvest_performance',
		doc: frm.doc,
		callback: function(r) {
			if (r.message) {
				let p = r.message;
				let d = new frappe.ui.Dialog({
					title: __('Performance'),
					fields: [{
						fieldtype: 'HTML',
						options: `
							<div class="fc-stats-compact">
								<div class="fc-stat-item">
									<div class="fc-stat-label">Total</div>
									<div class="fc-stat-value">${p.total_harvests}</div>
								</div>
								<div class="fc-stat-item">
									<div class="fc-stat-label">Completed</div>
									<div class="fc-stat-value" style="color: #10b981;">${p.completed}</div>
								</div>
								<div class="fc-stat-item">
									<div class="fc-stat-label">Pending</div>
									<div class="fc-stat-value" style="color: #3b82f6;">${p.pending}</div>
								</div>
								<div class="fc-stat-item">
									<div class="fc-stat-label">Delayed</div>
									<div class="fc-stat-value" style="color: #ef4444;">${p.delayed}</div>
								</div>
							</div>
							
							<div class="fc-section-header">Quantity</div>
							<table class="fc-table-clean">
								<tr><td>Expected</td><td>${p.total_planned.toFixed(2)} Tonne</td></tr>
								<tr><td>Actual</td><td>${p.total_actual.toFixed(2)} Tonne</td></tr>
								<tr><td>Fulfillment</td><td>${p.fulfillment_pct.toFixed(1)}%</td></tr>
							</table>
							
							<div class="fc-progress-compact" style="margin-top: 12px;">
								<div class="fc-progress-bar-compact">
									<div class="fc-progress-fill-compact" style="width: ${p.fulfillment_pct}%; background: ${p.fulfillment_pct >= 80 ? '#10b981' : '#ef4444'};"></div>
								</div>
								<div class="fc-progress-text">
									<span>Fulfillment</span>
									<span><strong>${p.fulfillment_pct.toFixed(1)}%</strong></span>
								</div>
							</div>
							
							<div class="fc-section-header">Schedule</div>
							<div class="fc-progress-compact">
								<div class="fc-progress-bar-compact">
									<div class="fc-progress-fill-compact" style="width: ${p.on_time_pct}%;"></div>
								</div>
								<div class="fc-progress-text">
									<span>On Time</span>
									<span><strong>${p.on_time_pct.toFixed(1)}%</strong></span>
								</div>
							</div>
							
							${p.delayed > 0 ? `
								<div class="fc-alert-compact fc-alert-warning">
									<strong>Attention:</strong> ${p.delayed} harvest(s) delayed
								</div>
							` : ''}
						`
					}],
					size: 'small'
				});
				
				d.$wrapper.find('.modal-dialog').addClass('fc-saas-dialog');
				d.show();
			}
		}
	});
}

// ==================== SMART HARVEST ENTRY ====================

function show_record_harvest_dialog(frm) {
	// Get next planned harvest
	let next_harvest = frm.doc.crop_harvest_schedule.find(h => h.harvest_status === 'Planned' || h.harvest_status === 'Delayed');
	
	if (!next_harvest) {
		frappe.show_alert({message: __('All harvests completed'), indicator: 'green'}, 5);
		return;
	}
	
	let harvest_number = frm.doc.crop_harvest_schedule.indexOf(next_harvest) + 1;
	
	let d = new frappe.ui.Dialog({
		title: __('Record Harvest'),
		fields: [
			{
				fieldtype: 'HTML',
				options: `
					<div class="fc-harvest-entry">
						<div class="fc-harvest-header">
							<div class="fc-harvest-number">Harvest #${harvest_number}</div>
							<div class="fc-harvest-date">${next_harvest.harvest_date}</div>
						</div>
						<div class="fc-harvest-fields">
							<div class="fc-field-group">
								<div class="fc-field-label">Expected</div>
								<input type="number" class="fc-field-input" value="${next_harvest.expected_quantity}" readonly />
							</div>
							<div class="fc-field-group">
								<div class="fc-field-label">Status</div>
								<input type="text" class="fc-field-input" value="${next_harvest.harvest_status}" readonly />
							</div>
						</div>
					</div>
				`
			},
			{
				label: __('Harvest Date'),
				fieldname: 'harvest_date',
				fieldtype: 'Date',
				default: frappe.datetime.get_today(),
				reqd: 1
			},
			{
				label: __('Actual Quantity (Tonne)'),
				fieldname: 'actual_quantity',
				fieldtype: 'Float',
				reqd: 1
			},
			{
				label: __('Remarks'),
				fieldname: 'remarks',
				fieldtype: 'Small Text'
			}
		],
		size: 'small',
		primary_action_label: __('Record'),
		primary_action(values) {
			frappe.call({
				method: 'update_harvest_actual',
				doc: frm.doc,
				args: {
					harvest_date: next_harvest.harvest_date,
					actual_quantity: values.actual_quantity,
					remarks: values.remarks
				},
				freeze: true,
				freeze_message: __('Saving...'),
				callback: function(r) {
					if (!r.exc) {
						d.hide();
						frm.reload_doc();
						frappe.show_alert({message: __('Harvest recorded successfully'), indicator: 'green'}, 5);
					}
				}
			});
		}
	});
	
	d.$wrapper.find('.modal-dialog').addClass('fc-saas-dialog');
	d.show();
}

// ==================== VIEW SCHEDULE ====================

function show_schedule_dialog(frm) {
	let schedule_html = frm.doc.crop_harvest_schedule.map((h, idx) => {
		let status_color = {
			'Completed': '#10b981',
			'Planned': '#3b82f6',
			'Delayed': '#ef4444'
		}[h.harvest_status] || '#6b7280';
		
		return `
			<tr style="border-bottom: 1px solid #e5e7eb;">
				<td style="padding: 8px; width: 50px; text-align: center;">
					<div style="width: 28px; height: 28px; border-radius: 50%; background: ${h.harvest_status === 'Completed' ? status_color : '#f3f4f6'}; border: 2px solid ${status_color}; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
						${h.harvest_status === 'Completed' ? '<span style="color: white; font-size: 12px;">✓</span>' : '<span style="font-size: 10px; font-weight: 600; color: ' + status_color + ';">' + (idx + 1) + '</span>'}
					</div>
				</td>
				<td style="padding: 8px;">
					<div style="font-weight: 500; color: #111827; margin-bottom: 2px; font-size: 11px;">${h.harvest_date}</div>
					<div style="font-size: 10px; color: #6b7280;">Expected: ${h.expected_quantity} T</div>
					${h.actual_quantity > 0 ? `<div style="font-size: 10px; color: #10b981;">Actual: ${h.actual_quantity} T</div>` : ''}
				</td>
				<td style="padding: 8px; text-align: right;">
					<span style="padding: 3px 8px; border-radius: 10px; font-size: 9px; font-weight: 500; background: ${h.harvest_status === 'Completed' ? '#f0fdf4' : h.harvest_status === 'Delayed' ? '#fef2f2' : '#eff6ff'}; color: ${status_color};">
						${h.harvest_status}
					</span>
				</td>
			</tr>
		`;
	}).join('');
	
	let completed = frm.doc.crop_harvest_schedule.filter(h => h.harvest_status === 'Completed').length;
	let progress = (completed / frm.doc.crop_harvest_schedule.length) * 100;
	
	let d = new frappe.ui.Dialog({
		title: __('Harvest Schedule'),
		fields: [{
			fieldtype: 'HTML',
			options: `
				<div class="fc-stats-compact">
					<div class="fc-stat-item">
						<div class="fc-stat-label">Total</div>
						<div class="fc-stat-value">${frm.doc.crop_harvest_schedule.length}</div>
					</div>
					<div class="fc-stat-item">
						<div class="fc-stat-label">Completed</div>
						<div class="fc-stat-value" style="color: #10b981;">${completed}</div>
					</div>
					<div class="fc-stat-item">
						<div class="fc-stat-label">Frequency</div>
						<div class="fc-stat-value" style="font-size: 14px;">${frm.doc.harvest_frequency}</div>
					</div>
					<div class="fc-stat-item">
						<div class="fc-stat-label">Cycle</div>
						<div class="fc-stat-value">${frm.doc.harvest_cycle_days}<span class="fc-stat-unit">d</span></div>
					</div>
				</div>
				
				<div class="fc-progress-compact">
					<div class="fc-progress-bar-compact">
						<div class="fc-progress-fill-compact" style="width: ${progress}%"></div>
					</div>
					<div class="fc-progress-text">
						<span>Progress</span>
						<span><strong>${progress.toFixed(0)}%</strong></span>
					</div>
				</div>
				
				<div style="margin-top: 12px; max-height: 350px; overflow-y: auto;">
					<table style="width: 100%; font-size: 11px;">
						${schedule_html}
					</table>
				</div>
			`
		}],
		size: 'small'
	});
	
	d.$wrapper.find('.modal-dialog').addClass('fc-saas-dialog');
	d.show();
}

// ==================== UTILITIES ====================

function get_status_color(status) {
	return {
		'Draft': 'grey',
		'Pending Approval': 'orange',
		'Active': 'green',
		'On Hold': 'yellow',
		'Expired': 'red',
		'Terminated': 'blue',
		'Completed': 'green'
	}[status] || 'grey';
}