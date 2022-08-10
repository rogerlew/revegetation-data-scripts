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

# https://github.com/rogerlew/all_your_base
from wepppy.all_your_base.geo import (
    raster_stacker, read_raster, RasterDatasetInterpolator
)
import subprocess
from glob import glob
from collections import Counter
from copy import deepcopy

products = [
            dict(src='/geodata/islay.ceoas.oregonstate.edu/v1/canopy/mean/canopy_{year}_mean.tif',
                 dst='emapr_canopy_mean_{year}.tif',
                 start_year=1984, end_year=2017),
            dict(src='/geodata/islay.ceoas.oregonstate.edu/v1/landcover/vote/landcover_{year}_vote.tif',
                 dst='emapr_landcover_vote_{year}.tif',
                 start_year=1984, end_year=2017),
            dict(src='/geodata/landfire/disturbance/*{year}*/Tif/*.tif',
                 dst='landfire_disturbance_{year}.tif',
                 start_year=1999, end_year=2020),
            dict(src='/geodata/rap/v3/vegetation-cover-v3-{year}.tif',
                 dst='rap_vegetation_cover_v3_{year}.tif',
                 start_year=1986, end_year=2021)
           ]


if __name__ == "__main__":
    target_ecoregion = '6.2.7'

    os.chdir('../')
    wd = os.getcwd()

    skip_processed = False

    fp = open('ecoregions.tsv')
    rdr = csv.DictReader(fp, delimiter='\t')

    for i, row in enumerate(rdr):

        ecoregions = json.loads(row['ecoregions'].replace("'", '"'))

        is627 = False
        for k, ecoregion in ecoregions.items():
            print( ecoregion['NA_L3CODE (String)'])
            if ecoregion['NA_L3CODE (String)'] == target_ecoregion:
                is627 = True
 
        if not is627:
            continue
        
        fn = row['dnbr']
        head, tail = _split(fn)
        _tail = tail.split('_')
        fire = _tail[0]
        year = int(_tail[1][:4])
        outdir = _join(wd, f'rasters2/{target_ecoregion}/{fire}')

        print(fire, year)
        fire_fn = _join(outdir, tail)

        if not _exists(outdir):
            os.makedirs(outdir)

        if not _exists(fire_fn):
            state = fire[:2].lower()
            shutil.copyfile(_join(f'/geodata/mtbs/dnbr6/{state}/{tail}'), fire_fn)
        
        for product in products:
            src = product['src']
            dst = product['dst']
            start_year = product['start_year']
            end_year = product['end_year']

            for year in range(start_year, end_year+1):
                src_fn = glob(src.format(year=year))
                assert len(src_fn) == 1, (year, src, src_fn)
                src_fn = src_fn[0]

                dst_fn = _join(outdir, dst.format(year=year))
                print(src_fn, fire_fn, dst_fn)
                raster_stacker(src_fn, fire_fn, dst_fn)

