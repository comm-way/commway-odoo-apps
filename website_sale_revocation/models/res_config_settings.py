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
    # A mandatory checkbox is an extra hurdle that § 13a FAGG / Art. 11a Directive 2023/2673
    # does not require; the GDPR information duty is met by a notice with a link.
    revocation_privacy_mode = fields.Selection(
        selection=[
            ('notice', 'Notice with link'),
            ('checkbox', 'Mandatory checkbox'),
        ],
        string='Privacy Policy Display',
        default='notice',
        required=True,
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
    revocation_privacy_mode = fields.Selection(
        related='company_id.revocation_privacy_mode',
        readonly=False
    )