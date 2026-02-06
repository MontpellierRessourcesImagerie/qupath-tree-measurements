# Segment, measure and analyze nuclei

Before starting, you must:
    - Download locally the content of this repository.
    - Download the [models used by StarDist](https://github.com/qupath/models/tree/main/stardist)
    - Download and install the [StarDist extension for QuPath](https://github.com/qupath/qupath-extension-stardist/releases)
    - Download and install [Miniconda](https://repo.anaconda.com/miniconda/)

## I. In QuPath

### 0. Import images

- Open QuPath and create a new project.
- Import all your images into that project and indicate that they are fluorescence.
- If the images are large, importing them will take a while since QuPath needs to build a pyramid for each of them.
- Double-click on one of them to visualize it.

### 1. Nuclei segmentation

> The goal of this step will be to segment nuclei (have a polygon around each nucleus) and expand them a little bit to capture more context of their surroundings. At the same time, the intensity values will be measured for each channel in each nucleus.

- In QuPath, open the script `segment_measure/scripts/segment_and_measure.groovy` (a simple drag and drop should work).
- In the script, everything before the line `// ####################` is settings that you can edit at your liking.

| Name                 | Description                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `input_class`        | We will search nuclei and measure them in every annotation having this class.                                            |
| `use_present`        | If `true` we will work on the annotations already made. Otherwise, we will make a new annotation taking the whole image. |
| `channel_1`          | If you go in ◑, what object contains the first channel.                                                                  |
| `channel_1`          | If you go in ◑, what object contains the second channel.                                                                 |
| `channel_1`          | If you go in ◑, what object contains the third channel.                                                                  |
| `channel_1`          | If you go in ◑, what object contains the fourth channel.                                                                 |
| `LUTs`               | If you prefer your channels to have a given color, you can give a RGB value here.                                        |
| `model_path`         | Path to `dsb2018_heavy_augment.pb` in the StarDist models that you downloaded.                                           |
| `expansion_distance` | How far the nuclei will be expanded to inspect the direct context.                                                       |

- If you want to test your settings before launching the execution on the whole image, you can:
    - Make a few rectangle annotations on your images.
    - Select them all in the left column.
    - Click on the class corresponding to what you provided in `input_class` and then on `Set selected`.
    - Pass the value of `use_present` to `true`.
- If you want to go with the full image, just pass `use_present` to `false`.
- You can run the script for the current image by clicking on `Run` or you can run it for every image by clicking on ⋮ and then on `Run for project`.
- The segmentation is a long process.
- **Don't forget to save (Ctrl+S), QuPath crashes very often.**

### 2. Filter the results

> The goal of this step is to remove nuclei that are either too big or too small and to remove StarDist's hallucinations.

- In QuPath, open the script `segment_measure/scripts/filter_cells.groovy` (a simple drag and drop should work).
- In the script, everything before the line `// ####################` is settings that you can edit at your liking.

| Name             | Description                                                                                                                                                                                                                                                |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `med_percentage` | Hallucinations removal is based on filtering objects by their DAPI signal. To do that we look at all the values (sorted) and we determine the threshold as a percentage of this list of values. This variable represents the percentage (e.g. 0.25 == 25%) |
| `min_area`       | Minimal area tolerated for a nucleus.                                                                                                                                                                                                                      |
| `max_area`       | Maximal area tolerated for a nucleus.                                                                                                                                                                                                                      |
| `delete_objects` | If you need to try different different settings, keep this variable to `false`. It will simply mark in gray the cells that should be removed if we applied the filtering.                                                                                  |

- Make sure that `delete_objects` is set to `false`.
- Play with the different settings and re-run the script as many times as you want.
- Once you found the correct combination, you can pass `delete_objects` to `true` and re-run the script.
- Again, you can now run it for the whole project.
- **Don't forget to save (Ctrl+S), QuPath crashes very often.**

### 3. Classify your objects

> The goal of this step is to classify cells as positive or negative to certain binary dyes (simple presence == positive).

- Copy the folder `segment_measure/classifiers` into the folder that you provided to QuPath when you created a new project.
- In QuPath, open the script `segment_measure/scripts/classify.groovy` (a simple drag and drop should work).
- In the script, everything before the line `// ####################` is settings that you can edit at your liking.

| Name                      | Description                                                                      |
| ------------------------- | -------------------------------------------------------------------------------- |
| `classification_channels` | List of channels that we classify in a binary way (either positive or negative). |

- The names in `classification_channels` should all appear in your channel names.
- If "NNN" is present in `classification_channels`, there must be `find-NNN.json` in `classifiers/object_classifiers`.
- If the list is correct, you can run the script right ahead.
- If the left column of QuPath, some new classes should be present with their color code.
- In the viewer, unclassified cells should be left red while other should take the color associated to their class.
- **Don't forget to save (Ctrl+S), QuPath crashes very often.**

### 4. Export the results

- If everything went well, you can now go to `Measure` > `Export measurements`.
- Pick all the images onto which you ran the analysis.
- Choose a path for the TSV file that will be produced.
- The useful data is stored in detections, so you must set `Export type` to "Detections".
- You can now click on `Populate` and `Export`.

## II. In Python

### 0. Before the first run

- To avoid package collisions in Python, we don't use your OS' Python but an environments manager called "Miniconda".
- Before the first run, we need to create an isolated environment, make it active and install the dependencies in it.
- If you downloaded and installed Miniconda as requested:
    - On Windows, you can search and open the program called "Anaconda prompt"
    - On Linux/Mac: Simply open a new terminal
- If you don't see "(base)" written on the left of the prompt, there is a problem.
- Start by creating a new environment using the command: `conda create -n analyzer-env -y python=3.12`.
- Once it's done, you can activate the environement that you just created using the command: `conda activate analyzer-env`.
- You can eventually install the dependencies with the command: `pip install numpy pandas PyQt5 qtpy`.
- Close the terminal once you are done.

### 1. Launch the GUI

- Open "Anaconda prompt" on Windows or open a new terminal on Linux/Mac.
- Launch the command: `conda activate analyzer-env`.
- Write `python ` (with a **space** at the end) but don't launch the command yet.
- Drag and drop the `analyze/gui.py` script in the terminal.
- You can now launch the command and a new window should appear.

### 2. Fill the settings

- Click the `Choose CSV/TSV` button and in the file selector, indicate the TSV that you just produced using QuPath.
- Right below the button, the binary classes found in the file should show up (e.g. "Caspase+", "Ki67+", ...).
- The list of measurable metrics should also show up in the first box and the list of images should be in the second box.

#### a. For classifiables

- For each classification (e.g. "Caspase+", ...), we must have:
    - The number of objects having this class.
    - Mean [measurable] (for each measurable chosen in the first box (e.g. Ki67, HES1, ...))
    - Median [measurable]
    - StdDev [measurable]
- We also need these same metrics for cell having no classification that we denotate as "∅".

#### b. For measurables

- You start by selecting a set of measurable properties in the proposed list. For each of them, you have to provide:
    - `Alias`: The name that it will have in the results table.
    - `Milestones`: At what percentages should we cut the list of values for this metric.
    - `Level`: To which level of the tree will correspond this value.
- Here is an exemple of the tree that you will get for a certain set of settings

| Metric name        | Alias          | Milestones   | Level |
| ------------------ | -------------- | ------------ | ----- |
| Nucleus: Area µm^2 | Nuclei area    | 0.5          | 0     |
| Cell: Ki67: Median | Ki67 intensity | 0.333, 0.666 | 1     |
| Cell: HES1: Median | HES1 intensity | 0.333, 0.666 | 2     |



- Each measurable is assigned to a level in the tree (ex: Ki67 -> 1, HES1 -> 2, ...)
- For each "measurable", the number of sub-branches that will be created depends on the number of milestones.
- Intensities corresponding to each milestones are processed on the images that you declare as references in the second box.
- On top of the global statistics, we create a file for each image corresponding the raw values.
