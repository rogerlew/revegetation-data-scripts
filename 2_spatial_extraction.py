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


lf_dist_meta = get_landfire_disturbance_meta()


def process_canopy(outdir, indices, start_year=1984, end_year=2017):
    res = {}
    for yr in range(start_year, end_year+1):
        res[yr] = {}
        fn = _join(outdir, f'emapr_canopy_mean_{yr}.tif')
        canopy, transform, proj = read_raster(fn, dtype=np.uint8)
        for k, i in indices.items():
            res[yr][k] = canopy[i]
    return res


def process_canopy_stats(canopy, fire_year, aggregators):
    res = []
    for yr in canopy:
        for k in canopy[yr]:
            series = canopy[yr][k]
            for stat, agg_func in aggregators.items():
                try:
                    value = agg_func(series)
                except:
                    value = None

                res.append(dict(year=yr, fire_year=yr-fire_year, 
                                burn_sev=k, stat=stat, value=value))
    return res

       
def process_disturbance(outdir, indices, start_year=1999, end_year=2020):
    global lf_dist_meta

    res = {}
    for yr in range(start_year, end_year+1):
        res[yr] = {}
        fn = _join(outdir, f'landfire_disturbance_{yr}.tif')
        disturbance, transform, proj = read_raster(fn, dtype=np.int16)
        for k, i in indices.items():
            res[yr][k] = {}
            for _k, v in Counter(disturbance[i]).most_common():
                dist_type = lf_dist_meta[yr][int(_k)]['dist_type']
                res[yr][k][dist_type] = v
    return res


if __name__ == "__main__":
    target_ecoregion = '6.2.7'
    skip_processed = False
    run_canopy = True
    run_disturbance = True

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

        fire_fn = _join(outdir, tail)
        dnbr, _, __ = read_raster(fire_fn)

        lc_year = year
        if year > 2017:
            lc_year = 2017

        lc_fn = _join(outdir, f'emapr_landcover_vote_{lc_year}.tif') 
        if _exists(lc_fn):
            lc, _, __ = read_raster(lc_fn)
        else:
            lc = None

        if run_canopy:
            indices = dict(low=np.where(dnbr==2),
                           moderate=np.where(dnbr==3),
                           high=np.where(dnbr==4))
            if lc is not None:
                indices.update(dict(low_deciduous=np.where((dnbr==2) & (lc==41)),
                           low_evergreen=np.where((dnbr==2) & (lc==42)),
                           low_mixed=np.where((dnbr==2) & (lc==43)),
                           moderate_deciduous=np.where((dnbr==3) & (lc==41)),
                           moderate_evergreen=np.where((dnbr==3) & (lc==42)),
                           moderate_mixed=np.where((dnbr==3) & (lc==43)),
                           high_deciduous=np.where((dnbr==4) & (lc==41)),
                           high_evergreen=np.where((dnbr==4) & (lc==42)),
                           high_mixed=np.where((dnbr==4) & (lc==43)),
                           low_forest=np.where((dnbr==2) & (lc>=41) & (lc<=43)),
                           mod_forest=np.where((dnbr==3) & (lc>=41) & (lc<=43)),
                           high_forest=np.where((dnbr==4) & (lc>=41) & (lc<=43)),
                           ))

            canopy = process_canopy(outdir, indices)
#            print(canopy)

            with open(_join(outdir, 'canopy.pkl'), 'wb') as pf:
                pickle.dump(canopy, pf) 

            canopy_stats = process_canopy_stats(canopy, fire_year=year, aggregators=dict(\
                count=len, 
                mean=np.mean, 
                median=np.median, 
                min=np.min, 
                max=np.max, 
                std=np.std))
#            pprint(canopy_stats)

            with open(_join(outdir, 'canopy_stats.csv'), 'w') as pf:
                wtr = csv.DictWriter(pf, fieldnames=list(canopy_stats[0].keys()))
                wtr.writeheader()
                wtr.writerows(canopy_stats)

        if run_disturbance:
            dist_indices = dict(burned=np.where((dnbr >= 2) & (dnbr <= 4)))

            if lc is not None:
                dist_indices.update(dict(
                           burned_deciduous=np.where((dnbr >= 2) & (dnbr <= 4) & (lc==41)),
                           burned_evergreen=np.where((dnbr >= 2) & (dnbr <= 4) & (lc==42)),
                           burned_mixed=np.where((dnbr >= 2) & (dnbr <= 4) & (lc==43)),
                           burned_forest=np.where((dnbr>=2) & (dnbr<=4) & (lc>=41) & (lc<=43))
                           ))

            print([ (k, len(v[0])) for k, v in dist_indices.items()])

            disturbance = process_disturbance(outdir, dist_indices)

            with open(_join(outdir, 'disturbance.json'), 'w') as pf:
                json.dump(disturbance, pf)

#            with open(_join(outdir, 'disturbance_stats.csv'), 'w') as pf:
#                pf.write('year,fire_year,disturbed\n')
#                for yr, d in disturbance.items():
#                    disturbed = (1.0 - d['burned'].get(1, 0.0)) * 100.0
#                    fy = yr - year
#                    pf.write(f'{yr},{fy},{disturbed}\n')

