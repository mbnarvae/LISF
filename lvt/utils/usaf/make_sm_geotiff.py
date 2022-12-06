#!/usr/bin/env python3

#-----------------------BEGIN NOTICE -- DO NOT EDIT-----------------------
# NASA Goddard Space Flight Center
# Land Information System Framework (LISF)
# Version 7.4
#
# Copyright (c) 2022 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#-------------------------END NOTICE -- DO NOT EDIT-----------------------

"""
#------------------------------------------------------------------------------
#
# SCRIPT: make_sm_geotiff.py
#
# PURPOSE:  Extracts soil moisture climatology, soil moisture anomaly, and
# latitude/longitude information from netCDF files, and converts to GeoTIFF.
#
# REQUIREMENTS as of 25 June 2021:
# * Python 3.8 or higher.
# * UNIDATA NetCDF4 Python library (for reading netCDF4 files)
# * GDAL Python library (bundled in osgeo package).
#
# REVISION HISTORY:
# 25 June 2021: Eric Kemp (SSAI), first version, based on code provided by
#               Sujay Kumar (NASA GSFC).
# 28 June 2021: Eric Kemp (SSAI), add support for each soil layer.
# 29 June 2021: Eric Kemp (SSAI), added processing for climatologies for all
#               months.  Also tweaked pylint checking for netCDF4 module.
# 09 July 2021: Eric Kemp (SSAI), added metadata to GeoTIFF files describing
#               raster fields.  Also changed numbering of soil layers from
#               0-3 to 1-4.
# 05 Dec 2022:  Eric Kemp (SSAI), updates to improve pylint score.
#
#------------------------------------------------------------------------------
"""

# Standard modules
import datetime
import sys

# Third party modules
# NOTE: pylint cannot see the Dataset class in netCDF4 since the latter is
# not written in Python.  We therefore disable a check for this line to
# avoid a known false alarm.
# pylint: disable=no-name-in-module
from netCDF4 import Dataset as nc4_dataset
# pylint: enable=no-name-in-module
from osgeo import gdal, osr

def _usage():
    """Print command line usage."""
    txt = f"[INFO] Usage: {sys.argv[0]} ldtfile tsfile finalfile"
    txt += " anomaly_gt_prefix climo_gt_prefix LSM yyyymmddhh"
    print(txt)
    print("[INFO]  where:")
    print("[INFO]   ldtfile: LDT parameter file with full lat/lon data")
    print("[INFO]   tsfile: LVT 'TS' soil moisture anomaly file")
    print("[INFO]   finalfile: LVT 'FINAL' soil moisture anomaly file")
    print("[INFO]   anomaly_gt_prefix: prefix for new anomaly GeoTIFF files")
    print("[INFO]   climo_gt_prefix: prefix for new climatology GeoTIFF files")
    print("[INFO]   LSM: land surface model")
    print("[INFO]   yyyymmddhh: Valid date and time (UTC)")

def _read_cmd_args():
    """Read command line arguments."""
    # Check if argument count is correct
    if len(sys.argv) != 8:
        print("[ERR] Invalid number of command line arguments!")
        _usage()
        sys.exit(1)

    # Check if LDT parameter file can be opened.
    _ldtfile = sys.argv[1]
    ncid_ldt = nc4_dataset(_ldtfile, mode='r', format='NETCDF4_CLASSIC')
    ncid_ldt.close()

    # Check of LVT TS anomaly file can be opened
    _tsfile = sys.argv[2]
    ncid_lvt = nc4_dataset(_tsfile, mode='r', format='NETCDF4_CLASSIC')
    ncid_lvt.close()

    # Check of LVT FINAL anomaly file can be opened
    _finalfile = sys.argv[3]
    ncid_lvt = nc4_dataset(_finalfile, mode='r', format='NETCDF4_CLASSIC')
    ncid_lvt.close()

    _outfile_anomaly_prefix = sys.argv[4]
    _outfile_climo_prefix = sys.argv[5]
    _lsm = sys.argv[6]
    _yyyymmddhh = sys.argv[7]

    if _lsm not in ["noah39", "noahmp401", "jules50"]:
        print(f"[ERR] Unknown LSM {_lsm}")
        print("Options are noah39, noahmp401, jules50")
        sys.exit(1)

    cmd_args = {
        "ldtfile" : _ldtfile,
        "tsfile" : _tsfile,
        "finalfile" : _finalfile,
        "outfile_anomaly_prefix" : _outfile_anomaly_prefix,
        "outfile_climo_prefix" : _outfile_climo_prefix,
        "lsm" : _lsm,
        "yyyymmddhh" : _yyyymmddhh,
    }
    return cmd_args

