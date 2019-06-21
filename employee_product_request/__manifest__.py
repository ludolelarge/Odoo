# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Product Request',
    'version': '1.0',
    'category': 'Employee',
    'author':'Ludovic Lelarge',
    'description': """

    """,
    'website': 'www.eta123.be',
    'depends': ['hr','purchase','stock','account'],
    'data': [
        'data/employee_product_request_data.xml',
        'security/employee_product_request_security.xml',
        'security/ir.model.access.csv',
        'views/employee_product_request_view.xml',
        'views/hr_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 105,
    'license': 'AGPL-3',
}
