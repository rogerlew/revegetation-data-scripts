import uuid
from glob import glob

from wepppy.all_your_base.geo import RasterDatasetInterpolator
import us_eco_l3

import json

import requests
import shutil
from enum import Enum
import csv
import os
import sys
from os.path import split as _split
from os.path import join as _join
from os.path import exists, dirname

import warnings

import numpy as np
import pandas as pd

import netCDF4

from wepppy.all_your_base import SCRATCH


class GridMetVariable(Enum):
    Precipitation = 1
    MinimumTemperature = 2
    MaximumTemperature = 3
    SurfaceRadiation = 4
#    PalmarDroughtSeverityIndex = 5
    PotentialEvapotranspiration = 6
    BurningIndex = 7


_var_meta = {
    GridMetVariable.Precipitation: ('pr', 'precipitation_amount'),
    GridMetVariable.MinimumTemperature: ('tmmn', 'air_temperature'),
    GridMetVariable.MaximumTemperature: ('tmmx', 'air_temperature'),
    GridMetVariable.SurfaceRadiation: ('srad', 'surface_downwelling_shortwave_flux_in_air'),
#    GridMetVariable.PalmarDroughtSeverityIndex: ('pdsi', 'palmer_drought_severity_index'),
    GridMetVariable.PotentialEvapotranspiration: ('pet', 'potential_evapotranspiration'),
    GridMetVariable.BurningIndex: ('bi', 'burning_index_g'),
}

# http://thredds.northwestknowledge.net:8080/thredds/ncss/MET/bi/bi_2019.nc?var=burning_index_g

def _retrieve(gridvariable: GridMetVariable, bbox, year):
    global _var_meta

    abbrv, variable_name = _var_meta[gridvariable]

    assert len(bbox) == 4
    west, north, east, south = [float(v) for v in bbox]
    assert east > west
    assert south < north

    url = 'http://thredds.northwestknowledge.net:8080/thredds/ncss/MET/{abbrv}/{abbrv}_{year}.nc?' \
          'var={variable_name}&' \
          'north={north}&west={west}&east={east}&south={south}&' \
          'disableProjSubset=on&horizStride=1&' \
          'time_start={year}-01-01T00%3A00%3A00Z&' \
          'time_end={year}-12-31T00%3A00%3A00Z&' \
          'timeStride=1&accept=netcdf' \
        .format(year=year, east=east, west=west, south=south, north=north,
                abbrv=abbrv, variable_name=variable_name)

    referer = 'https://rangesat.nkn.uidaho.edu'
    s = requests.Session()
    response = s.get(url, headers={'referer': referer}, stream=True)
    id = uuid.uuid4()
    with open(_join(SCRATCH, '%s.nc' % id), 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response

    return id


def retrieve_timeseries(variables, lng, lat, start_year, end_year, outdir):
    global _var_meta
    ll_x, ll_y = lng, lat
    ur_x, ur_y = lng, lat

    ll_x -= 0.04
    ll_y -= 0.04
    ur_x += 0.04
    ur_y += 0.04

    bbox = [ll_x, ur_y, ur_x, ll_y]

    start_year = int(start_year)
    end_year = int(end_year)

    assert start_year <= end_year

    df = pd.DataFrame()
    for gridvariable in variables:
        d = []
        for year in range(start_year, end_year + 1):
            print(gridvariable, year)
            id = _retrieve(gridvariable, bbox, year)
            fn = _join(SCRATCH, '%s.nc' % id)

            try:
                rds = RasterDatasetInterpolator(fn, proj='EPSG:4326')
                ts = rds.get_location_info(lng, lat, 'nearest')

                abbrv, variable_name = _var_meta[gridvariable]
                ds = netCDF4.Dataset(fn)
                variable = ds.variables[variable_name]
                desc = variable.description
                units = variable.units
                scale_factor = getattr(variable, 'scale_factor', 1.0)
                add_offset = getattr(variable, 'add_offset', 0.0)

                if ts is not None:
                    ts = np.array(ts, dtype=np.float64)
                    ts *= scale_factor
                    ts += add_offset
                    units = variable.units
                    if 'K' == variable.units:
                        ts -= 273.15
                        units = 'C'

                    d.append(ts)

                os.remove(fn)
            except:
                warnings.warn(
                    'Error retrieving ({}, {}, {})'.format(gridvariable, year, fn)
                )
                # os.remove(fn)
                raise

        df[variable_name] = np.concatenate(d)

    df.insert(0, 'date', pd.period_range(
                 start=f'1/1/{start_year}', periods=len(df.index), freq="D"))
 
    df.to_csv(_join(outdir, 'daily_climate.csv'))
    
    return df



if __name__ == "__main__":
    start_year = 1979
    end_year = 2021

    target_ecoregion = '6.2.7'

    os.chdir('../')
    wd = os.getcwd()


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

        lng, lat = float(row['fire_centroid_lng']), float(row['fire_centroid_lat'])

        if exists(_join(outdir, 'daily_climate.csv')):
            continue

        print(outdir)
        d = retrieve_timeseries([var for var in GridMetVariable],
                                lng, lat, start_year, end_year, outdir)

