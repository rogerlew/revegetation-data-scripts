from glob import glob
import string
import zipfile
import os
from os.path import exists
from os.path import join as _join

if __name__ == '__main__':
    fp = open('dnbr_extract.log', 'w')

    zip_fns = glob('zip/*/*.zip')
    for zip_fn in zip_fns:
        print(zip_fn)
        zf = zipfile.ZipFile(zip_fn)
        dnbr6 = [f for f in zf.filelist if 'nbr6.tif' in f.filename]
        if [len(dnbr6) > 0]:
            dnbr6 = dnbr6[0]
            filename = dnbr6.filename
            state = filename[:2]

            fix_capitalization = any(tok in string.ascii_uppercase for tok in state)
            if fix_capitalization:
                state = state.lower()

            _dir = f'dnbr6/{state}'
            if not exists(_dir):
                os.makedirs(_dir)
            zf.extract(dnbr6, _dir)

            if fix_capitalization:
                os.rename(_join(_dir, filename), _join(_dir, filename.lower())

            fp.write(f'zip_fn,1\n')
        else:
            fp.write(f'zip_fn,0\n')

