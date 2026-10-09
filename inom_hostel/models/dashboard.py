from odoo import api, models


class InomPortalDashboard(models.AbstractModel):
    _inherit = 'inom.portal.dashboard'

    @api.model
    def _dash_hostel(self, scope):
        Block = self.env['inom.hostel.block']
        Room = self.env['inom.hostel.room']

        blocks = Block.search([])
        beds = sum(blocks.mapped('beds_total'))
        taken = sum(blocks.mapped('beds_taken'))
        free = beds - taken
        maintenance = Room.search_count([('maintenance', '=', True)])
        occupancy = (taken / beds * 100.0) if beds else 0.0

        kpis = [
            self._kpi('Blocks', len(blocks)),
            self._kpi('Beds occupied', taken,
                      hint='Counted from active allocations, not a stored figure.'),
            self._kpi('Beds free', free, tone='ok' if free else 'warn'),
            self._kpi('Occupancy', f'{occupancy:.1f}%',
                      tone='warn' if occupancy > 95 else 'ok'),
        ]

        cards = [
            {'cols': 2, 'items': [
                {'title': 'Occupancy by block', 'type': 'progress',
                 'rows': [{'label': b.name, 'value': b.occupancy} for b in blocks]},
                {'title': 'Rooms by state', 'type': 'donut',
                 'values': [{'label': label, 'value': count} for label, count in
                            self._group_counts('inom.hostel.room', [], 'state')]},
            ]},
            {'cols': 1, 'items': [
                {'title': 'Rooms with beds free', 'type': 'table',
                 'head': ['Room', 'Block', 'Type', 'Capacity', 'Free'],
                 'rows': [[r.display_name, r.block_id.name, r.room_type,
                           r.capacity, r.beds_free]
                          for r in Room.search([('beds_free', '>', 0),
                                                ('maintenance', '=', False)])[:15]]},
                {'title': 'Under maintenance', 'type': 'note',
                 'text': f'{maintenance} rooms are out of allocation.'} if maintenance else
                {'title': 'Under maintenance', 'type': 'note',
                 'text': 'Every room is available for allocation.'},
            ]},
        ]
        return {'kpis': kpis, 'cards': cards}
