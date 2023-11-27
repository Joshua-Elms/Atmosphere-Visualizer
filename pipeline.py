import cdsapi
import pathlib
import logging
import pprint
import xarray as xr
import matplotlib.pyplot as plt
import subprocess
import shutil

def setup_logger(log_loc: pathlib.Path):
    """
    Logger will be used instead of print statements, except by the Copericus API.
    """
    logging.basicConfig(filename=log_loc,
                        filemode='w',
                        format='%(asctime)s - %(levelname)s\n%(message)s\n',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
    print(f"Logging to {log_loc}")

def pull_data(
    year, month, start_day_inc, stop_day_inc, 
    step_day, start_hour_inc, stop_hour_inc, 
    step_hour, sfc_vars, pl_vars, pl_levels,
    target_loc, output_stem, output_stem_explain
    ):
    """
    Using the cdsapi.Client() object, pull data from the ERA5 reanalysis dataset.
    The cdsapi client expects a valid config file (.cdsapirc) to be present in the user's home directory.
    
    
    Information on setting up the cdsapi.Client() object can be found here:
        1. https://cds.climate.copernicus.eu/api-how-to
    
    Information on the ERA5 reanalysis dataset can be found here:
        1. https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation#heading-Parameterlistings
        2. https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels?tab=overview
    
    year: str - year to pull data from
    month: str - month to pull data from
    start_day_inc: str - start day to pull data from (inclusive)
    stop_day_inc: str - stop day to pull data from (inclusive)
    step_day: int - step size for days
    start_hour_inc: str - start hour to pull data from (inclusive)
    stop_hour_inc: str - stop hour to pull data from (inclusive)
    step_hour: int - step size for hours
    sfc_vars: list[str] - list of surface variables to pull (if empty list / None / False, no surface data is pulled)
    pl_vars: list[str] - list of pressure level variables to pull (if empty list / None / False, no pressure level data is pulled)
    pl_levels: list[str] - list of pressure levels to pull (in hPa)
    """
    logging.info(f"Target directory: {target_loc}")
    logging.info(f"Output fname format: {output_stem_explain}")

    try:
        c = cdsapi.Client()

    except Exception as e:
        logging.exception(e)

    shared = {
        'product_type': 'reanalysis',
        'format': 'netcdf',
        'year': year,
        'month': month,
        'day': [f"{i:02}" for i in range(int(start_day_inc), int(stop_day_inc) + 1, step_day)],
        'time': [f"{i:02}:00" for i in range(int(start_hour_inc), int(stop_hour_inc) + 1, step_hour)], # 00:00, 01:00, ..., 23:00
    }

    sfc_request = {
        "name": "reanalysis-era5-single-levels",
        "request": {
            'variable': sfc_vars,
            **shared
        },
        "target": target_loc / f'{output_stem}_sfc.nc'
    }

    pl_request = {
        "name": "reanalysis-era5-pressure-levels",
        "request": {
            'variable': pl_vars,
            'pressure_level': pl_levels,
            **shared,
        },
        "target": target_loc / f'{output_stem}_pl.nc'
    }

    if sfc_vars:
        logging.info(f"Starting download of {sfc_request['name']} data")
        c.retrieve(**sfc_request)
        logging.info(f"Completed download. Request info: \n{pprint.pformat(sfc_request)}")

    if pl_vars:
        logging.info(f"Starting download of {pl_request['name']} data")
        c.retrieve(**pl_request)
        logging.info(f"Completed download. Request info: \n{pprint.pformat(pl_request)}")
        
    logging.info(f"Completed all downloads.")
    
    return sfc_request, pl_request

def postprocessing(sfc_request, pl_request, output_path, rm_originals, lookup_variables):
    """
    Merge pl and sfc data, convert to xarray ds, derive fields (e.g. wind speed, wind direction, etc.)
    
    lookup table for variable names
    see https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation#heading-Parameterlistings
    if you need more variables
    """
    sfc_exists = sfc_request['target'].exists()
    pl_exists = pl_request['target'].exists()
    
    if sfc_exists:
        sfc_ds = xr.open_dataset(sfc_request['target'])
    
    if pl_exists:
        pl_ds = xr.open_dataset(pl_request['target'])

    # Merge the two datasets along the common dimensions (longitude, latitude, time)
    if sfc_exists and pl_exists:
        out_ds = xr.merge([sfc_ds, pl_ds], compat='override')
        
    else:
        out_ds = sfc_ds if sfc_exists else pl_ds

    # Loop through pressure levels and create new data variables with updated names
    if pl_exists:
        # logging.info(f"PL: \n{pl_ds}")
        windflag = False # winds are not always requested, but u and v terms need to be processed into wind speed if they are
        if 'u_component_of_wind' in pl_request['request']['variable'] and 'v_component_of_wind' in pl_request['request']['variable']:
            windflag = True
            
        pl_levels = pl_request['request']['pressure_level']
        multi_level = len(pl_levels) > 1 # if there are multiple levels, we can't use the level dimension (not generated)
        for level in pl_levels:
            for var in pl_request['request']["variable"]:
                short_var = lookup_variables[var]
                if var in ('u_component_of_wind', 'v_component_of_wind'):
                    continue # ignore, we'll process these later
                
                if multi_level:
                    out_ds[f'{short_var}{level}'] = pl_ds[short_var].sel(level=level)
                    
                else: 
                    out_ds[f'{short_var}{level}'] = pl_ds[short_var]

            # Add the new data variables to the merged dataset
            if windflag:
                if multi_level:
                    out_ds[f'wind{level}'] = (pl_ds.u.sel(level=level)**2 + pl_ds.v.sel(level=level)**2)**0.5
                    
                else:
                    out_ds[f'wind{level}'] = (pl_ds.u**2 + pl_ds.v**2)**0.5

    # Remove the original data variables from the merged dataset
    if pl_exists:
        for var in pl_request['request']["variable"]:
            short_var = lookup_variables[var]
            try:
                out_ds = out_ds.drop_vars(short_var)
            except ValueError as e:
                logging.warning(f"Variable {short_var} not in dataset - skipping")
                logging.exception(e)

        if multi_level:
            out_ds = out_ds.drop_dims('level')

    # Print the resulting dataset
    logging.info(f"Resulting dataset: \n{out_ds}")

    # Save the resulting dataset if desired
    if output_path: # if output_path is not None, save the dataset
        out_ds.to_netcdf(output_path)
        logging.info(f"Saving dataset to {output_path}")
        
    if rm_originals:
        if sfc_exists:
            sfc_request['target'].unlink()
            logging.info(f"Deleted {sfc_request['target']}")
            
        if pl_exists:
            pl_request['target'].unlink()
            logging.info(f"Deleted {pl_request['target']}")
            
    return out_ds

def fmt_time_str(t, fmt="%Y-%m-%d %Hz"): 
    """For some reason, this works."""
    return t.astype('datetime64[s]').item().strftime(fmt)
    
def plot_frames(ds, output_dir, channel_metadata, border_color, plot_metadata, default_cmap_name = "viridis", metadata_pos = "upper-right"):
    """
    Plot frames of video for each channel and time.
    
    in channel_metadata, pref_cmap is the colormap to use for the channel. 
    units is the units of the channel. In this program, units won't be used unless
    you modify the program to show the cbar and label.
    Set the pref_cmap to False to use the default colormap, which is viridis.
    Here's a link to some colormaps: https://matplotlib.org/stable/tutorials/colors/colormaps.html
    border_color is the color of the border above & below the image. Use plt colors.
    
    output_dir: pathlib.Path - directory to save frames to
    channel_metadata: dict - see above
    border_color: str - color of border above & below image
    plot_metadata: bool - whether to plot metadata (time, channel, etc.) on the image
    default_cmap_name: str - default colormap to use if channel not in channel_metadata
    metadata_pos: str - where to plot metadata (upper-right, upper-left, lower-right, lower-left)
    """
    # deriving some useful items
    ds = ds.isel(latitude=slice(0, 720))
    channels = list(ds.data_vars.keys())
    times = ds.time.values
    data_dims = (720, 1440)
    img_size_in = (16, 10)
    dpi = int(data_dims[1] / img_size_in[0])

    for channel_idx, channel in enumerate(channels):
        channel_dir = output_dir / f"var_{channel}"
        channel_dir.mkdir(parents=True, exist_ok=True)
        da = ds[channel] 
        cbar_lower, cbar_upper = da.min(), da.max() # ensure colors are consistent across frames
        logging.info(f"Generating frames for channel {channel} ({channel_idx+1}/{len(channels)})")
        
        if channel in channel_metadata:
            cmap_name = channel_metadata[channel]["pref_cmap"] # if channel is not saved, can't plot until saved
            
        else: 
            cmap_name = default_cmap_name
            logging.warning(f"Channel {channel} not in channel_metadata - using default colormap {default_cmap_name}")
        
        for t_idx, t in enumerate(times):
            t_path = channel_dir / f"{t_idx+1:04}.png" # output path for this frame
            field = da.isel(time=t_idx)
            fig, ax = plt.subplots(figsize=img_size_in) # create figure
            ax.imshow(field, cmap=cmap_name, vmin=cbar_lower, vmax=cbar_upper) # plot field
            
            # clear axes and fill with black outside of data
            ax.axis('off')
            ax.set_position([0, 0.1, 1, 0.8]) # (left, bottom, width, height)
            
            # plot metadata
            metadata_pos_options = {
                "upper-right" : {"time": (0.9, 1.03), "channel": (0.9, 1.08)},
                "upper-left" : {"time": (0.1, 1.03), "channel": (0.1, 1.08)},
                "lower-right" : {"time": (0.9, -0.03), "channel": (0.9, -0.08)},
                "lower-left" : {"time": (0.1, -0.03), "channel": (0.1, -0.08)},
            }
            if plot_metadata:
                ax.text(*metadata_pos_options[metadata_pos]["channel"], f"{channel}", transform=ax.transAxes, ha='center', va='center', fontsize=20, color='white' if border_color != 'white' else 'black')
                ax.text(*metadata_pos_options[metadata_pos]["time"], f"{fmt_time_str(t)}", transform=ax.transAxes, ha='center', va='center', fontsize=20, color='white' if border_color != 'white' else 'black')

            fig.set_facecolor(border_color)
            fig.savefig(t_path, dpi=dpi)
            plt.close(fig)
            
    logging.info(f"Completed generating frames for all channels.")
    
def dir2movie(
    input_dir: pathlib.Path,
    output_path: pathlib.Path,
    input_fmt: str = r'%04d.png',
    fps: int = 24,
    ):
    """
    Convert a directory of images to an mp4 movie.
    
    If you are seeing all of your frames outputted properly,
    but the movie is not being created, you may need to modify
    the 'cmd = ...' below, which is run from the shell to create
    the video out of the images. You may need to preface 'ffmpeg' 
    with 'python -m' or 'python3 -m', depending on your system.
    
    Output from this function will be printed to the terminal, not logged.
    You can change this by passing an output stream to the subprocess.run() call.
    """
    cmd = f"ffmpeg -framerate {fps} -i '{input_fmt}' -c:v libx264 -pix_fmt yuv420p {output_path}"
    logging.info(f"Using command: \n\t{cmd}")
    subprocess.run(cmd, shell=True, cwd=input_dir)
    logging.info(f"Probably saved movie to {output_path}")    

def main(
    data_params, vid_dir, img_dir, use_ds, 
    output_ds_path, rm_originals, rm_images, 
    lookup_variables, channel_metadata, 
    border_color, fps, plot_metadata, metadata_pos,
    output_stem_explain, working_dir, output_stem
    ):
    # prepare home dir and output dirs
    vid_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)
    
    # load dataset
    if use_ds: # use a pre-existing dataset
        ds = xr.open_dataset(use_ds)
        
    else: # if not using a pre-existing dataset, pull data from cdsapi and process it
        # pull data
        sfc_request, pl_request = pull_data(**data_params, target_loc=working_dir, output_stem=output_stem, output_stem_explain=output_stem_explain)
        
        # post process data
        ds = postprocessing(sfc_request, pl_request, output_ds_path, rm_originals, lookup_variables)
        
    # plot frames of video
    plot_frames(ds, img_dir, channel_metadata, border_color, plot_metadata, metadata_pos)
    
    # create video
    logging.info("Creating videos")
    
    for dir in img_dir.glob("var_*"): # glob format set in plot_frames() above
        logging.info(f"Creating video for {dir.name}")
        varname = dir.name.split("_")[1]
        vid_output_path = vid_dir / f"{varname}.mp4"
        dir2movie(input_dir=dir, output_path=vid_output_path, fps=fps) # input_fmt set in plot_frames() above
    
    logging.info("Videos created (maybe)")
    
    # delete images
    if rm_images:
        shutil.rmtree(img_dir)
        logging.info("Deleted all frames")
        
    ds.close()
    
    logging.info("Program execution complete")
    print("Program execution complete")
    
    ### END EXECUTION ###

