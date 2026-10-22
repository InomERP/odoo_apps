def migrate(cr, version):
    """ Before 19.0.1.4.0, starting a lease did not change the property's status.
    Properties with a running lease are now shown as Rented. """
    cr.execute("""
        UPDATE property_property p SET state = 'rented'
         WHERE p.state IN ('draft', 'available')
           AND EXISTS (SELECT 1 FROM property_rental_contract c
                        WHERE c.property_id = p.id AND c.state = 'running')
    """)
