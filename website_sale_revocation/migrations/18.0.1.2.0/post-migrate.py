# -*- coding: utf-8 -*-
"""Drop outdated translations of the receipt confirmation body.

The new template body contains no translatable text (the text comes from the
QWeb view), so every language uses the same body. Old per-language bodies
would otherwise keep sending the previous content without the legally required
details.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE mail_template t
           SET body_html = jsonb_build_object('en_US', t.body_html->'en_US')
          FROM ir_model_data d
         WHERE d.module = 'website_sale_revocation'
           AND d.name = 'email_template_revocation_receipt'
           AND d.model = 'mail.template'
           AND d.res_id = t.id
           AND t.body_html ? 'en_US'
    """)
