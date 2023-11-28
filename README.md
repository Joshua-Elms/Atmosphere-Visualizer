# Atmosphere-Visualizer

### Introduction
This tool creates visualizations of the Earth's atmosphere. The data (Hersbach, H. et al., (2018)) comes from the Copernicus Climate Change Service Climate Data Store (CDS) and can be freely accessed by setting up a CDS API account. The individual video frames are plotted in Python and concatenated into a video using FFmpeg.



https://github.com/Joshua-Elms/Atmosphere-Visualizer/assets/91396382/68a60315-7f37-4515-b32f-1d94386cf1c4



https://github.com/Joshua-Elms/Atmosphere-Visualizer/assets/91396382/06e5a763-b389-478a-a8c5-bfbfd982d90e



https://github.com/Joshua-Elms/Atmosphere-Visualizer/assets/91396382/1c1617a2-78a3-49b9-8b13-7615b7a3bf3c



### Dependencies

1. CDS API - register for a free account [here](https://cds.climate.copernicus.eu/user/register?destination=%2F%23!%2Fhome) and set up your `$HOME/.cdsapirc` file according to the instructions [here](https://cds.climate.copernicus.eu/api-how-to).
2. Conda Environment - build the necessary conda environment from the requirements file using the following command: `conda create -f environment.yml`. Enter the environment with `conda activate atmos-vis`. If the system-dependencies included in the `environment.yml` file yield non-functional environment for you, simply enter the following commands to build it on your own:
   1. `conda create -n atmos-vis`
   2. `conda activate atmos-vis`
   3. `conda install xarray ffmpeg -c anaconda`
   4. `conda install cdsapi matplotlib netcdf4 scipy -c conda-forge`
4. Memory - ensure you have enough RAM to load and process the data you are requesting. One month of hourly data for a 4 byte variable will be about 4 GB.
5. Time - short run (a few hours of data) will likely run in seconds or minutes, but full-length visualizations of month of data for multiple variables may take a few hours, especially if the CDS queue is long. Check the queue [here](https://cds.climate.copernicus.eu/live/queue).

### Usage

Set the parameters to their desired values in `run_pipeline.py`, then activate your conda environment and enter `python run_pipeline.py` to generate your visualizations.

### Parameters

| Parameter          | Explanation                                                                                                                                                                                                                                                                                                                                                                            |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `data_params`      | Information about the times, pressure levels, and variables to be requested. Find the names of other variables [here](https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation#heading-Table9pressurelevelparametersinstantaneous). See comments in `run_pipeline.py` for more details                                                                                                                                                                                                                                                        |
| `working_dir`      | Location for all temporary and persistent output from the pipeline (`.nc` files for intermediate data, `.png` files for frames, and `.mp4` files for video)                                                                                                                                                                                                                            |
| `output_ds_path`   | Desired output location for final dataset                                                                                                                                                                                                                                                                                                                                              |
| `use_ds`           | If you already have a dataset formatted for this pipeline, but would like to change the colormap or add/remove metadata, set this to the path for your dataset and re-run the pipeline                                                                                                                                                                                                 |
| `rm_originals`     | If True, delete the intermediate `sfc` and `pl` files (`merged` netcdf will still be saved to `output_ds_path`)                                                                                                                                                                                                                                                                        |
| `rm_images`        | If True, delete the frames (`.png` files) that are used to generate the final `.mp4`                                                                                                                                                                                                                                                                                                   |
| `channel_metadata` | Used to pass visualization information to the pipeline; see [matplotlib colormaps](https://matplotlib.org/stable/users/explain/colors/colormaps.html) for more cmap options                                                                                                                                                                                                            |
| `border_color`     | Defaults to `"black"`; use only valid matplotlib color strings. Background color for the video.                                                                                                                                                                                                                                                                                        |
| `fps`              | Framerate of the output video as a string (ex. `"12"`)                                                                                                                                                                                                                                                                                                                                 |
| `plot_metadata`    | Whether to plot the variable name and timestamp in the corner of the video.                                                                                                                                                                                                                                                                                                            |
| `metadata_pos`     | If `plot_metadata` is True, can be `"(upper/lower)-(right/left)"` (ex. `"upper-right"`)                                                                                                                                                                                                                                                                                                |
| `lookup_variables` | Pressure-level data from the CDS uses long and short names for each variable. This dictionary is formatted as {long : short} to allow the program to track variables properly. If requesting PL variables not in this dict, it's necessary to add them from [this page](https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation#heading-Table9pressurelevelparametersinstantaneous) |


### Citations

Code and documentation by Joshua Elms. Email: joshua.elms111@gmail.com

Hersbach, H. et al., (2018) was downloaded from the Copernicus Climate Change Service (C3S) (2023).

The results contain modified Copernicus Climate Change Service information 2023. Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information or data it contains.

Copernicus Climate Change Service (C3S) (2023): ERA5 hourly data on single levels from 1940 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). 10.24381/cds.adbb2d47 (Accessed on 27-NOV-2023)

Hersbach, H., Bell, B., Berrisford, P., Biavati, G., Horányi, A., Muñoz Sabater, J., Nicolas, J., Peubey, C., Radu, R., Rozum, I., Schepers, D., Simmons, A., Soci, C., Dee, D., Thépaut, J-N. (2018): ERA5 hourly data on single levels from 1940 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). 10.24381/cds.adbb2d47 (Accessed on 27-NOV-2023)

Copernicus Climate Change Service (C3S) (2023): ERA5 hourly data on pressure levels from 1940 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). 10.24381/cds.bd0915c6 (Accessed on 27-NOV-2023)

Hersbach, H., Bell, B., Berrisford, P., Biavati, G., Horányi, A., Muñoz Sabater, J., Nicolas, J., Peubey, C., Radu, R., Rozum, I., Schepers, D., Simmons, A., Soci, C., Dee, D., Thépaut, J-N. (2023): ERA5 hourly data on pressure levels from 1940 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS), DOI: 10.24381/cds.bd0915c6 (Accessed on 27-NOV-2023)
