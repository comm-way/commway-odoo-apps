from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    revocation_notification_user_id = fields.Many2one(
        'res.users', 
        string='Revocation Notification User'
    )
    revocation_privacy_policy_url = fields.Char(
        string='Privacy Policy URL', 
        default='/privacy'
    )

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    revocation_notification_user_id = fields.Many2one(
        related='company_id.revocation_notification_user_id',
        readonly=False
    )
    revocation_privacy_policy_url = fields.Char(
        related='company_id.revocation_privacy_policy_url',
        readonly=False
    )