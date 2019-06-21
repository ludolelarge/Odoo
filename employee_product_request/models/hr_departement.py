# -*- coding: utf-8 -*-

from odoo import fields, models

class Department(models.Model):

    _name = "hr.department"
    _description = "Hr Department"
    _inherit = ['hr.department']
    
    location_id = fields.Many2one('stock.location', string='Location')
    
    location_dest_id = fields.Many2one('stock.location', string='Location Destination')
    
    move_type = fields.Selection([
        ('direct', 'Partial'), ('one', 'All at once')], 'Delivery Type',
        default='one', required=True)
    
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type')
    
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')