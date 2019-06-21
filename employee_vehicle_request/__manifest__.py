# -*- coding: utf-8 -*-

{
    'name': 'Employee Vehicle Request',
    'version': '10.0.1.0.0',
    'summary': """Manage Vehicle Requests From Employee""",
    'description': """This module is used for manage vehicle requests from employee.
                   This module also checking the vehicle availability at the requested time slot.
                   
                   Fork from Cybrosys Employee Vehicule Request.     
                                 
                   Adding if allday, check only date, if not check datetime.     
                                 
                   Adding check_user_group() to allow modify datetime only by hr.group_hr_manager.  
                                    
                   Adding in "Plus" retuned for multi selection.   
                                   
                   Adding in "Plus" unlink to remove fleet.reserved before remove employee.fleet.     
                                 
                   Adding web_timeline view.""",
    'category': 'Human Resources',
    'author': 'Ludovic Lelarge',
    'company': 'ETA123',
    'website': "www.eta123.be",
    'depends': ['base', 'hr', 'fleet','web_timeline'],
    'data': [
        'data/data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/employee_fleet_view.xml',
    ],
    'images': [''],
    'license': 'LGPL-3',
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
