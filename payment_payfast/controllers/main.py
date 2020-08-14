# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.website_sale.controllers import main
from odoo.http import request


class PayfastController(http.Controller):
    return_url = '/payfast/return'
    cancel_url = '/payfast/cancel'
    notify_url = '/payfast/notify'

    @http.route('/payfast/notify', type='http', auth='public', methods=['GET', 'POST'], website=True, csrf=False)
    def payfast_notify(self, **post):
        reference = post.get('custom_str1')
        tx = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        if post.get('payment_status') == 'COMPLETE':
            post['pf_payment_id'] = post.get('pf_payment_id')
            post['signature'] = post.get('signature')
            post['reference'] = reference
            post['txn_id'] = tx.id
            post['status'] = 'COMPLETE'
            request.env['payment.transaction'].sudo().form_feedback(post, 'payfast')
            tx.sudo().write({'response_payload': post})
        elif tx:
            tx.sudo().write({'request_payload': post})

    @http.route('/payfast/return', type='http', auth='public', methods=['GET', 'POST'], website=True, csrf=False)
    def return_from_payfast(self, **post):
        return request.redirect('/payment/process')

    @http.route('/payfast/cancel', type='http', auth='public', methods=['GET'], website=True, csrf=False)
    def payfast_cancel_payment(self, **post):
        request.session.update({'payfast_payment_cancel': True})
        return request.redirect('/shop/payment')


class payfastShop(main.WebsiteSale):

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        if 'payfast_payment_cancel' not in request.session.keys():
            return super(payfastShop, self).payment()
        order = request.website.sale_get_order()
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        render_values = self._get_shop_payment_values(order, **post)

        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')

        render_values['errors'] = [['Your payment has been cancelled', 'Please try again']]
        request.session.pop('payfast_payment_cancel')
        return request.render("website_sale.payment", render_values)
