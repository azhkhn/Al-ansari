# Copyright (c) 2022, Indictrans and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class OvertimeCalculator(Document):
	# pass
	def on_submit(self):
		if not self.overtime_calculator_detail:
			frappe.throw("The Overtime Calculator Details table cannot be empty.")
		additional_salary_entry(self)	

@frappe.whitelist()
def get_employees_on_oc(from_date,to_date,branch,reporting_manager):

	emp_list = []

	if reporting_manager == " " and branch !=" ":
		emp_list = frappe.db.get_list('Employee',
		    filters={
		        'branch': branch,
		        'status': 'Active'
		    },
		    fields=['name','hourly_rate']
		)

	if branch == " " and reporting_manager !=" ":
		emp_list = frappe.db.get_list('Employee',
		    filters={
		        'reports_to': reporting_manager,
		        'status': 'Active'
		    },
		    fields=['name','hourly_rate']
		)

	if branch != " " and reporting_manager != " ":
		emp_list = frappe.db.get_list('Employee',
		    filters={
		    	'branch': branch,
		        'reports_to': reporting_manager,
		        'status': 'Active'
		    },
		    fields=['name','hourly_rate']
		)

	if branch == " " and reporting_manager ==" ":
		frappe.throw("Please select either branch or reporting manager")

	if emp_list:
		for emp in emp_list:
			h_overtime = frappe.db.sql(""" 
				Select 
					ec.name,
					ec.employee,
					ec.employee_name,
					max(ec.actual_hours) as actual_hours,
					ec.overtime_rate,
					ec.productive_hours,
					st.shift_hours ,
					ec.time,
					ec.is_holiday
				from `tabEmployee Checkin` ec, `tabShift Type` st,`tabEmployee` e  
				where 
					ec.employee = e.name and 
					e.default_shift = st.name and 
					DATE(ec.time) >= %s and 
					DATE(ec.time) <= %s and 
					ec.log_type = 'OUT' and
					e.working_status != 'On Leave' and
					e.name = %s and
					ec.is_holiday = 1
					group by date(ec.time);
				""",(from_date,to_date,emp["name"]),as_dict=1)

			nh_overtime = frappe.db.sql(""" 
				Select 
					ec.name,
					ec.employee,
					ec.employee_name,
					max(ec.actual_hours) as actual_hours,
					ec.overtime_rate,
					ec.productive_hours,
					st.shift_hours ,
					ec.time,
					ec.is_holiday
				from `tabEmployee Checkin` ec, `tabShift Type` st,`tabEmployee` e  
				where 
					ec.employee = e.name and 
					e.default_shift = st.name and 
					DATE(ec.time) >= %s and 
					DATE(ec.time) <= %s and 
					ec.log_type = 'OUT' and
					e.working_status != 'On Leave' and
					e.name = %s and
					ec.is_holiday = 0
					group by date(ec.time);
				""",(from_date,to_date,emp["name"]),as_dict=1)

			final_shift_total = 0.00
			h_actual_total = 0.00
			holiday_overtime_total = 0.00
			h_shift_total = 0.00
			nh_actual_total = 0.00
			non_holiday_overtime_total = 0.00
			nh_shift_total = 0.00
			if h_overtime :
				emp.update({
					"employee_name":h_overtime[0]["employee_name"] ,
					"productive_hours_ratio":h_overtime[0]["productive_hours"] 
					})
			if nh_overtime:
				emp.update({
					"employee_name":nh_overtime[0]["employee_name"],
					"productive_hours_ratio":nh_overtime[0]["productive_hours"]
					})

			if h_overtime:
				ot_amt = 0.00

				for h_ot in h_overtime:
					h_actual_total += h_ot["actual_hours"]
			# 		print("ot_hr ==",round((item2["actual_hours"]-item2["shift_hours"]),2) * item2["productive_hours"]*item2["overtime_rate"])
					holiday_overtime_total += h_ot["actual_hours"] # -h_ot["shift_hours"] if (h_ot["actual_hours"]>h_ot["shift_hours"]) else 0
					# h_shift_total += h_ot["shift_hours"]
					# ot_amt += item2["overtime_rate"] * (item2["productive_hours"] * round((item2["actual_hours"]-item2["shift_hours"]),2))
				
				emp.update({
					"holiday_overtime_rate":h_overtime[0]["overtime_rate"],
					"holiday_overtime":holiday_overtime_total,
					"holiday_actual_hours":h_actual_total,
					"h_shift_total":h_shift_total
					})
			else:
				emp.update({
					"holiday_overtime_rate":frappe.get_value("Employee",emp["name"],["h_ot_rate"]),
					"holiday_overtime":holiday_overtime_total,
					"holiday_actual_hours":h_actual_total,
					"h_shift_total":h_shift_total
					})

			if nh_overtime:	
				ot_amt = 0.00

				for nh_ot in nh_overtime:
					nh_actual_total += nh_ot["actual_hours"]
			# 		print("ot_hr ==",round((item2["actual_hours"]-item2["shift_hours"]),2) * item2["productive_hours"]*item2["overtime_rate"])
					non_holiday_overtime_total += nh_ot["actual_hours"]-nh_ot["shift_hours"] if (nh_ot["actual_hours"]>nh_ot["shift_hours"]) else 0
					nh_shift_total += nh_ot["shift_hours"]
					# ot_amt += item2["overtime_rate"] * (item2["productive_hours"] * round((item2["actual_hours"]-item2["shift_hours"]),2))
				
				emp.update({
					"non_holiday_overtime_rate":nh_overtime[0]["overtime_rate"],
					"non_holiday_overtime":non_holiday_overtime_total,
					"non_holiday_actual_hours":nh_actual_total,
					"nh_shift_total":nh_shift_total
					})

			else:
				emp.update({
					"non_holiday_overtime_rate":frappe.get_value("Employee",emp["name"],["nh_ot_rate"]),
					"non_holiday_overtime":non_holiday_overtime_total,
					"non_holiday_actual_hours":nh_actual_total,
					"nh_shift_total":nh_shift_total
					})

			emp.update({
				"shift_hours":round(emp["h_shift_total"] + emp["nh_shift_total"],2),
				"hourly_rate":emp["hourly_rate"]
				})

	return emp_list

