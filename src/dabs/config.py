"""
config.py: Configuration values. Secrets to be handled with Secrets Manager
"""

import logging
import socket

SKID_NAME = 'DABS'

AGOL_ORG = 'https://utah.maps.arcgis.com'
SENDGRID_SETTINGS = {  #: Settings for SendGridHandler
    'from_address': 'noreply@utah.gov',
    'to_addresses': 'eneemann@utah.gov',
    'prefix': f'{SKID_NAME} on {socket.gethostname()}: ',
}
LOG_LEVEL = logging.DEBUG
LOG_FILE_NAME = 'log'

FEATURE_LAYER_ITEMID = 'bb9518380e0f42ec9a7bd29104762c32'
# FEATURE_LAYER_ITEMID = '20f8b7b52f3042de9f41081d605dcf08'
JOIN_COLUMN = 'Lic_Number'
ATTACHMENT_LINK_COLUMN = ''
ATTACHMENT_PATH_COLUMN = ''
FIELDS = {
    'Lic_Number': str,
    'Name': str,
    'Address': str,
    'City': str,
    'Zip': str,
}
