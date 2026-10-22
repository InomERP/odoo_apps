def migrate(cr, version):
    """ Contacts already used as owner, tenant or buyer get the matching role,
    so the role checks added in 19.0.1.2.0 hold for existing records. """
    cr.execute("""
        UPDATE res_partner SET is_property_owner = TRUE
         WHERE is_property_owner IS NOT TRUE
           AND id IN (SELECT owner_id FROM property_property WHERE owner_id IS NOT NULL)
    """)
    cr.execute("""
        UPDATE res_partner SET is_tenant = TRUE
         WHERE is_tenant IS NOT TRUE
           AND id IN (SELECT tenant_id FROM property_rental_contract)
    """)
    cr.execute("""
        UPDATE res_partner SET is_property_buyer = TRUE
         WHERE is_property_buyer IS NOT TRUE
           AND id IN (SELECT buyer_id FROM property_sale_contract)
    """)
