# Author: Teemu Ikonen <teemu.ikonen@psi.ch>
# Copyright: 2010 Paul Scherrer Institute
# License:
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as
#   published by the Free Software Foundation; either version 2 of
#   (the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
#   02111-1307  USA

import cbf, re, sys
import numpy as np
import matplotlib.pylab as plt
from optparse import OptionParser
from xformats.detformats import write_pnglog

description="Show information about a CBF file"

usage="%prog <file.cbf>"


def read_mask(fname):
    """Read a mask (Numpy bool array) from an image file"""
    import matplotlib.image
    mfloat = matplotlib.image.imread(fname)
    if len(mfloat.shape) == 2:
        mask = (mfloat[:,:] != 0.0)
    else:
        mask = (mfloat[:,:,0] != 0.0)
    return mask


def parse_center(center_str):
    mob = re.match(' *([0-9.]+)[,]([0-9.]+) *', center_str)
    if mob is None or len(mob.groups()) != 2:
        return None
    else:
        return (float(mob.group(1)), float(mob.group(2)))


def mark_cross(center, **kwargs):
    """Mark a cross. Correct for matplotlib imshow funny coordinate system.
    """
    N = 20
    plt.hold(1)
    plt.axhline(y=center[1]-0.5, **kwargs)
    plt.axvline(x=center[0]-0.5, **kwargs)


def write_to_temp(fin):
    import tempfile
    tf = tempfile.NamedTemporaryFile(suffix=".cbfdump.cbf", delete=False)
    tf.file.write(fin.read())
    fin.close()
    tf.file.close()
    return tf.name


def main():
    oprs = OptionParser(usage=usage, description=description)
    oprs.add_option("-m", "--maskfile",
        action="store", type="string", dest="maskfile", default=None)
    oprs.add_option("-c", "--cross",
        action="store", type="string", dest="center_str", default=None)
    oprs.add_option("-o", "--output",
        action="store", type="string", dest="pngfile", default=None,
        help="Write the logarithm of the frame to a PNG file.")
    (opts, args) = oprs.parse_args()
    if(len(args) < 1):
        oprs.error("Input file argument required")

    center = None
    if opts.center_str is not None:
        center = parse_center(opts.center_str)
        if center is None:
            print >> sys.stderr, oprs.format_help()
            print >> sys.stderr, "Could not parse the center."
            sys.exit(1)
        print("Marking point " + str(center))

    mask = None
    if opts.maskfile != None:
        mask = read_mask(opts.maskfile)

    filename = args[0]
    file_is_temporary = False
    # FIXME: Use magic to detect file type.
    if filename.endswith(".bz2"):
        import bz2
        fin = bz2.BZ2File(filename, mode='r')
        fname = write_to_temp(fin)
        file_is_temporary = True
    elif filename.endswith(".gz"):
        import gzip
        fin = gzip.GzipFile(filename, mode='r')
        fname = write_to_temp(fin)
        file_is_temporary = True
    else:
        fname = filename

    h = cbf.CBF()
    h.read_file(fname)
    h.rewind_datablock()
    print("Found %s datablocks" % h.count_datablocks())
    h.select_datablock(0)
    print("Zeroth is named %s" % h.datablock_name())
    h.rewind_category()
    categories = h.count_categories()
    for i in range(categories):
        print("Category: %d" % i),
        h.select_category(i)
        category_name = h.category_name()
        print("Name: %s" % category_name),
        rows=h.count_rows()
        print("Rows: %d" % rows),
        cols = h.count_columns()
        print("Cols: %d" % cols)
        h.rewind_column()
        ss = 'Row#'
        while True:
            colname = h.column_name()
            ss += (' "%s"' % colname)
            try:
               h.next_column()
            except:
                break
        print(ss)
        ll = ''
        for i in range(len(ss)):
            ll += '-'
        print(ll)
        for j in range(rows):
            h.select_row(j)
            print("%d:" % j),
            h.rewind_column()
            for k in range(cols):
                h.select_column(k)
                typeofvalue=h.get_typeofvalue()
                if typeofvalue.find("bnry") > -1:
                    print("<binary>")
                    s=h.get_arrayparameters()
                    print(s)
                    d, valtype = h.get()
                    print d.shape
                    if len(d.shape) == 1:
                        plt.semilogy(d)
                        plt.show()
                    elif len(d.shape) == 2:
                        if mask is not None:
                            logim = np.log(np.abs(d*mask)+1)
                        else:
                            logim = np.log(np.abs(d)+1)
                        if opts.pngfile is not None:
                            write_pnglog(logim, opts.pngfile)
                        plt.imshow(logim, interpolation='nearest')
                        if center is not None:
                            mark_cross(center, color='white')
                        plt.show()
                    else:
                        print("Cannot show 3D arrays")
                else:
                    value=h.get_value()
                    print('"%s":%s, ' % (value, typeofvalue)),
            print('')
        print('')
    del(h)


if __name__ == "__main__":
    main()

