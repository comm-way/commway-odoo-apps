from odoo import http, _
from odoo.http import request

class WebsiteRevocationController(http.Controller):

    @http.route(['/shop/revocation'], type='http', auth="public", website=True)
    def revocation_form(self, **kw):
        """ Step 1: Render the form """
        values = {}
        # Pre-fill if the user is logged in
        if request.env.user.partner_id != request.env.ref('base.public_partner'):
            partner = request.env.user.partner_id
            values.update({
                'customer_name': partner.name,
                'customer_email': partner.email,
            })
        values['privacy_url'] = request.env.company.revocation_privacy_policy_url or '/privacy'
        return request.render("website_sale_revocation.revocation_form_template", values)

    @http.route(['/shop/revocation/submit'], type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def revocation_submit(self, **post):
        order_name = post.get('order_ref')
        # Try to find the sale order in Odoo
        sale_order = request.env['sale.order'].sudo().search([('name', '=', order_name)], limit=1)

        # If an order number was entered but not found, append it to the reason
        reason = post.get('reason') or ''
        if order_name and not sale_order:
            reason = _("ATTENTION: Customer provided order number '%s' (not found in the system).\n\nReason:\n%s") % (order_name, reason)

        revocation_vals = {
            'customer_name': post.get('customer_name'),
            'customer_email': post.get('customer_email'),
            'reason': reason.strip(),
            'sale_order_id': sale_order.id if sale_order else False,
            'partner_id': request.env.user.partner_id.id if request.env.user.partner_id != request.env.ref('base.public_partner') else False,
        }
        
        revocation = request.env['website.revocation'].sudo().create(revocation_vals)
        
        if sale_order:
            # Log a message on the sale order chatter
            sale_order.message_post(body=_("<b>ATTENTION:</b> A revocation request (%s) has been submitted.") % revocation.name)

        return request.render("website_sale_revocation.revocation_success_template", {'revocation': revocation})