"""
config.py: Configuration values. Secrets to be handled with Secrets Manager
"""

import logging
import socket

SKID_NAME = "DABS"

AGOL_ORG = "https://utah.maps.arcgis.com"
SENDGRID_SETTINGS = {  #: Settings for SendGridHandler
    "from_address": "noreply@utah.gov",
    "to_addresses": ["jdadams@utah.gov", "rkelson@utah.gov"],
    "prefix": f"{SKID_NAME} on {socket.gethostname()}: ",
}
LOG_LEVEL = logging.DEBUG
LOG_FILE_NAME = "log"

# FEATURE_LAYER_ITEMID = 'bb9518380e0f42ec9a7bd29104762c32' # TESTING
# FEATURE_LAYER_ITEMID = 'b120a5ee1f85468c9367e9a98a2ccf22' # TESTING_4
# FEATURE_LAYER_ITEMID = '96fbd8c210a24ed7be12611502be6c1e' # TESTING_3
# FEATURE_LAYER_ITEMID = '132af29731ca4ae5b505d46a720c9a60' # TESTING_1027
# FEATURE_LAYER_ITEMID = '9b85a1f6ccab4351b7be6c8f37e1095f' # TESTING_20230103
# FEATURE_LAYER_ITEMID = '5708ae24486a4dae810e37fe613a63b6' # The Live Layer!
# FEATURE_LAYER_ITEMID = '3290130042634a34a89547b850d38141' # TESTING_20230207
# FEATURE_LAYER_ITEMID = '20c79ac41afa4431b9f77d201860d8ee' # Test layer 20230418
FEATURE_LAYER_ITEMID = "0909ac49fa404f1793862499e914caef"  # The New Live Layer!
JOIN_COLUMN = "Rec_Number"
ATTACHMENT_LINK_COLUMN = ""
ATTACHMENT_PATH_COLUMN = ""
FIELDS = {
    "Rec_Number": str,
    "Name": str,
    "Address": str,
    "Lic_Address": str,
    "City": str,
    "Zip": str,
}
