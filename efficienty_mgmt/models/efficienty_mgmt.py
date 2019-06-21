# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError
from mx.DateTime.DateTime import today
    
class EfficientyMgmtStage(models.Model):
    """ Model for case stages. This models the main stages of a Maintenance Request management flow. """

    _name = 'efficienty.mgmt.stage'
    _description = 'Efficienty Mgmt Stage'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=20)
    fold = fields.Boolean('Folded in Maintenance Pipe')
    done = fields.Boolean('Request Done')    
    
class EfficientyMgmt(models.Model):
    _name = 'efficienty.mgmt'
    _description = 'Efficienty Management'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date desc'
    
    def _get_default_category_id(self):
        if self._context.get('categ_id') or self._context.get('default_categ_id'):
            return self._context.get('categ_id') or self._context.get('default_categ_id')
        category = self.env.ref('product.product_category_all', raise_if_not_found=False)
        return category and category.type == 'normal' and category.id or False
    
    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values:
            return 'truck_mgmt.mt_truck_status'
        return super(EfficientyMgmt, self)._track_subtype(init_values)

    @api.returns('self')
    def _default_stage(self):
        return self.env['efficienty.mgmt.stage'].search([], limit=1)

    stage_id = fields.Many2one('efficienty.mgmt.stage', string='Stage', track_visibility='onchange',
                               group_expand='_read_group_stage_ids', default=_default_stage)
    
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority')
    color = fields.Integer('Color Index')
    kanban_state = fields.Selection([('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
                                    string='Kanban State', required=True, default='normal', track_visibility='onchange')
    owner_user_id = fields.Many2one('res.users', string='Created by', default=lambda s: s.env.uid)
    
    state = fields.Selection(
        [('draft', 'Draft'),
         ('confirm', 'Confirm'),
         ('canceled', 'Canceled')],
        string='State', readonly=True, default='draft')
       
    date = fields.Datetime(string="Date", required=True, index=True, default=today)
    instructor_id = fields.Many2one('res.users', string='Instructor', index=True, required=True,
                             track_visibility='onchange', default=lambda self: self.env.user)     
    line = fields.Integer(string="Line", required=True, track_visibility='onchange', default=1)
    product_id = fields.Many2one('product.product', 'Product', domain=[('type', 'in', ['product', 'service'])],
        translate=True, required=True)
    product_code = fields.Char(string='Code')    
    product_qty = fields.Float(string="Product Quantity", required=True, track_visibility='onchange', default=1)
    hour_qty = fields.Float(string="Hour Quantity", required=True, track_visibility='onchange', default=1)
    efficienty = fields.Float(string="Efficienty", compute='_compute_efficienty', digits=dp.get_precision('Product Price'))
    efficienty_average = fields.Float(string="Efficienty average", compute='_compute_efficienty_average', digits=dp.get_precision('Product Price'))
    turnover = fields.Float(string="Turnover", compute='_compute_turnover', digits=dp.get_precision('Product Price'))
    lst_price = fields.Float(string="Price", compute='_compute_price', digits=dp.get_precision('Product Price'))
    categ_id = fields.Many2one(
        'product.category', 'Internal Category',
        change_default=True, default=_get_default_category_id, domain="[('type','=','normal')]",
        required=True, help="Select category for the current product", compute='_compute_categ_id', store=True)
    
    @api.one
    @api.depends('product_id','product_qty','hour_qty')
    def _compute_efficienty(self):
        if self.hour_qty > 0:
            self.efficienty = (self.product_id.lst_price * self.product_qty) / self.hour_qty
            
    @api.one
    @api.depends('date','categ_id','product_qty','hour_qty')
    def _compute_efficienty_average(self):

        records = self.env['efficienty.mgmt'].search([('date', 'like', self.date[:10]+'%'),('categ_id', '=' , self.categ_id.id)])
        
        sum_turnover = 0.0
        sum_product_qty = 0.0
        
        for rec in records:
            sum_turnover += (rec.product_qty * rec.efficienty)
            sum_product_qty += rec.product_qty
            
        if records:
            self.efficienty_average = (sum_turnover / sum_product_qty)

    @api.one
    @api.depends('product_id','product_qty','hour_qty')
    def _compute_turnover(self):
        self.turnover = (self.product_id.lst_price * self.product_qty)
               
    @api.one
    @api.depends('product_id')
    def _compute_price(self):
        self.lst_price = self.product_id.lst_price

    @api.one
    @api.depends('product_id')
    def _compute_categ_id(self):
        self.categ_id = self.product_id.categ_id
             
    @api.model
    def create(self, vals):
        # context: no_log, because subtype already handle this
        self = self.with_context(mail_create_nolog=True)
        if vals.get('product_qty') <= 0 or vals.get('hour_qty') <= 0:
            raise ValidationError(_('Product or Hour Quantity must be greater than 0'))
        else :
            res = super(EfficientyMgmt, self).create(vals)
        if res.owner_user_id:
            res.message_subscribe_users(user_ids=[res.owner_user_id.id])
        return res
    
    @api.multi
    def write(self, vals):
        if vals.get('owner_user_id'):
            self.message_subscribe_users(user_ids=[vals['owner_user_id']])
        res = super(EfficientyMgmt, self).write(vals)
        return res
    
    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})
    
    @api.multi
    def action_confirm(self):
        self.write({'state': 'confirm'})
        
    @api.multi
    def action_cancel(self):
        self.write({'state': 'canceled'})
        
    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)
    