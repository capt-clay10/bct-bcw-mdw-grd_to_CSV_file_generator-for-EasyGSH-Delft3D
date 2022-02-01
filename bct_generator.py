# -*- coding: utf-8 -*-
"""
Part two of the process
This script extracts boundary conditions - water level from the EasyGsh data
It requires the csv file generated from the part one of the process
It requires the netcdf file with the water level data
It requires the mdf file
The output file (.bct) will have the same name as the mdf file

"""

# %% Over head function


def bct_file_generator(boundaries, nc_file, mdf_file, start_time, end_time, step, bct_file):

    # %% Import packages
    import pandas as pd
    import numpy as np
    import os
    import utm
    import csv
    import time

    try:
        import xarray as xr
    except ModuleNotFoundError as err_4:
        # Error handling
        print(
            str(err_4) +
            ' This package also requires extra dependencies like netCDF4, h5netcdf and possibly scipy')

    # %% Create functions

    def convert_flt_to_sci_not(fltt, prec, exp_digits):
        s = "%.*e" % (prec, fltt)
        # print(f's: {s}')
        if s == 'nan':
            s = "%.*e" % (prec, 0)  # TODO: is it a good idea to replace nan with 0?
        mantissa, exp = s.split('e')
        # print(f'mantissa: {mantissa}')
        # print(f'exp: {exp}')
        # add 1 to digits as 1 is taken by sign +/-
        return "%se%+0*d" % (mantissa, exp_digits + 1, int(exp))

    def convert_list_to_sci_not(input_list, prec, exp_digits):
        converted = []
        for flt in input_list:
            sci = convert_flt_to_sci_not(fltt=flt, prec=prec, exp_digits=exp_digits)
            converted.append(sci)

        return converted

    def add_blank_pos_val(input_str):
        """Add leading blank for positive value."""

        if input_str[:1] != '-':
            output_str = f' {input_str}'
        else:
            output_str = input_str
        return output_str

    # %% Extract information from mdf file

    string1 = 'Tstart'
    string2 = 'Tstop'
    string3 = 'Itdate'  # reference time

    file1 = open(mdf_file, "r")
    for line in file1:
        # checking string is present in line or not
        if string1 in line:
            values = line.split('=')
            tstart_val = values[1].strip()
            break
            file1.close()  # close file

    file1 = open(mdf_file, "r")
    for line in file1:
        # checking string is present in line or not
        if string2 in line:
            values_2 = line.split('=')
            tstop_val = values_2[1].strip()
            break
            file1.close()  # close file

    file1 = open(mdf_file, "r")
    for line in file1:
        # checking string is present in line or not
        if string3 in line:
            values_3 = line.split('=')
            ref_time_unedited = values_3[1].strip()
            break
            file1.close()  # close file

    # time series
    start = float(tstart_val)  # from mdf file
    stop = float(tstop_val)  # from mdf file
    ref_time = ref_time_unedited[1:11]
    reference_time = ref_time.replace('-', '')  # remove the hyphen for the bct file format
    # step = 2.0000000e+001  # 20 minute step # adding here for understanding

    # %% Open input files

    bnd_loc = pd.read_csv(boundaries, names=['boundary', 'easting', 'northing'], )

    data = xr.open_dataset(nc_file)

    dataset = data.sel(nMesh2_data_time=slice(start_time, end_time))
    wl = dataset['Mesh2_face_Wasserstand_2d']

    # %% Convert to geographic coordinates

    easting = bnd_loc['easting']
    northing = bnd_loc['northing']
    bnd = bnd_loc['boundary']
    # converting to a numpy array to suit the module 'UTM'
    easting = easting.to_numpy(dtype='float64')
    northing = northing.to_numpy(dtype='float64')
    bnd_loc_geo = utm.to_latlon(easting, northing, 32, 'N')  # convert to utm
    bnd_loc_geo = pd.DataFrame(bnd_loc_geo)  # convert tuple to dataframe
    bnd_loc_geo = bnd_loc_geo.T  # transpose the dataframe
    bnd_loc_geo.columns = ['lat', 'lon']
    bnd_loc_geo['boundaries'] = bnd  # adding the boundary names

    # %%  Converting time to scientific notations and check for records in table

    float_range = np.arange(start, stop + step, step).tolist()  # create a range of the input time

    record_in_table = len(float_range)  # for the bct file number of records in a tbale

    time_list = convert_list_to_sci_not(input_list=float_range,
                                        prec=7, exp_digits=3)

    # %%  Separating all boundary values into a dictionary with the boundary name as key
    output_dict = {}
    output_dict_2 = {}

    for index, row in bnd_loc_geo.iterrows():
        # print(index)
        # print(row)
        # if index < 6:  # TODO: Remove after testing
        wl_sel = wl.sel(lon=row['lon'], lat=row['lat'], method="nearest")
        wl_2 = wl_sel.to_numpy()  # convert to sci_not?
        output_dict[row['boundaries']] = wl_2

    for bnd_point_key, bnd_point_wl_list in output_dict.items():
        # Generate dict where keyword is bnd name and value is a list containing 3 list:
        # (1) time (2) wl at point a, (3) wl at point b

        bnd_point_wl_list_sci_not = convert_list_to_sci_not(
            input_list=bnd_point_wl_list,
            prec=7, exp_digits=3)  # convert to scientific notation

        # For every 'a' point: (1) create new list to write into dict (2) append array of time values
        if bnd_point_key[-1:] == 'a':
            list_in_dict = []
            list_in_dict.append(time_list)  # append array of time values
        list_in_dict.append(bnd_point_wl_list_sci_not)
        output_dict_2[bnd_point_key[:-2]] = list_in_dict

    # %% write the bct file

    try:
        os.remove(bct_file)
    except FileNotFoundError:
        pass

    for key in output_dict_2:
        bn_name = str(key)
        header_lines = ["table-name           'Boundary Section : 1'",
                        "contents             'Uniform             '",
                        "location             '{}              '".format(bn_name),
                        "time-function        'non-equidistant'",
                        "reference-time       {}".format(reference_time),
                        "time-unit            'minutes'",
                        "interpolation        'linear'",
                        "parameter            'time                '                     unit '[min]'",
                        "parameter            'water elevation (z)  end A'               unit '[m]'",
                        "parameter            'water elevation (z)  end B'               unit '[m]'",
                        "records-in-table     {}".format(record_in_table)]

        with open(bct_file, 'a', newline='') as f:
            for one_line in header_lines:
                f.write(one_line)
                f.write('\r\n')

            csv_writer = csv.writer(f)
            count = 0
            bnd_data_list = output_dict_2[key]
            for row in bnd_data_list[0]:
                # Set values to write, add leading blank for positive values
                time_val = add_blank_pos_val(input_str=bnd_data_list[0][count])
                wl_a = add_blank_pos_val(input_str=bnd_data_list[1][count])
                wl_b = add_blank_pos_val(input_str=bnd_data_list[2][count])

                # Generate row content as single string
                row_str = f'{time_val} {wl_a} {wl_b}'

                # Write row to file
                csv_writer.writerow([row_str])

                count += 1