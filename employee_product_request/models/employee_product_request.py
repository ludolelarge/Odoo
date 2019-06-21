# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError

_STATES = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('done','Done'),
    ('canceled', 'Canceled')
]

class EmployeeProductRequest(models.Model):

    _name = 'employee.product.request'
    _description = 'Employee Product Request'
    _inherit = ['mail.thread']
    _order = 'request_date desc'

    @api.model
    def _get_default_requested_by(self):
        return self.env['res.users'].browse(self.env.uid)

    name = fields.Char(string='Product Order Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    request_date = fields.Date('Request date',
                             help="Date when the user initiated the request.",
                             default=fields.Date.context_today,
                             track_visibility='onchange')
    delivery_date = fields.Date('Delivery date',
                             default=fields.Date.context_today,
                             track_visibility='onchange')
    requested_by = fields.Many2one('res.users',
                                   'Requested by',
                                   required=True,
                                   track_visibility='onchange', 
                                   default=_get_default_requested_by, readonly = False)
    assigned_to = fields.Many2one('res.users', 'Assigned to', required=True,
                                  track_visibility='onchange')
    line_ids = fields.One2many('employee.product.request.line', 'request_id',
                               'Products to Request',
                               readonly=False,
                               copy=True,
                               track_visibility='onchange', ondelete='cascade', required=True)
    state = fields.Selection(selection=_STATES,
                             string='Status',
                             index=True,
                             track_visibility='onchange',
                             required=True,
                             copy=False,
                             default='draft')    
    requested_department_id = fields.Many2one('hr.department', string='Requested Department', compute='_compute_requested_department', required=True, readonly = False)
    assigned_department_id = fields.Many2one('hr.department', string='Assigned Department', compute='_compute_assigned_department', required=True, readonly = False)
    picking_id = fields.Many2one('stock.picking', string='Picking')
    
    @api.onchange('state')
    def onchange_state(self):
        assigned_to = None
        if self.state:
            if (self.requested_by.id == False):
                self.assigned_to = None
                return

            employee = self.env['hr.employee'].search([('work_email', '=', self.requested_by.email)])
            if(len(employee) > 0):
                if(employee[0].department_id and employee[0].department_id.manager_id):
                    assigned_to = employee[0].department_id.manager_id.user_id

        self.assigned_to = assigned_to

    @api.one
    @api.depends('assigned_to')
    def _compute_assigned_department(self):
        if (self.assigned_to.id == False):
            self.assigned_department_id = None
            return

        employee = self.env['hr.employee'].search([('work_email', '=', self.assigned_to.email)])
        if (len(employee) > 0):
            self.assigned_department_id = employee[0].department_id.id
        else:
            self.assigned_department_id = None
            
    @api.one
    @api.depends('requested_by')
    def _compute_requested_department(self):
        if (self.requested_by.id == False):
            self.requested_department_id = None
            return

        employee = self.env['hr.employee'].search([('work_email', '=', self.requested_by.email)])
        if (len(employee) > 0):
            self.requested_department_id = employee[0].department_id.id
        else:
            self.requested_department_id = None

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('employee.product.request') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('employee.product.request') or _('New')
        
        request = super(EmployeeProductRequest, self).create(vals)
        
        if vals.get('assigned_to'):
            request.message_subscribe_users(user_ids=[request.assigned_to.id])
        return request

    @api.multi
    def write(self, vals):
        res = super(EmployeeProductRequest, self).write(vals)
        for request in self:
            if vals.get('assigned_to'):
                self.message_subscribe_users(user_ids=[request.assigned_to.id])
        return res

    @api.multi
    def button_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def button_confirm(self):
        if self.line_ids:
            return self.write({'state': 'confirm'})
        else:
            raise ValidationError(_('Product not set.'))
        
    @api.multi
    def button_stock_picking(self):    
        
        if self.line_ids:
            for line_ids in self.line_ids:       
                #Create Move vals
                move_vals = {
                    'partner_id': self.assigned_to.partner_id.id,
                    'origin': self.name, 
                    'location_id': self.assigned_department_id.location_id.id,
                    'location_dest_id': self.requested_department_id.location_dest_id.id,
                    'picking_type_id': self.assigned_department_id.picking_type_id.id,
                    'name': self.name,
                    'product_id': line_ids.product_id.id,
                    'product_uom': line_ids.product_uom_id.id,
                    'product_uom_qty': line_ids.product_qty
                }
                #Create Move    
                move = self.env['stock.move'].create(move_vals)
                #Create Picking vals    
                picking_vals = {
                    'partner_id': self.assigned_to.partner_id.id,
                    'origin': self.name, 
                    'location_id': self.assigned_department_id.location_id.id,
                    'location_dest_id': self.requested_department_id.location_dest_id.id,
                    'move_type': self.assigned_department_id.move_type,
                    'picking_type_id': self.assigned_department_id.picking_type_id.id,
                    'move_lines': [(move.ids)]
                }
                #Create Picking
                picking = self.env['stock.picking'].create(picking_vals)
                #Link Move to Picking
                move.write({'picking_id': picking.id})
                #Assign picking id
                self.picking_id = picking.id
                #Action Reserve
                picking.action_assign()
            
                return self.write({'state': 'done'})
        else:
            raise ValidationError(_('Product not set.'))

    @api.multi
    def button_cancel(self):
        return self.write({'state': 'canceled'})

class EmployeeProductRequestLine(models.Model):

    _name = "employee.product.request.line"
    _description = "Employee Product Request Line"
    _inherit = ['mail.thread']

    request_id = fields.Many2one('employee.product.request',
                                 'Product Request',
                                 ondelete='cascade', readonly=True)
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('purchase_ok', '=', True)], required=True,
        track_visibility='onchange')
    name = fields.Char('Description', size=256,
                       track_visibility='onchange')
    product_uom_id = fields.Many2one('product.uom', 'Product Unit of Measure',
                                     track_visibility='onchange')
    product_qty = fields.Float('Quantity', track_visibility='onchange',
                               digits=dp.get_precision(
                                   'Product Unit of Measure'))
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', compute='_compute_analytic_account')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            name = self.product_id.name
            if self.product_id.code:
                name = '[%s] %s' % (name, self.product_id.code)
            if self.product_id.description_purchase:
                name += '\n' + self.product_id.description_purchase
            self.product_uom_id = self.product_id.uom_id.id
            self.product_qty = 1
            self.name = name

    @api.one
    @api.depends('product_id')
    def _compute_analytic_account(self):
        if (self.request_id.requested_by.id == False):
            self.analytic_account_id = None
            return

        employee = self.env['hr.employee'].search([('work_email', '=', self.request_id.requested_by.email)])
        if (len(employee) > 0):
            self.analytic_account_id = employee[0].department_id.analytic_account_id.id
        else:
            self.analytic_account_id = None

    @api.multi
    def write(self, vals):
        res = super(EmployeeProductRequestLine, self).write(vals)
        return res
