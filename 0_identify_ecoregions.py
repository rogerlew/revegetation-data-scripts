from glob import glob

from wepppy.all_your_base.geo import RasterDatasetInterpolator
import us_eco_l3


if __name__ == "__main__":
    os.chdir('../')

    dnbr6s = glob('/geodata/mtbs/dnbr6/*/*.tif')

    fp = open('ecoregions.tsv', 'w')
    fp.write('dnbr\tfire_centroid_lng\tfire_centroid_lat\tecoregions\n')
    for dnbr6 in dnbr6s:
        rdi = RasterDatasetInterpolator(dnbr6)
        lng, lat = rdi.gt0_centroid
        d = us_eco_l3.identify(lng, lat)
        print(dnbr6, lng, lat, d)
        fp.write(f'{dnbr6}\t{lng}\t{lat}\t{d}\n')
