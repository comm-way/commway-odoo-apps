import logging

from odoo import http, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

# Action name shared between the Turnstile widget (data-action) and the
# server-side verification. Only [a-z0-9_-], max 32 chars.
CAPTCHA_ACTION = 'revocation_submit'
# Name of the hidden honeypot field. Humans never see it, bots fill it.
HONEYPOT_FIELD = 'website_url'


class WebsiteRevocationController(http.Controller):

    def _get_form_values(self, **extra):
        values = {}
        # Pre-fill if the user is logged in
        if request.env.user.partner_id != request.env.ref('base.public_partner'):
            partner = request.env.user.partner_id
            values.update({
                'customer_name': partner.name,
                'customer_email': partner.email,
            })
        values['privacy_url'] = request.env.company.revocation_privacy_policy_url or '/privacy'
        values['privacy_mode'] = request.env.company.revocation_privacy_mode or 'notice'
        # Cloudflare Turnstile site key (set via Website > Settings > Cloudflare Turnstile)
        values['turnstile_site_key'] = request.env['ir.config_parameter'].sudo().get_param('cf.turnstile_site_key')
        values['captcha_action'] = CAPTCHA_ACTION
        values['honeypot_field'] = HONEYPOT_FIELD
        values.update(extra)
        return values

    @http.route(['/shop/revocation'], type='http', auth="public", website=True)
    def revocation_form(self, **kw):
        """ Step 1: Render the form """
        return request.render("website_sale_revocation.revocation_form_template", self._get_form_values())

    def _verify_captcha(self):
        """ Verify the Turnstile (or reCAPTCHA) token with Odoo's built-in check.

        Odoo's ir.http._verify_request_recaptcha_token reads the token from
        request.params ('turnstile_captcha' / 'recaptcha_token_response') and
        raises UserError/ValidationError if the check fails. If no captcha is
        configured, it lets the request through.
        """
        ir_http = request.env['ir.http']
        if not hasattr(ir_http, '_verify_request_recaptcha_token'):
            return True
        try:
            ir_http._verify_request_recaptcha_token(CAPTCHA_ACTION)
        except (UserError, ValidationError) as e:
            _logger.info("Revocation form: captcha check failed from %s: %s",
                         request.httprequest.remote_addr, e)
            return False
        return True

    @http.route(['/shop/revocation/submit'], type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def revocation_submit(self, **post):
        # Honeypot: a hidden field that only bots fill in. Pretend success so
        # the bot gets no signal, but create nothing and send no mail.
        if post.get(HONEYPOT_FIELD):
            _logger.info("Revocation form: honeypot triggered from %s", request.httprequest.remote_addr)
            return request.render("website_sale_revocation.revocation_success_template", {'revocation': False})

        if not self._verify_captcha():
            values = self._get_form_values(
                customer_name=post.get('customer_name'),
                customer_email=post.get('customer_email'),
                order_ref=post.get('order_ref'),
                revocation_items=post.get('revocation_items'),
                reason=post.get('reason'),
                error=_("The security check failed. Please try again."),
            )
            return request.render("website_sale_revocation.revocation_form_template", values)

        order_name = (post.get('order_ref') or '').strip()
        # Try to find the sale order in Odoo
        sale_order = request.env['sale.order'].sudo().search([('name', '=', order_name)], limit=1) if order_name else request.env['sale.order']

        revocation_vals = {
            'customer_name': post.get('customer_name'),
            'customer_email': post.get('customer_email'),
            # Keep the reference exactly as entered, even if no matching order was found
            'order_reference': order_name or False,
            # Partial withdrawal: items the customer wants to withdraw (empty = entire order)
            'revocation_items': (post.get('revocation_items') or '').strip() or False,
            'reason': (post.get('reason') or '').strip(),
            'sale_order_id': sale_order.id if sale_order else False,
            'partner_id': request.env.user.partner_id.id if request.env.user.partner_id != request.env.ref('base.public_partner') else False,
        }

        revocation = request.env['website.revocation'].sudo().create(revocation_vals)

        if sale_order:
            # Log a message on the sale order chatter
            sale_order.message_post(body=_("<b>ATTENTION:</b> A revocation request (%s) has been submitted.") % revocation.name)

        return request.render("website_sale_revocation.revocation_success_template", {'revocation': revocation})
