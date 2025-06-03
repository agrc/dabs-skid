# DABS Skid

[![Push Events](https://github.com/agrc/dabs-skid/actions/workflows/push.yml/badge.svg)](https://github.com/agrc/dabs-skid/actions/workflows/push.yml)

This skid updates a monthly tab in a google sheet with locations to add and remove from the [DABS_GIS/DABS_All_Licenses feature service](https://utah.maps.arcgis.com/home/item.html?id=0909ac49fa404f1793862499e914caef&sublayer=0) in AGOL. Rick runs this locally as needed.

## Development Setup

1. Create new environment for the project and install Python
   - `conda create --name dabs-skid python=3.11`
   - `conda activate dabs-skid`
1. Install the skid in your conda environment as an editable package for development
   - This will install all the normal and development dependencies (palletjack, supervisor, etc)
   - `cd c:\path\to\repo`
   - `pip install -e .[tests]`
   - add any additional project requirements to the `setup.py:install_requires` list
1. Set secrets
   - Duplicate `src/secrets/secrets_template.json` to `src/secrets/secrets.json` and fill in the values
