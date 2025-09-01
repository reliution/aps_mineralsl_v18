from odoo import models, fields, api, _
from odoo.http import request
import requests
from datetime import datetime ,timedelta
from odoo.exceptions import ValidationError
import logging



class IndiamartLog(models.Model):
    _name = "indiamart.log"
    _description = 'Indiamart Log'
    _rec_name = "display_name"

    api_hit_key = fields.Char(string='Api Hit Time')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    count = fields.Integer(string='Count')
    response_code = fields.Char(string='Response Code')
    response_description = fields.Char(string='Response')
    display_name = fields.Char(string="Log Name", compute="_compute_display_name", store=True)


    @api.depends("api_hit_key", "start_date")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"Log {record.api_hit_key} - {record.start_date}"

    @api.model
    def _cron_retrieve_indiamart_leads(self):
        ''' 
        Method called to retrieve IndiaMart leads and create leads in Odoo.
        '''
        config = self.env['indiamart.config.settings'].search([], order="id desc", limit=1)

        now = datetime.now()
        last_hit_time = config.last_api_hit_time
        block_until = config.block_until
        hit_count = config.hit_count or 0

        # Check 5-minute restriction first**
        if config.last_api_hit_time and (now - config.last_api_hit_time) < timedelta(minutes=5):
            raise ValidationError("API calls are restricted to once every 5 minutes. Try again later.")

        # Check if API is currently blocked for 15 minutes**
        if block_until and now < block_until:
            raise ValidationError(
                f"API blocked due to excessive hits. Try again after {block_until.strftime('%Y-%m-%d %H:%M:%S')}.")

        # Check 5-minute restriction**
        if last_hit_time and (now - last_hit_time) < timedelta(minutes=5):
            hit_count += 1  # Increment hit count for every failed attempt
            config.sudo().write({'hit_count': hit_count})

            #Trigger 15-minute block if more than 5 attempts in 5 minutes**
            if hit_count >= 5:
                block_time = now + timedelta(minutes=15)
                config.sudo().write({'block_until': block_time, 'hit_count': 0})  # Reset hit count after blocking
                raise ValidationError(
                    f"Too many requests! API blocked until {block_time.strftime('%Y-%m-%d %H:%M:%S')}.")

            raise ValidationError("API calls are restricted to once every 5 minutes. Try again later.")

        #Reset hit count and update last API hit time on successful call**
        config.sudo().write({'last_api_hit_time': now, 'hit_count': 1})

        if not config.api_key_generated_time:
            # First-time key generation, store now's time
            config.sudo().write({'api_key_generated_time': now})
        else:
            # API key already exists, check if 24 hours have passed
            next_allowed_time = config.api_key_generated_time + timedelta(hours=24)
            if now < next_allowed_time:
                raise ValidationError(
                    f"API can only be triggered 24 hours after the last key generation. "
                    f"Try again after {next_allowed_time.strftime('%Y-%m-%d %H:%M:%S')}."
                )

        # If all checks pass, update last API hit time and hit count**
        config.sudo().write({
            'hit_count': hit_count,
            'last_api_hit_time': now
        })

        glusr_crm_key, start_time, end_time = self._get_indiamart_config_params()
        formatted_start_time, formatted_end_time = self._format_time(start_time, end_time)
        response = self._send_indiamart_request(glusr_crm_key, formatted_start_time, formatted_end_time)
        response_json = response.json()
        self._log_indiamart_response(start_time, end_time, response_json)
        if response.status_code == 200:
            response_json = {
                "CODE": 200,
                "STATUS": "SUCCESS",
                "MESSAGE": "",
                "TOTAL_RECORDS": 18,
                "RESPONSE": [
                    {
                        "UNIQUE_QUERY_ID": "2012487827",
                        "QUERY_TYPE": "W",
                        "QUERY_TIME": "2021-12-08 12:47:25",
                        "SENDER_NAME": "Test",
                        "SENDER_MOBILE": "+91-999XXXXXXX",
                        "SENDER_EMAIL": "arunxyz@gmail.com",
                        "SENDER_COMPANY": "Arun Industries ",
                        "SENDER_ADDRESS": "Arun Industries, Meerut, Uttar Pradesh, 250001",
                        "SENDER_CITY": "Meerut",
                        "SENDER_STATE": "Uttar Pradesh",
                        "SENDER_PINCODE": "250001",
                        "SENDER_COUNTRY_ISO": "IN",
                        "SENDER_MOBILE_ALT": 0,
                        "SENDER_EMAIL_ALT": "arunxyz1@gmail.com",
                        "QUERY_PRODUCT_NAME": "Dye Sublimation Ink",
                        "QUERY_MESSAGE": "I want to buy Dye Sublimation Ink.",
                        "QUERY_MCAT_NAME": "Sublimation Ink",
                        "CALL_DURATION": 0,
                        "RECEIVER_MOBILE": 0
                    }
                ]
            }
            self._process_indiamart_response(response_json)
        else:
            print(f"Error: {response.status_code} - {response.text}")
        config.sudo().write({'last_api_hit_time': now})

    def _get_indiamart_config_params(self):
        '''Fetches configuration parameters from selected Indiamart Configuration'''
        config = self.env['indiamart.config.settings'].search([], order="id desc", limit=1)
        if not config:
            raise ValidationError("No Indiamart Configuration found. Please create one.")

        # Ensure end_time is 7 days after start_time
        end_time = config.start_time + timedelta(days=7)
        config.end_time =end_time
        return (
            config.glusr_crm_key,
            # config.last_sync_time or config.start_time,
            config.last_sync_time if config.last_sync_time else config.start_time,
            end_time
        )

    def _format_time(self, start_time, end_time):
        '''Converts string times to the required format (DD-MMM-YYYY 00:00:00)'''

        def _convert(date_val):
            if not date_val:
                # If missing, use the current timestamp
                return datetime.now().strftime("%d-%m-%Y %H:%M:%S")

            if isinstance(date_val, datetime):
                return date_val.strftime("%d-%m-%Y %H:%M:%S")

            try:
                return datetime.strptime(date_val, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y %H:%M:%S")
            except ValueError:
                try:
                    return datetime.strptime(date_val, "%Y-%m-%d").strftime("%d-%m-%Y %H:%M:%S")
                except ValueError:
                    raise ValidationError(
                        f"Invalid date format: {date_val}. Expected format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS.")

        formatted_start = _convert(start_time)
        formatted_end = _convert(end_time)

        # Ensure end_time is greater than start_time
        if datetime.strptime(formatted_end, "%d-%m-%Y %H:%M:%S") <= datetime.strptime(formatted_start,
                                                                                      "%d-%m-%Y %H:%M:%S"):
            raise ValidationError("End time must be greater than start time.")

        return formatted_start, formatted_end

    def _send_indiamart_request(self, glusr_crm_key, start_time, end_time):
        '''Sends the request to the IndiaMart API'''
        base_url = "https://mapi.indiamart.com/wservce/crm/crmListing/v2/?"
        params = f"glusr_crm_key={glusr_crm_key}&start_time={start_time}&end_time={end_time}"
        url = base_url + params
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json={}, headers=headers)
        return response
    
    @api.model
    def _log_indiamart_response(self, start_time, end_time, response_json):
        ''' 
        Method to log API response in the indiamart.log model.
        '''
        response_code = response_json.get('CODE')
        status = response_json.get('STATUS')
        msg = response_json.get('MESSAGE')
        log_values = {
            'api_hit_key': datetime.now(),
            'start_date': start_time,
            'end_date': end_time,
            'count': self.count,
            'response_code': f"{response_code}({status})",
            'response_description': msg if response_code != 200 else status,
        }

        self.env['indiamart.log'].create(log_values)
        config = self.env['indiamart.config.settings'].search([], order="id desc", limit=1)
        if config:
            config.sudo().write({'last_sync_time': datetime.now()})

    def _process_indiamart_response(self, response_json):
        '''Processes the response from IndiaMart API'''
        if response_json.get('CODE') == 200:
            self._update_last_sync_time()
            self._create_crm_lead(response_json)
        else:
            print(f"Error: {response_json.get('MESSAGE')}")


    def _update_last_sync_time(self):
        '''Update last sync time in the latest Indiamart Configuration record'''
        config = self.env['indiamart.config.settings'].search([], order="id desc", limit=1)
        if config:
            start_time = config.start_time
            # .strftime('%Y-%m-%d %H:%M:%S')
            config.sudo().write({'last_sync_time': start_time})
            self.env.cr.commit()

    def _create_crm_lead(self, response_json):
        response_data = response_json.get('RESPONSE', [])
        leads_to_create = []
        country_obj = self.env['res.country']
        state_obj = self.env['res.country.state']
        config = self.env['indiamart.config.settings'].sudo().search([], limit=1, order="id desc")
        create_customer = config.create_customer if config else False
        sales_team = self.env.ref('indiamart_integration_4devnet.sales_team_indiamart', raise_if_not_found=False)

        for record in response_data:
            sender_company = record.get('SENDER_COMPANY')
            sender_name = record.get('SENDER_NAME')
            customer = False  # Default value
            contact = False  # Default value

            # Step 1: If "Create Customer" is enabled, create or search customer
            if create_customer:
                # Search for the customer (company) based on sender company name
                if sender_company:
                    customer = self.env['res.partner'].search([('name', '=', sender_company)], limit=1)
                else:
                    customer = self.env['res.partner'].search([('name', '=', sender_name)], limit=1)

                if not customer:
                    # No customer found, create new customer (company)
                    customer_vals = {
                        'name': sender_company if sender_company else sender_name,
                        'phone': record.get('SENDER_MOBILE'),
                        'email': record.get('SENDER_EMAIL'),
                        'street': record.get('SENDER_ADDRESS'),
                        'city': record.get('SENDER_CITY'),
                        'state_id': state_obj.search([('name', '=', record.get('SENDER_STATE'))], limit=1).id,
                        'zip': record.get('SENDER_PINCODE'),
                        'country_id': country_obj.search([('code', '=', record.get('SENDER_COUNTRY_ISO'))], limit=1).id,
                        'company_type': 'company' if sender_company else 'person',
                        'is_indiamart_lead': True,
                    }
                    customer = self.env['res.partner'].create(customer_vals)

                # Step 2: Check if a contact already exists under this customer
                if customer:
                    # Search for the contact under the customer (parent_id) by matching the contact's name
                    contact = self.env['res.partner'].search(
                        [('parent_id', '=', customer.id), ('name', '=', sender_name)], limit=1)

                    # Step 3: If contact doesn't exist under the customer, check if it exists as an individual
                    if not contact:
                        contact = self.env['res.partner'].search(
                            [('name', '=', sender_name), ('parent_id', '=', False)], limit=1)

                        # If contact exists as an individual, link it to the customer (parent_id)
                        if contact:
                            contact.write({'parent_id': customer.id})
                        else:
                            # If no contact found as an individual, create a new contact under the company
                            contact_vals = {
                                'name': sender_name,
                                'phone': record.get('SENDER_MOBILE'),
                                'email': record.get('SENDER_EMAIL'),
                                'street': record.get('SENDER_ADDRESS'),
                                'city': record.get('SENDER_CITY'),
                                'state_id': state_obj.search([('name', '=', record.get('SENDER_STATE'))], limit=1).id,
                                'zip': record.get('SENDER_PINCODE'),
                                'country_id': country_obj.search([('code', '=', record.get('SENDER_COUNTRY_ISO'))],
                                                                 limit=1).id,
                                'parent_id': customer.id,  # Link this contact to the customer
                                'is_indiamart_lead': True,
                            }
                            contact = self.env['res.partner'].create(contact_vals)

            # Step 4: Prepare lead values (this will be linked to the customer)
            lead_vals = {
                'type': 'lead',
                'name': record.get('QUERY_MESSAGE'),
                'create_date': record.get('QUERY_TIME'),
                'phone': record.get('SENDER_MOBILE'),
                'email_from': record.get('SENDER_EMAIL'),
                'partner_name': sender_company or sender_name,
                'contact_name': sender_name,
                'street': record.get('SENDER_ADDRESS'),
                'city': record.get('SENDER_CITY'),
                'state_id': state_obj.search([('name', '=', record.get('SENDER_STATE'))], limit=1).id,
                'zip': record.get('SENDER_PINCODE'),
                'description': record.get('QUERY_MESSAGE'),
                'country_id': country_obj.search([('code', '=', record.get('SENDER_COUNTRY_ISO'))], limit=1).id,
                'is_indiamart_lead': True,
                'team_id': sales_team.id if sales_team else False,
                'partner_id': customer.id if customer else False,  # Link the lead to the customer (parent)
            }
            leads_to_create.append(lead_vals)

        # Step 5: Bulk create all leads at once
        if leads_to_create:
            self.env['crm.lead'].create(leads_to_create)

