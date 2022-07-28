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
            dist_type = lf_dist_meta[yr][int(k)]['dist_type']
            n = float(len(i[0]))
            res[yr][k] = { _k : v/n for _k, v in Counter(disturbance[i]).most_common() }
    return res


if __name__ == "__main__":
    os.chdir('../')
    wd = os.getcwd()

    skip_processed = False
    run_canopy = False
    run_disturbance = True

    for ecoregion in [7, 6, 10, 11, 13, 12, 9]:
        ecoregion = str(ecoregion)
        fp = open('ecoregions.tsv')
        rdr = csv.DictReader(fp, delimiter='\t')

        for row in rdr:

            try:
                ecoregions = json.loads(row['ecoregions'].replace("'", '"'))
            except:
                print(row['ecoregions'])
                raise
            
            fn = row['dnbr']
            head, tail = _split(fn)
            _tail = tail.split('_')
            fire = _tail[0]
            year = int(_tail[1][:4])
            outdir = _join(wd, f'rasters/{ecoregion}/{year}/{fire}')
            if not _exists(outdir) and skip_processed:
                continue


            print(fire, year)
            fire_fn = _join(outdir, tail)

            if not _exists(outdir):
                os.mkdir(outdir)

            if not _exists(fire_fn):
                state = fire[:2].lower()
                shutil.copyfile(_join(f'/geodata/mtbs/dnbr6/{state}/{tail}'), fire_fn)
             
            dnbr, transform, proj  = read_raster(fire_fn)

            if run_canopy:
                indices = dict(low=np.where(dnbr==2),
                               moderate=np.where(dnbr==3),
                               high=np.where(dnbr==4))

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
                indices_234 = np.where((dnbr >= 2) & (dnbr <= 4))
                disturbance = process_disturbance(outdir, dict(burned=indices_234))
                pprint(disturbance)
                input()

                with open(_join(outdir, 'disturbance.pkl'), 'wb') as pf:
                    pickle.dump(disturbance, pf)

                with open(_join(outdir, 'disturbance_stats.csv'), 'w') as pf:
                    pf.write('year,fire_year,disturbed\n')
                    for yr, d in disturbance.items():
                        disturbed = (1.0 - d['burned'].get(1, 0.0)) * 100.0
                        fy = yr - year
                        pf.write(f'{yr},{fy},{disturbed}\n')