if __name__=="__main__":
    
    ### BEGIN PARAMS ###
    
    # data_params, working_dir, and output_stem are defined before config to avoid code duplication
    
    # data params
    data_params = dict( 
        year = "2023",
        month = "07", # only works within one month of one year
        start_day_inc = "1",
        stop_day_inc = "1",
        step_day = 1,
        start_hour_inc = "00", # 00-23
        stop_hour_inc = "09", # 00-23
        step_hour = 1,
        sfc_vars = [],
        pl_vars = ["u_component_of_wind", "v_component_of_wind"],
        pl_levels = ["850"]
    )
    
    # Where to save the data, images, and videos.
    working_dir = pathlib.Path('/Users/joshuaelms/Desktop/github_repos/Atmosphere-Visualizer/output/example')
    
    # Output stem for the data
    output_stem = f'y{data_params["year"]}_m{data_params["month"]}_da{data_params["start_day_inc"]}_db{data_params["stop_day_inc"]}_ha{data_params["start_hour_inc"]}_hb{data_params["stop_hour_inc"]}'
    
    config = dict(
    data_params = data_params,
    
    # path params
    working_dir = working_dir,
    output_stem = output_stem,
    output_stem_explain = r"yYYYY_mMM_diDD_djDD_hmHH_hnHH_{pl,sfc,merged}.nc, where YYYY is the year, MM is the month, DD is the day (a=start, b=stop) inclusive, HH is the hour (a=start, b=stop) inclusive, final tag indicates whether using pl (pressure level data) or sfc (surface data) or merged (combined pl and sfc).",
    output_ds_path = working_dir / f'{output_stem}_merged.nc', # save the output dataset to a netcdf file or False / None to not save
    use_ds = "/Users/joshuaelms/Desktop/github_repos/atmospheric-science/Random/earth_vis/data/ERA5_raw/y2023_m10_da24_db25_ha00_hb23.nc", # provide a path to a dataset to use instead of pulling data from cdsapi, or False to pull data from cdsapi
    rm_originals = True, # delete the original .nc files after merging and processing
    rm_images = False, # delete the images after creating the video
    img_dir = working_dir / 'frames', # directory to save images to
    vid_dir = working_dir / 'videos', # directory to save videos to
    
    # vis params
    channel_metadata = { 
        "pv50" : dict(pref_cmap = "viridis", units = "PVU"),
        "pv500" : dict(pref_cmap = "viridis", units = "PVU"),
        "pv850" : dict(pref_cmap = "viridis", units = "PVU"),
        "pv1000" : dict(pref_cmap = "viridis", units = "PVU"),
        "t2m": dict(pref_cmap = "magma", units = "deg K"),
        "tcc": dict(pref_cmap = "Greys", units = "%"),
        "wind50": dict(pref_cmap = "viridis", units = "m/s"),
        "wind500": dict(pref_cmap = "viridis", units = "m/s"),
        "wind850": dict(pref_cmap = "viridis", units = "m/s"),
        "wind1000": dict(pref_cmap = "viridis", units = "m/s"),
    },
    border_color = 'black',
    fps = '24', # frames per second for the video, as a string,
    plot_metadata = True,
    metadata_pos = "upper-right", # if plot_metadata is True, where to plot the metadata (upper-right, upper-left, lower-right, lower-left)
    
    # random params
    lookup_variables = dict(
        potential_vorticity = "pv",
        geopotential = "z",
        temperature = "t",
        u_component_of_wind = "u",
        v_component_of_wind = "v",
        specific_humidity = "q",
        vertical_velocity = "w",
        divergence = "d",
        relative_humidity = "r",
        fraction_of_cloud_cover = "cc",
    ),
    # end paramdict
    )
    
    ### END PARAMS ###
    
    
    
    
    ### BEGIN EXECUTION ###
    
    # ensure working_dir exists
    working_dir.mkdir(parents=True, exist_ok=True)
    
    # set up logger
    setup_logger(log_loc = working_dir / 'pipeline.log',)
    
    # run main
    main(**config)
    
   ### END EXECUTION ###