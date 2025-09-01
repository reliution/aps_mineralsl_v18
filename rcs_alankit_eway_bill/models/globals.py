# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# For Sandbox

# AUTHENTICATION_ENDPOINT = "{auth_url}/api/ewaybillapi/v1.03/auth"
# EWAY_BILL = "{auth_url}/api/ewaybillapi/v1.03/ewayapi"

# For Production
#
AUTHENTICATION_ENDPOINT = "{auth_url}/ewaybillgateway/v1.03/auth"
EWAY_BILL = "{auth_url}/ewaybillgateway/v1.03/ewayapi"
GENERATE_BILL_BY_IRN = "{auth_url}/eInvoiceGateway/eiewb/v1.03/ewaybill"
GENERATE_EWAY_BILL_ERRORLIST = "{auth_url}/api/ewaybillapi/v1.03/Master/GetErrorList"