def _make_geotransform(lon, lat, nxx, nyy):
    """Set affine transformation from image coordinate space to georeferenced
    space.  See https://gdal.org/tutorials/geotransforms_tut.html"""
    xmin = lon.min()
    xmax = lon.max()
    ymin = lat.min()
    ymax = lat.max()
    xres = (xmax - xmin) / float(nxx)
    yres = (ymax - ymin) / float(nyy)
    # Sujay's original code
    #geotransform = (xmax, xres, 0, ymin, 0, -yres)
    # Eric's code...Based on gdal.org/tutorials/geotransforms_tut.html
    # xmin is x-coordinate of upper-left corner of upper-left pixel
    # ymax is y-coordinate of upper-left corner of upper-left pixel
    # Third variable is row rotation, set to zero for north-up image
    # Fourth variable is column rotation, set to zero
    # Sixth variable is n-s pixel resolution (negative for north-up image)
    _geotransform = (xmin, xres, 0, ymax, 0, -1*yres)
    #print(_geotransform)
    return _geotransform

def _create_output_raster(outfile, nxx, nyy, _geotransform, var1):
    """Create the output raster file (the GeoTIFF), including map projection"""
    _output_raster = gdal.GetDriverByName('GTiff').Create(outfile,
                                                          nxx, nyy, 1,
                                                          gdal.GDT_Float32)

    _output_raster.SetGeoTransform(_geotransform)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326) # Corresponds to WGS 84
    _output_raster.GetRasterBand(1).SetNoDataValue(-9999)
    _output_raster.SetProjection(srs.ExportToWkt())
    _output_raster.GetRasterBand(1).WriteArray(var1)

    return _output_raster

def _set_metadata(varname_arg, soil_layer, model, \
                  yyyymmddhh_arg, \
                  climomonth=None):
    """Create metadata dictionary for output to GeoTIFF file"""
    validdt = datetime.datetime(year=int(yyyymmddhh_arg[0:4]),
                                month=int(yyyymmddhh_arg[4:6]),
                                day=int(yyyymmddhh_arg[6:8]),
                                hour=int(yyyymmddhh_arg[8:10]))
    _metadata = { 'varname' : f'{varname_arg}',
                  'units' : 'm3/m3',
                  'soil_layer' : f'{soil_layer}',
                  'land_surface_model' : f'{model}' }
    if climomonth is None:
        time_string = f"Valid {validdt.hour:02}Z {validdt.day} "
        time_string += f"{_MONTHS[validdt.month-1]} {validdt.year:04}"
        _metadata["valid_date_time"] = time_string
    else:
        time_string = f"Updated {validdt.hour:02}Z {validdt.day} "
        time_string += f"{_MONTHS[validdt.month-1]} {validdt.year:04}"
        _metadata["update_date_time"] = time_string
        _metadata["climo_month"] = climomonth

    return _metadata

_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
           "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

_SOIL_LAYERS = {
    "noah39" :    ["0-0.1 m", "0.1-0.4 m",  "0.4-1.0 m",  "1.0-2.0 m"],
    "noahmp401" : ["0-0.1 m", "0.1-0.4 m",  "0.4-1.0 m",  "1.0-2.0 m"],
    "jules50" :   ["0-0.1 m", "0.1-0.35 m", "0.35-1.0 m", "1.0-3.0 m"],
}

