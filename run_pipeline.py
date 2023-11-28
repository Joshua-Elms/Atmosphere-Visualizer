import pathlib
from pipeline import main, setup_logger

### BEGIN PARAMS ###

# data_params, working_dir, and output_stem are defined before config to avoid code duplication

# data params
data_params = dict( 
    year = "2023",
    month = "09", # only works within one month of one year (can't download June-July data, for example)
    start_day_inc = "01",
    stop_day_inc = "30",
    step_day = 1,
    start_hour_inc = "00", # 00-23
    stop_hour_inc = "23", # 00-23
    step_hour = 1,
    sfc_vars = ["total_column_water_vapour", "2m_temperature", "total_cloud_cover", "vertical_integral_of_total_energy"],
    pl_vars = [], # "u_component_of_wind", "v_component_of_wind", "geopotential"
    pl_levels = [] # 500, 1000
)

# Where to save the data, images, and videos. Please provide an absolute path, not a relative path.
working_dir = pathlib.Path('/Users/joshuaelms/Desktop/github_repos/Atmosphere-Visualizer/large_output')

# Output stem for the data
output_stem = f'y{data_params["year"]}_m{data_params["month"]}_da{data_params["start_day_inc"]}_db{data_params["stop_day_inc"]}_ha{data_params["start_hour_inc"]}_hb{data_params["stop_hour_inc"]}'

config = dict(
data_params = data_params,

# path params
working_dir = working_dir,
output_stem = output_stem,
output_stem_explain = r"yYYYY_mMM_diDD_djDD_hmHH_hnHH_{pl,sfc,merged}.nc, where YYYY is the year, MM is the month, DD is the day (a=start, b=stop) inclusive, HH is the hour (a=start, b=stop) inclusive, final tag indicates whether using pl (pressure level data) or sfc (surface data) or merged (combined pl and sfc).",
output_ds_path = working_dir / f'{output_stem}_merged.nc', # save the output dataset to a netcdf file or False / None to not save
use_ds = "large_output/y2023_m09_da01_db30_ha00_hb23_merged.nc", # provide a path to a dataset to use instead of pulling data from cdsapi, or False to pull data from cdsapi
rm_originals = True, # delete the original .nc files after merging and processing
rm_images = True, # delete the images after creating the video
img_dir = working_dir / 'frames', # directory to save images to
vid_dir = working_dir / 'videos', # directory to save videos to

# vis params
channel_metadata = { 
    "t2m": dict(pref_cmap = "magma"),
    "tcc": dict(pref_cmap = "Greys"),
    "tcwv": dict(pref_cmap = "ocean"),
    "wind500": dict(pref_cmap = "viridis"),
    "wind1000": dict(pref_cmap = "viridis"),
},
border_color = 'black',
fps = '18', # frames per second for the video, as a string,
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