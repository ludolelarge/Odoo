# -*- coding: utf-8 -*-

{
    "name": "Truck Management",
    "version": "1.0",
    "author" : "Ludovic Lelarge",
    "website": "www.eta123.be",
    "description": """
    
    """,

    "category": "Transport",
    "depends": [
        "product",
    ],
    "data": [
       'security/truck_mgmt_security.xml',
       'security/ir.model.access.csv',
       'data/truck_mgmt_data.xml',
       'views/truck_mgmt_menu.xml',
       'views/truck_mgmt.xml',

    ],
    "active": False,
    "installable": True,
}
