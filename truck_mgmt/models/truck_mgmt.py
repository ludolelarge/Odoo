# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID

from odoo.addons import decimal_precision as dp

class TruckMgmtStage(models.Model):
    """ Model for case stages. This models the main stages of a Maintenance Request management flow. """

    _name = 'truck.mgmt.stage'
    _description = 'Truck Mgmt Stage'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=20)
    fold = fields.Boolean('Folded in Maintenance Pipe')
    done = fields.Boolean('Request Done')
    
class TruckMgmtAccess(models.Model):

    _name = 'truck.mgmt.access'
    _description = 'Truck Mgmt Access'
    _order = 'id'

    name = fields.Char('Name', required=True, translate=True)
    num = fields.Char('Num', required=True, translate=True)
    active = fields.Boolean('Active', default=False, translate=True)
    type = fields.Selection(
        [('badge', 'Badge'),
         ('carte', 'Carte')],
        string='Type', default='carte') 

class TruckMgmt(models.Model):
    _name = 'truck.mgmt'
    _description = 'Truck Management'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date desc'
    
    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values:
            return 'truck_mgmt.mt_truck_status'
        return super(TruckMgmt, self)._track_subtype(init_values)
    
    @api.returns('self')
    def _default_stage(self):
        return self.env['truck.mgmt.stage'].search([], limit=1)

    stage_id = fields.Many2one('truck.mgmt.stage', string='Stage', track_visibility='onchange',
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
    
    #Common
       
    name = fields.Char(string='Name', translate=True, required=True, index=True)
    date = fields.Datetime(string="Date", translate=True, required=True, index=True)
    
    #Delivery

    access_id = fields.Many2one('truck.mgmt.access', string='Access', track_visibility='onchange')
    section = fields.Selection(
        [('ferrero', 'Ferrero'),
         ('bocq', 'Bocq'),
         ('oreal', 'Oreal'),
         ('bois', 'Bois'),
         ('reliure', 'Reliure'),
         ('travaux exterieur', 'Travaux Extérieurs'),
         ('mecanique', 'Mecanique'),
         ('cantine', 'Cantine'),
         ('autres', 'Autres')],
        string='Section', translate=True, index=True, default='ferrero')    
    time_in = fields.Datetime(string="Time In", translate=True)
    truck_plate = fields.Char(string='Truck Plate', translate=True)
    trailer_plate = fields.Char(string='Trailer Plate', translate=True)
    carrier = fields.Char(string='Carrier', translate=True)
    dock = fields.Selection(
        [('dock1', 'Dock 1'),
         ('dock2', 'Dock 2'),
         ('dock3', 'Dock 3'),
         ('dock4', 'Dock 4'),
         ('dock5', 'Dock 5')],
        string='Dock', translate=True, index=True, default='dock1')    
    partner_id = fields.Many2one('res.partner', string='Supplier', readonly=True,
                                 states={'draft': [('readonly', False)]}, translate=True,
                                 change_default=True, track_visibility='always')
    contact_id = fields.Many2one('res.users', string='Contact', index=True,
                             track_visibility='onchange', translate=True, default=lambda self: self.env.user)
    commodity = fields.Text(string='Commodity', translate=True)
    
    #Loading
    lead_num = fields.Char(string='Lead Number', translate=True)
    time_out = fields.Datetime(string='Time out', translate=True)
    temperature = fields.Char(string='Temperature', translate=True)
    humidity = fields.Char(string='Humidity', translate=True)
    inlet = fields.Boolean(string='Inlet', translate=True, default=False)
    lead_num_in = fields.Char(string='Lead Number Inlet', translate=True)
    outing = fields.Boolean(string='Outing', translate=True, default=False)
    lead_num_out = fields.Char(string='Lead Number Outing', translate=True) 
    instructor_id = fields.Many2one('res.users', string='Instructor', index=True,
                             track_visibility='onchange', translate=True, default=lambda self: self.env.user)
    packaging = fields.Selection(
        [('mf', 'MF'),
         ('sf', 'SF'),
         ('pf', 'PF'),
         ('emballage', 'Emballage')],
        string='Packaging', translate=True, default='mf')
    
    truck_odour = fields.Boolean(string='Odour', translate=True, default=False)
    truck_state = fields.Boolean(string='State', translate=True, default=False)
    truck_pastille = fields.Boolean(string='Pastille', translate=True, default=False)
    truck_cleanness = fields.Boolean(string='Cleanness', translate=True, default=False)
    truck_pest = fields.Boolean(string='Pest', translate=True, default=False)
    truck_pallet = fields.Boolean(string='Pallet', translate=True, default=False)
    
    #instructor
    
    driver_ref = fields.Char(string='Driver Reference', translate=True)
    delivery_num = fields.Char(string='Delivery Number', translate=True)
    
    loading_lines = fields.One2many(
        comodel_name='truck.mgmt.loading.line', inverse_name='truckmgmt_id',
        string='Loading line', readonly=True,
        states={'draft': [('readonly', False)]})
    
    @api.model
    def create(self, vals):
        # context: no_log, because subtype already handle this
        self = self.with_context(mail_create_nolog=True)
        res = super(TruckMgmt, self).create(vals)
        if res.owner_user_id:
            res.message_subscribe_users(user_ids=[res.owner_user_id.id])
        return res
    
    @api.multi
    def write(self, vals):
        # Overridden to reset the kanban_state to normal whenever
        # the stage (stage_id) of the Maintenance Request changes.
        if vals and 'kanban_state' not in vals and 'stage_id' in vals:
            vals['kanban_state'] = 'normal'
        if vals.get('owner_user_id'):
            self.message_subscribe_users(user_ids=[vals['owner_user_id']])
        res = super(TruckMgmt, self).write(vals)
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
    
    #@api.onchange('inlet')
    #def check_in(self):
    #    if self.inlet == True:
    #        self.outing= False
    
    #@api.onchange('outing')
    #def check_out(self):
    #    if self.outing == True:
    #        self.inlet = False

        
class TruckMgmtLoadingLine(models.Model):
    _name = 'truck.mgmt.loading.line'
    _description = 'Truck Management Loading Line'

    truckmgmt_id = fields.Many2one('truck.mgmt', string='Truck Mgmt', ondelete='cascade')

    state = fields.Selection([
        [('draft', 'Draft'),
         ('confirm', 'Confirm'),
         ('canceled', 'Canceled')],
    ], related='truckmgmt_id.state', string='State', readonly=True, copy=False, store=True, default='draft')

    
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', 'in', ['product', 'consu'])],
        translate=True, readonly=True,
        states={'draft': [('readonly', False)]})
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')
    product_qty = fields.Float(
        'Quantity To Deliver',
        default=1.0, digits=dp.get_precision('Product Unit of Measure'),
        translate=True, readonly=True,
        states={'draft': [('readonly', False)]})
