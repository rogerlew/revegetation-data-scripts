import csv
import json
import pickle
import os
import sys
import shutil
from os.path import exists as _exists
from os.path import split as _split
from os.path import join as _join
import numpy as np
from pprint import pprint

from wepppy.all_your_base.geo import read_raster, RasterDatasetInterpolator
import subprocess
from glob import glob
from collections import Counter
from copy import deepcopy

sys.path.append('/geodata/')

from landfire.disturbance import get_landfire_disturbance_meta


if __name__ == "__main__":
    os.chdir('../')
    wd = os.getcwd()


    fp = open('ecoregions.tsv')
    rdr = csv.DictReader(fp, delimiter='\t')

    for row in rdr:

        
        ecoregions = json.loads(row['ecoregions'].replace("'", '"'))
        for k, ecoregion in ecoregions.items():
            if ecoregion['NA_L3CODE (String)'] == '6.2.7':
                print(row['dnbr'])

