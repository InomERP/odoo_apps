# -*- coding: utf-8 -*-
# Order matters: load lighter extensions first, heavier RPC-bearing
# models (stock_lot) afterwards.
from . import pos_config
from . import pos_session
from . import pos_order
from . import pos_order_line
from . import pos_pack_operation_lot
from . import product_product
from . import stock_lot
from . import res_config_settings
