# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class InomAssetIotController(http.Controller):
    """Token secured REST endpoint that lets external devices push meter
    readings for an asset.

    Example:
        POST /asset_care/iot/push
        {
            "token": "<asset iot token>",
            "meter": "Running Hours",
            "value": 1523.5
        }
    """

    @http.route('/asset_care/iot/push', type='http', auth='public',
                methods=['POST'], csrf=False)
    def push_reading(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except (ValueError, TypeError):
            return self._json_response(
                {'status': 'error', 'message': 'Invalid JSON body.'}, 400)

        token = payload.get('token')
        meter_name = payload.get('meter')
        value = payload.get('value')
        if not token or not meter_name or value is None:
            return self._json_response({
                'status': 'error',
                'message': 'Fields token, meter and value are required.',
            }, 400)

        asset = request.env['inom.asset'].sudo().search(
            [('iot_token', '=', token)], limit=1)
        if not asset:
            return self._json_response(
                {'status': 'error', 'message': 'Invalid token.'}, 401)

        meter = request.env['inom.asset.meter'].sudo().search([
            ('asset_id', '=', asset.id),
            ('name', '=ilike', meter_name),
        ], limit=1)
        if not meter:
            return self._json_response({
                'status': 'error',
                'message': 'Meter not found on this asset.',
            }, 404)

        try:
            reading = request.env['inom.asset.meter.reading'].sudo().create({
                'meter_id': meter.id,
                'value': float(value),
                'source': 'iot',
            })
        except Exception as exc:  # noqa: BLE001 - surfaced to device
            return self._json_response(
                {'status': 'error', 'message': str(exc)}, 422)

        return self._json_response({
            'status': 'ok',
            'reading_id': reading.id,
            'asset': asset.reference_no,
            'meter': meter.name,
            'value': reading.value,
        }, 200)

    @staticmethod
    def _json_response(body, status):
        return request.make_response(
            json.dumps(body), status=status,
            headers=[('Content-Type', 'application/json')])