# @frappe.whitelist()
# def additional_salary_entry(frm):
# 	frm = frappe.json.loads(frm)
# 	pending_list = []
# 	created_list = []
# 	for rec in frm["overtime_calculator_detail"]:
# 		if(frappe.db.get_value("Additional Salary",{"employee":rec["employee"],"salary_component":"Overtime","payroll_date":frm["payroll_date"]})):
# 			pending_list.append(rec["idx"])
# 			frappe.msgprint(_("Additional Salary component is already created for row {0}.Please remove the entry from child table.").format(rec["idx"]))
# 		else:
# 			if rec["overtime_amount"] > 0:
# 				add_sal_doc = frappe.new_doc("Additional Salary")
# 				add_sal_doc.employee = rec["employee"]
# 				add_sal_doc.salary_component = "Overtime"
# 				add_sal_doc.amount = rec["overtime_amount"]
# 				add_sal_doc.payroll_date = frm["payroll_date"]
# 				add_sal_doc.save()
# 				add_sal_doc.submit()
# 				created_list.append(rec["idx"])
# 				frappe.msgprint("Additional Salary component created successfully")


def additional_salary_entry(self):
	# frm = frappe.json.loads(frm)
	pending_list = []
	created_list = []
	for rec in range(len(self.overtime_calculator_detail)):
		if(frappe.db.get_value("Additional Salary",{"employee":self.overtime_calculator_detail[rec].employee,"salary_component":"Overtime","payroll_date":self.payroll_date})):
			pending_list.append(self.overtime_calculator_detail[rec].idx)
			frappe.throw(_("Additional Salary component is already created for row {0}. Please remove the entry from child table and then try to submit.").format(self.overtime_calculator_detail[rec].idx))
		else:
			if self.overtime_calculator_detail[rec].overtime_amount > 0:
				add_sal_doc = frappe.new_doc("Additional Salary")
				add_sal_doc.employee = self.overtime_calculator_detail[rec].employee
				add_sal_doc.salary_component = "Overtime"
				add_sal_doc.amount = self.overtime_calculator_detail[rec].overtime_amount
				add_sal_doc.payroll_date = self.payroll_date
				add_sal_doc.save()
				add_sal_doc.submit()
				created_list.append(self.overtime_calculator_detail[rec].idx)
				frappe.msgprint("Additional Salary component created successfully")
			else:
				frappe.msgprint(_("Additional Salary Entry not done for row {0} as the Overtime Amount is 0").format(self.overtime_calculator_detail[rec].idx))