#!/usr/bin/env python
# * coding: utf8 *
"""
Run the SKIDNAME script as a cloud function.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import arcgis
from palletjack import (FeatureServiceInlineUpdater, FeatureServiceOverwriter,GSheetLoader)
from palletjack.transform import APIGeocoder
from supervisor.message_handlers import SendGridHandler
from supervisor.models import MessageDetails, Supervisor

#: This makes it work when calling with just `python <file>`/installing via pip and in the gcf framework, where
#: the relative imports fail because of how it's calling the function.
try:
    from . import config, version
except ImportError:
    import config
    import version


def _get_secrets():
    """A helper method for loading secrets from either a GCF mount point or the local src/skidname/secrets/secrets.json file

    Raises:
        FileNotFoundError: If the secrets file can't be found.

    Returns:
        dict: The secrets .json loaded as a dictionary
    """

    secret_folder = Path('/secrets')

    #: Try to get the secrets from the Cloud Function mount point
    if secret_folder.exists():
        return json.loads(Path('/secrets/app/secrets.json').read_text(encoding='utf-8'))

    #: Otherwise, try to load a local copy for local development
    secret_folder = (Path(__file__).parent / 'secrets')
    if secret_folder.exists():
        return json.loads((secret_folder / 'secrets.json').read_text(encoding='utf-8'))

    raise FileNotFoundError('Secrets folder not found; secrets not loaded.')


def _initialize(log_path, sendgrid_api_key):
    """A helper method to set up logging and supervisor

    Args:
        log_path (Path): File path for the logfile to be written
        sendgrid_api_key (str): The API key for sendgrid for this particular application

    Returns:
        Supervisor: The supervisor object used for sending messages
    """

    skid_logger = logging.getLogger(config.SKID_NAME)
    skid_logger.setLevel(config.LOG_LEVEL)
    palletjack_logger = logging.getLogger('palletjack')
    palletjack_logger.setLevel(config.LOG_LEVEL)

    cli_handler = logging.StreamHandler(sys.stdout)
    cli_handler.setLevel(config.LOG_LEVEL)
    formatter = logging.Formatter(
        fmt='%(levelname)-7s %(asctime)s %(name)15s:%(lineno)5s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )
    cli_handler.setFormatter(formatter)

    log_handler = logging.FileHandler(log_path, mode='w')
    log_handler.setLevel(config.LOG_LEVEL)
    log_handler.setFormatter(formatter)

    skid_logger.addHandler(cli_handler)
    skid_logger.addHandler(log_handler)
    palletjack_logger.addHandler(cli_handler)
    palletjack_logger.addHandler(log_handler)

    #: Log any warnings at logging.WARNING
    #: Put after everything else to prevent creating a duplicate, default formatter
    #: (all log messages were duplicated if put at beginning)
    logging.captureWarnings(True)

    skid_logger.debug('Creating Supervisor object')
    skid_supervisor = Supervisor(handle_errors=False)
    sendgrid_settings = config.SENDGRID_SETTINGS
    sendgrid_settings['api_key'] = sendgrid_api_key
    skid_supervisor.add_message_handler(
        SendGridHandler(
            sendgrid_settings=sendgrid_settings, client_name=config.SKID_NAME, client_version=version.__version__
        )
    )

    return skid_supervisor


def _remove_log_file_handlers(log_name, loggers):
    """A helper function to remove the file handlers so the tempdir will close correctly

    Args:
        log_name (str): The logfiles filename
        loggers (List<str>): The loggers that are writing to log_name
    """

    for logger in loggers:
        for handler in logger.handlers:
            try:
                if log_name in handler.stream.name:
                    logger.removeHandler(handler)
                    handler.close()
            except Exception as error:
                pass

def process():
    """The main function that does all the work.
    """

    #: Set up secrets, tempdir, supervisor, and logging
    start = datetime.now()

    secrets = SimpleNamespace(**_get_secrets())

    with TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)
        log_name = f'{config.LOG_FILE_NAME}_{start.strftime("%Y%m%d-%H%M%S")}.txt'
        log_path = tempdir_path / log_name

        skid_supervisor = _initialize(log_path, secrets.SENDGRID_API_KEY)
        module_logger = logging.getLogger(config.SKID_NAME)

        #: Get our GIS object via the ArcGIS API for Python
        gis = arcgis.gis.GIS(config.AGOL_ORG, secrets.AGOL_USER, secrets.AGOL_PASSWORD)

        #########################################################################
        #: Use the various palletjack classes and other code to do your work here
        #########################################################################
        import pandas as pd
        import numpy as np

        #: Read data from Google Sheet
        module_logger.info('Reading in DABS data from Google Sheet ...')
        loader = GSheetLoader(secrets.SERVICE_ACCOUNT_JSON)
        dabs_df = loader.load_specific_worksheet_into_dataframe(secrets.SHEET_ID, 'TEST_TAB', by_title=True)
        
        #: Seperate rows to geocode if ACTION.casefold() == 'add', else put them into the removes dataframe
        adds_df = dabs_df[dabs_df['ACTION'].str.casefold() == 'add']
        adds_df.drop(['ACTION'], axis='columns', inplace=True)
        removes_df = dabs_df[dabs_df['ACTION'].str.casefold() == 'remove']

        #: OVERWRITE/TRUNCATE AND LOAD METHOD
        #: Pull down original data and copy to working dataframe
        feature_layer_item = gis.content.get(config.FEATURE_LAYER_ITEMID)
        feature_layer = arcgis.features.FeatureLayer.fromitem(feature_layer_item)
        featureset = feature_layer.query()
        original_dataframe = featureset.sdf
        working_dataframe = original_dataframe.copy()

        #: Convert to SEDF in 4326 spatial reference using lat/lon fields in the data
        module_logger.info('Converting data to SEDF in 4326 spatial reference ...')
        pd.DataFrame.spatial.from_xy(df=working_dataframe, x_column='Point_X', y_column='Point_Y', sr=4326)
        
        #: Remove rows for licenses in removes_df
        before_count = len(working_dataframe.index)
        module_logger.info('Deleting removed rows from dataframe ...')
        remove_licenses = removes_df['Lic_Number'].tolist()
        working_dataframe = working_dataframe[~working_dataframe['Lic_Number'].isin(remove_licenses)]
        after_count = len(working_dataframe.index)
        change = before_count - after_count
        module_logger.info(f'Removed {change} rows from working dataframe ...')
        
        #: Geocode rows if ACTION.casefold() == 'add', else put them into the removes dataframe
        if len(adds_df.index) > 0:
            module_logger.info('Geocoding new rows ...')
            geocoder = APIGeocoder(secrets.GEOCODE_KEY)
            geo_df = geocoder.geocode_dataframe(adds_df, 'Address', 'Zip', 4326, rate_limits=(0.015, 0.03), acceptScore=90)
            valid = geo_df.spatial.validate()
            print(f'Is geo_df spatial?: {valid}')
            # geo_df = geocoder.geocode_dataframe(adds_df, 'Address', 'Zip', 3857, rate_limits=(0.015, 0.03), **{"acceptScore": 90})

            #: Add rows to AGOL layer (include bad geocodes for now, then manually edit them)
            columns = ['Lic_Number', 'Name', 'Address', 'City', 'Zip', 'SHAPE']
            geo_df_to_add = geo_df[columns]

            #: Calculate appropriate OIDs on the geocoded dataframe (use original_dataframe to be safe)
            # max_OID = original_dataframe['OBJECTID'].max()
            # geo_df_to_add.insert(0, 'OBJECTID', range(max_OID + 1, max_OID + len(geo_df_to_add) + 1))

            #: Combine working dataframe with geocoded dataframe
            combined_dataframe = pd.concat([working_dataframe, geo_df_to_add])

            #: Convert NaNs to 0s and make dtype 'int' on Comp_Zone
            combined_dataframe['Comp_Zone'].fillna(0, inplace=True)
            combined_dataframe['Comp_Zone'] = combined_dataframe['Comp_Zone'].astype('int')

            #: Convert NaNs to 0s for double fields (Point_X and Point_Y)
            combined_dataframe['Point_X'].fillna(0, inplace=True)
            combined_dataframe['Point_Y'].fillna(0, inplace=True)

            #: Convert remaining NaNs to empty strings in string fields (County, Suite_Unit, Lic_Type, Lic_Descr, Renew_Date, Lic_Group, Comp_Group, Comp_Needed,  )
            combined_dataframe = combined_dataframe.replace(np.nan, '', regex=True)

            #: Deduplicate Lic_Number field
            module_logger.info(f'Combined dataframe has {len(combined_dataframe.index)} rows ...')
            lic_nums = combined_dataframe['Lic_Number']
            dupes = combined_dataframe[lic_nums.isin(lic_nums[lic_nums.duplicated()])].sort_values("Lic_Number")
            # module_logger.info(dupes.head(10))
            if len(dupes.index) > 0:
                module_logger.info(f'Found {len(dupes.index)} duplicates in newly combined data, dropping all but last occurrences ...')
                combined_dataframe.drop_duplicates('Lic_Number', keep='last', inplace=True)
                module_logger.info(f'Combined dataframe now has {len(combined_dataframe.index)} rows ...')
        else:
            module_logger.info('No new rows to geocode ...')
            combined_dataframe = working_dataframe

        
        #: Backup data and overwrite existing feature service
        fail_dir = r'C:\Temp'
        overwriter = FeatureServiceOverwriter(gis)
        overwriter.truncate_and_load_feature_service(config.FEATURE_LAYER_ITEMID, combined_dataframe, fail_dir, layer_index=0)
           
        
        end = datetime.now()

        summary_message = MessageDetails()
        summary_message.subject = f'{config.SKID_NAME} Update Summary'
        summary_rows = [
            f'{config.SKID_NAME} update {start.strftime("%Y-%m-%d")}',
            '=' * 20,
            '',
            f'Start time: {start.strftime("%H:%M:%S")}',
            f'End time: {end.strftime("%H:%M:%S")}',
            f'Duration: {str(end-start)}',
            #: Add other rows here containing summary info captured/calculated during the working portion of the skid,
            #: like the number of rows updated or the number of successful attachment overwrites.
        ]

        summary_message.message = '\n'.join(summary_rows)
        summary_message.attachments = tempdir_path / log_name

        # skid_supervisor.notify(summary_message)

        #: Remove file handler so the tempdir will close properly
        loggers = [logging.getLogger(config.SKID_NAME), logging.getLogger('palletjack')]
        _remove_log_file_handlers(log_name, loggers)




def main(event, context):  # pylint: disable=unused-argument
    """Entry point for Google Cloud Function triggered by pub/sub event

    Args:
         event (dict):  The dictionary with data specific to this type of
                        event. The `@type` field maps to
                         `type.googleapis.com/google.pubsub.v1.PubsubMessage`.
                        The `data` field maps to the PubsubMessage data
                        in a base64-encoded string. The `attributes` field maps
                        to the PubsubMessage attributes if any is present.
         context (google.cloud.functions.Context): Metadata of triggering event
                        including `event_id` which maps to the PubsubMessage
                        messageId, `timestamp` which maps to the PubsubMessage
                        publishTime, `event_type` which maps to
                        `google.pubsub.topic.publish`, and `resource` which is
                        a dictionary that describes the service API endpoint
                        pubsub.googleapis.com, the triggering topic's name, and
                        the triggering event type
                        `type.googleapis.com/google.pubsub.v1.PubsubMessage`.
    Returns:
        None. The output is written to Cloud Logging.
    """

    #: This function must be called 'main' to act as the Google Cloud Function entry point. It must accept the two
    #: arguments listed, but doesn't have to do anything with them (I haven't used them in anything yet).

    #: Call process() and any other functions you want to be run as part of the skid here.
    process()

#: Putting this here means you can call the file via `python main.py` and it will run. Useful for pre-GCF testing.
if __name__ == '__main__':
    process()