def _proc_sm_anomalies(cmd_args, longitudes, latitudes):
    """Process soil moisture anomalies"""
    # Next, fetch the soil moisture anomalies from the LVT 'TS' file.
    ncid = nc4_dataset(cmd_args["tsfile"], 'r', format='NETCDF4')
    for i in range(0, 4): # Loop across four LSM layers
        sm_anomalies = ncid.variables["SoilMoist"][i,:,:]
        nrows, ncols = sm_anomalies.shape

        _soil_layer = _SOIL_LAYERS[cmd_args["lsm"]][i]

        # Write soil moisture anomalies to GeoTIFF
        sm1 = sm_anomalies[::-1, :]
        geotransform = _make_geotransform(longitudes, latitudes, ncols, nrows)
        outfile_anomaly = f"{cmd_args['outfile_anomaly_prefix']}"
        outfile_anomaly += f".layer{i+1}.tif"
        varname = "Soil Moisture Anomaly"
        output_raster = _create_output_raster(outfile_anomaly,
                                              ncols, nrows, geotransform,
                                              sm1)
        metadata = _set_metadata(varname_arg=varname,
                                 soil_layer=_soil_layer,
                                 model=cmd_args["lsm"],
                                 yyyymmddhh_arg=cmd_args["yyyymmddhh"])
        output_raster.GetRasterBand(1).SetMetadata(metadata)
        output_raster.FlushCache() # Write to disk
        del output_raster
    ncid.close()

def _main():
    """Main driver"""
    # Get the file names for this invocation.
    cmd_args = _read_cmd_args()

    # First, fetch latitude/longitudes.  This is pulled from the LDT parameter
    # file, since LVT output has data voids over water.
    ncid = nc4_dataset(cmd_args["ldtfile"], 'r', format='NETCDF4')
    longitudes = ncid.variables["lon"][:,:]
    latitudes = ncid.variables["lat"][:,:]
    ncid.close()

    # Next, fetch the soil moisture anomalies from the LVT 'TS' file.
    _proc_sm_anomalies(cmd_args, longitudes, latitudes)

    # ncid = nc4_dataset(tsfile, 'r', format='NETCDF4')
    # for i in range(0, 4): # Loop across four LSM layers
    #     sm_anomalies = ncid.variables["SoilMoist"][i,:,:]
    #     nrows, ncols = sm_anomalies.shape

    #     _soil_layer = _SOIL_LAYERS[lsm][i]

    #     # Write soil moisture anomalies to GeoTIFF
    #     sm1 = sm_anomalies[::-1, :]
    #     geotransform = _make_geotransform(longitudes, latitudes, ncols, nrows)
    #     outfile_anomaly = f"{anomaly_gt_prefix}.layer{i+1}.tif"
    #     varname = "Soil Moisture Anomaly"
    #     output_raster = _create_output_raster(outfile_anomaly,
    #                                           ncols, nrows, geotransform,
    #                                           sm1)
    #     metadata = _set_metadata(varname_arg=varname,
    #                              soil_layer=_soil_layer,
    #                              model=lsm,
    #                              yyyymmddhh_arg=yyyymmddhh)
    #     output_raster.GetRasterBand(1).SetMetadata(metadata)
    #     output_raster.FlushCache() # Write to disk
    #     del output_raster
    # ncid.close()

    # Next, fetch the monthly soil moisture climatologies from the LVT 'FINAL'
    # file.
    ncid = nc4_dataset(cmd_args["finalfile"], 'r', format='NETCDF4')
    for imonth in range(0, 12):
        month = _MONTHS[imonth]
        climo_name = f"SoilMoist_{month}_climo"
        for i in range(0, 4): # Loop across four LSM layers
            sm_climo = ncid.variables[climo_name][i,:,:]
            nrows, ncols = sm_climo.shape

            _soil_layer = _SOIL_LAYERS[cmd_args["lsm"]][i]

            # Write soil moisture climatology to GeoTIFF
            sm1 = sm_climo[::-1, :]
            geotransform = _make_geotransform(longitudes, latitudes,
                                              ncols, nrows)
            outfile_climo = f"{cmd_args['outfile_climo_prefix']}"
            outfile_climo += f".{month}.layer{i+1}.tif"
            varname = "Climatological Soil Moisture"
            output_raster = _create_output_raster(outfile_climo,
                                                  ncols, nrows, geotransform,
                                                  sm1)
            metadata = _set_metadata(varname_arg=varname,
                                     soil_layer=_soil_layer,
                                     model=cmd_args["lsm"],
                                     yyyymmddhh_arg=cmd_args["yyyymmddhh"],
                                     climomonth=month)
            output_raster.GetRasterBand(1).SetMetadata(metadata)

            output_raster.FlushCache() # Write to disk
            del output_raster
    ncid.close()

# Main driver
if __name__ == "__main__":
    _main()
