# -*- coding: utf-8 -*-

from datetime import datetime
import pytz
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError


class FleetReservedTime(models.Model):
    _name = "fleet.reserved"
    _description = "Reserved Time"

    employee = fields.Many2one('hr.employee', string='Employee')
    date_from = fields.Datetime(string='Reserved Date From')
    date_to = fields.Datetime(string='Reserved Date To')
    allday = fields.Boolean(string='All Day', default=False)
    reserved_obj = fields.Many2one('fleet.vehicle')

class FleetVehicleInherit(models.Model):
    _inherit = 'fleet.vehicle'

    check_availability = fields.Boolean(default=True, copy=False)
    reserved_time = fields.One2many('fleet.reserved', 'reserved_obj', String='Reserved Time', readonly=1,
                                    ondelete='cascade')

class EmployeeFleet(models.Model):
    _name = 'employee.fleet'
    _description = 'Employee Vehicle Request'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date_from desc'
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('employee.fleet')
        return super(EmployeeFleet, self).create(vals)
    
    @api.multi
    def unlink(self):
        for each in self:
            each.reserved_fleet_id.unlink()
            each.fleet.write({'check_availability': True})
        return super(EmployeeFleet,self).unlink()
        
    @api.multi
    def send(self):
        fleet_obj = self.env['fleet.vehicle'].search([('name', '=', self.fleet.name)])
        check_availability = 0
        for i in fleet_obj:
            for each in i.reserved_time:
                if not each.allday:                  
                    if each.date_from <= self.date_from <= each.date_to:
                        check_availability = 1
                        break
                    elif self.date_from < each.date_from:
                        if each.date_from <= self.date_to <= each.date_to:
                                check_availability = 1
                                break
                        elif self.date_to > each.date_to:
                                check_availability = 1
                                break
                        else:
                            check_availability = 0
                    else:
                        check_availability = 0
                else:
                    if each.date_from <= self.date_from <= each.date_to:
                        check_availability = 1
                        break
                    elif self.date_from < each.date_from:
                        if each.date_from <= self.date_to <= each.date_to:
                                check_availability = 1
                                break
                        elif self.date_to > each.date_to:
                                check_availability = 1
                                break
                        else:
                            check_availability = 0
                    else:
                        check_availability = 0
                    
        if check_availability == 0:
            reserved_id = self.fleet.reserved_time.create({'employee': self.employee.id,
                                                           'date_from': self.date_from,
                                                           'date_to': self.date_to,
                                                           'allday': self.allday,
                                                           'reserved_obj': self.fleet.id,
                                                           })
            self.write({'reserved_fleet_id': reserved_id.id})
            self.state = 'waiting'
        else:
            raise Warning('Sorry This vehicle is already requested by another employee')

    @api.multi
    def approve(self):
        self.fleet.fleet_status = True
        self.state = 'confirm'
        mail_content = _('Hi %s,<br>Your vehicle request for the reference %s is approved.') % \
                        (self.employee.name, self.name)
        main_content = {
            'subject': _('%s: Approved') % self.name,
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': self.employee.work_email,
        }
        mail_id = self.env['mail.mail'].create(main_content)
        mail_id.mail_message_id.body = mail_content
        mail_id.send()
        if self.employee.user_id:
            mail_id.mail_message_id.write({'needaction_partner_ids': [(4, self.employee.user_id.partner_id.id)]})
            mail_id.mail_message_id.write({'partner_ids': [(4, self.employee.user_id.partner_id.id)]})

    @api.multi
    def reject(self):
        self.reserved_fleet_id.unlink()
        self.state = 'reject'
        mail_content = _('Hi %s,<br>Sorry, Your vehicle request for the reference %s is Rejected.') % \
                        (self.employee.name, self.name)

        main_content = {
            'subject': _('%s: Approved') % self.name,
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': self.employee.work_email,
        }
        mail_id = self.env['mail.mail'].create(main_content)
        mail_id.mail_message_id.body = mail_content
        mail_id.send()
        if self.employee.user_id:
            mail_id.mail_message_id.write({'needaction_partner_ids': [(4, self.employee.user_id.partner_id.id)]})
            mail_id.mail_message_id.write({'partner_ids': [(4, self.employee.user_id.partner_id.id)]})

    @api.multi
    def cancel(self):
        if self.reserved_fleet_id:
            self.reserved_fleet_id.unlink()
        self.state = 'cancel'

    @api.multi
    def returned(self):
        for each in self:
            each.reserved_fleet_id.unlink()
            each.returned_date = fields.datetime.now()
            each.state = 'return'

    @api.one
    def check_group(self):
        user=self.env['res.users'].browse(self.env.uid)
        if user.has_group('hr.group_hr_manager'):
            self.check_user_group = True
        else:
            self.check_user_group = False
            
    @api.constrains('start_datetime', 'stop_datetime', 'start_date', 'stop_date')
    def _check_closing_date(self):
        for each in self:
            if each.start_datetime and each.stop_datetime and each.stop_datetime < each.start_datetime:
                raise ValidationError(_('Ending datetime cannot be set before starting datetime.'))
            if each.start_date and each.stop_date and each.stop_date < each.start_date:
                raise ValidationError(_('Ending date cannot be set before starting date.'))
  
    @api.onchange('start_date', 'start_datetime', 'stop_date', 'stop_datetime')
    def check_availability(self):
        self.fleet = ''
        fleet_obj = self.env['fleet.vehicle'].search([])
        for i in fleet_obj:
            for each in i.reserved_time:
                if self.state not in ('waiting','confirm'):
                    if not self.allday:
                        #Request Partial Day    
                        if each.date_from <= self.start_datetime <= each.date_to:
                            i.write({'check_availability': False})
                            break
                        elif self.start_datetime < each.date_from:
                            if each.date_from <= self.stop_datetime <= each.date_to:
                                i.write({'check_availability': False})
                                break
                            elif self.stop_datetime > each.date_to:
                                i.write({'check_availability': False})
                                break
                            else:
                                i.write({'check_availability': True})
                        else:
                            i.write({'check_availability': True})
                    else:
                        #Request Full Day
                        if each.date_from[:10] <= self.start_date <= each.date_to[:10]:
                            i.write({'check_availability': False})
                            break
                        elif self.start_date < each.date_from[:10]:
                            if each.date_from[:10] <= self.stop_date <= each.date_to[:10]:
                                i.write({'check_availability': False})
                                break
                            elif self.stop_date > each.date_to[:10]:
                                i.write({'check_availability': False})
                                break
                            else:
                                i.write({'check_availability': True})
                        else:
                            i.write({'check_availability': True})
    @api.multi
    def _compute_dates(self):
        self.start_date = self.date_from
        self.start_datetime = self.date_from
        self.stop_date = self.date_to
        self.stop_datetime = self.date_to
        
    @api.multi
    def _inverse_dates(self):
        if self.allday:
            tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc

            enddate = fields.Datetime.from_string(self.stop_date)
            enddate = tz.localize(enddate)
            enddate = enddate.replace(hour=18)
            enddate = enddate.astimezone(pytz.utc)
            self.date_to = fields.Datetime.to_string(enddate)

            startdate = fields.Datetime.from_string(self.start_date)
            startdate = tz.localize(startdate)  # Add "+hh:mm" timezone
            startdate = startdate.replace(hour=8) # Set 8 AM in localtime
            startdate = startdate.astimezone(pytz.utc)  # Convert to UTC
            self.date_from = fields.Datetime.to_string(startdate)
        else:
            self.date_from = self.start_datetime
            self.date_to = self.stop_datetime
                                   
    check_user_group = fields.Boolean(string='Check User Group', compute='check_group', default=True)
    reserved_fleet_id = fields.Many2one('fleet.reserved', invisible=1, copy=False)
    name = fields.Char(string='Request Number', copy=False)
    employee = fields.Many2one('hr.employee', string='Employee', required=1, readonly=True,
                               states={'draft': [('readonly', False)]})
    req_date = fields.Date(string='Requested Date', default=datetime.now(), required=1, readonly=True,
                           states={'draft': [('readonly', False)]}, help="Requested Date")
    fleet = fields.Many2one('fleet.vehicle', string='Vehicle', required=1, readonly=True,
                            states={'draft': [('readonly', False)]} , track_visibility='onchange')
    
    date_from = fields.Datetime(string='Date From')
    date_to = fields.Datetime(string='Date To')
    
    # default=datetime.now().date().replace(month=1, day=1)
    
    start_date = fields.Date('Start Date',compute='_compute_dates', inverse='_inverse_dates'
                             , store=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'
                             , default=datetime.now().date())
    
    start_datetime = fields.Datetime('Start DateTime',compute='_compute_dates', inverse='_inverse_dates'
                                     , store=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'
                                     , default=datetime.now().date())
    
    stop_date = fields.Date('End Date',compute='_compute_dates', inverse='_inverse_dates'
                            , store=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'
                            , default=datetime.now().date())
    
    stop_datetime = fields.Datetime('End DateTime',compute='_compute_dates', inverse='_inverse_dates'
                                    , store=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'
                                    , default=datetime.now().date())
    
    allday = fields.Boolean(string='All Day', inverse='_inverse_dates', required=0, readonly=True,
                              states={'draft': [('readonly', False)]}, default=False , track_visibility='onchange')
    
    returned_date = fields.Datetime(string='Returned Date', readonly=1)
    purpose = fields.Text(string='Purpose', required=1, readonly=True,
                          states={'draft': [('readonly', False)]}, help="Purpose")
    state = fields.Selection([('draft', 'Draft'), ('waiting', 'Waiting for Approval'), ('cancel', 'Cancel'),
                              ('confirm', 'Approved'), ('reject', 'Rejected'), ('return', 'Returned')],
                             string="State", default="draft" , track_visibility='onchange')