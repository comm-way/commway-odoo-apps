# -*- coding: utf-8 -*-
"""Allow the receipt confirmation e-mail template to be updated.

The template lives in a noupdate block, so existing installations would keep the
old body. Version 1.2.0 moves the legally required content (§ 13a FAGG /
Art. 11a Directive 2023/2673) into a translatable QWeb view and the template
only references it. Flag the record as updatable for this upgrade; the data
loader sets noupdate back to True afterwards.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_model_data
           SET noupdate = false
         WHERE module = 'website_sale_revocation'
           AND name = 'email_template_revocation_receipt'
    """)
