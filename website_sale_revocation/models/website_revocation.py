# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from markupsafe import Markup

class WebsiteRevocation(models.Model):
    _name = 'website.revocation'
    _description = 'Customer Revocation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    
    # Customer data
    customer_name = fields.Char(string='Customer Name', required=True, tracking=True)
    customer_email = fields.Char(string='Email', required=True, tracking=True)
    
    # Link to Odoo structures
    sale_order_id = fields.Many2one('sale.order', string='Order', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    
    # Cancellation Details
    revocation_date = fields.Datetime(string='Receipt Date', default=fields.Datetime.now, readonly=True, tracking=True)
    reason = fields.Text(string='Reason (Optional)')
    
    # Status Pipeline
    state = fields.Selection([
        ('draft', 'Received'),
        ('process', 'In Review'),
        ('approved', 'Accepted'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('website.revocation') or _('New')
        
        # Create records
        records = super(WebsiteRevocation, self).create(vals_list)
        
        # Automatically trigger the order confirmation email
        records._send_receipt_confirmation_mail()
        
        # ==========================================
        # Notification in the Odoo Center (Activity)
        # ==========================================
        for record in records:
            # Define who will get notices
            if record.sale_order_id and record.sale_order_id.user_id:
                assignee_id = record.sale_order_id.user_id.id
            else:
                assignee_id = self.env.ref('base.user_admin').id
            
            # Creates a red To-Do Counter
            record.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('New revocation for review'),
                note=_('Customer %s has submitted a revocation. Please check deadlines and process.') % record.customer_name,
                user_id=assignee_id
            )
            
        return records

    def _send_receipt_confirmation_mail(self):
        """ Sends the legally required, immediate receipt confirmation """
        # Searches the email template
        template = self.env.ref('website_sale_revocation.email_template_revocation_receipt', raise_if_not_found=False)
        if template:
            for record in self:
                template.send_mail(record.id, force_send=True)

    # ==========================================
    # BACKEND AUTOMATION
    # ==========================================

    def action_set_in_process(self):
        self.ensure_one()
        self.write({'state': 'process'})
        return True

    def action_approve_and_refund(self):
        self.ensure_one()
        self.write({'state': 'approved'})
        
        raw_body = _("<p>Hello %s,</p><p>we have reviewed and accepted your revocation. The refund will be processed shortly.</p>") % self.customer_name
        
        mail_body = Markup(raw_body)
        
        self.message_post(body=mail_body, subtype_xmlid='mail.mt_note')
        
        if self.customer_email:
            mail_vals = {
                'subject': _('Revocation Accepted: %s') % self.name,
                'body_html': mail_body,
                'email_to': self.customer_email,
                'model': self._name,
                'res_id': self.id,
                'auto_delete': True,
            }
            self.env['mail.mail'].sudo().create(mail_vals).send()
            
        self.activity_ids.action_done()
            
        return True

    def action_reject_revocation(self):
        self.ensure_one()
        self.write({'state': 'rejected'})
        
        raw_body = _("<p>Hello %s,</p><p>we have reviewed your revocation. Unfortunately, we cannot accept it.</p>") % self.customer_name
        
        mail_body = Markup(raw_body)
        
        self.message_post(body=mail_body, subtype_xmlid='mail.mt_note')
        
        if self.customer_email:
            mail_vals = {
                'subject': _('Revocation Rejected: %s') % self.name,
                'body_html': mail_body,
                'email_to': self.customer_email,
                'model': self._name,
                'res_id': self.id,
                'auto_delete': True,
            }
            self.env['mail.mail'].sudo().create(mail_vals).send()
            
        self.activity_ids.action_done()
            
        return True