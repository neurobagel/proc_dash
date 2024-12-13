# Descriptive & neuroImaging data Graphical Explorer for Subject Tracking

- [Overview](#overview)
- [Preview](#preview)  
- [Quickstart](#quickstart)  
- [Input schema](#input-schema)  
- [Creating a dashboard-ready "digest" file](#creating-a-dashboard-ready-digest-file)
- [Running in a Docker container](#running-in-a-docker-container)
- [Local development](#local-development)

## Overview
`digest` is a web dashboard for exploring subject-level availability of pipeline derivatives and phenotypic variables in a neuroimaging dataset.
It provides user-friendly options for querying data availability, along with interactive visual summaries.

`digest` supports any tabular dataset file that follows a data modality-specific [schema](/schemas/), referred to here as a "digest" file.
`digest` is also compatible with the processing status files generated by [Nipoppy](https://nipoppy.readthedocs.io/en/stable/), a framework for organization and processing of neuroimaging-clinical datasets.

## Preview
![alt text](img/ui_overview_table.png?raw=true)
![alt text](img/ui_overview_plots.png?raw=true)

## Quickstart
`digest` is publicly available at https://digest.neurobagel.org/!

You can find correctly formatted example input files [here](/example_bagels/) to test out dashboard functionality.

## Input schema
`digest` supports long format TSVs that contain the columns specified in the [bagel schema](/schemas/) (see also the schemas [README](https://github.com/neurobagel/digest/tree/main/schemas#readme) for more info). 

At the moment, each digest file is expected to correspond to one dataset.

## Creating a dashboard-ready "digest" file
While `digest` can be used with any TSV compliant with one of the [digest schemas](/schemas/), the easiest way to obtain dashboard-ready files for pipeline derivative availability is to use the [Nipoppy](https://neurobagel.org/nipoppy/overview/) specification for your neuroimaging dataset organization.
Nipoppy provides dataset [trackers](https://nipoppy.readthedocs.io/en/stable/user_guide/tracking.html) that can automatically extract subjects' imaging data and pipeline output availability, producing processing status files that are directly `digest` compatible.

For detailed instructions to get started using Nipoppy, see the [documentation](https://nipoppy.readthedocs.io/en/stable/). 
In brief, the (mostly automated!) Nipoppy steps to generate a processing status file can be as simple as:
1. Initializing an empty, Nipoppy-compliant dataset directory tree for your dataset
2. Updating your Nipoppy configuration with the pipeline versions you are using, and creating a manifest spreadsheet of all available participants and sessions
2. Populating the directory tree with any existing data and pipeline outputs *
3. Running the tracker for the relevant pipeline(s) for your dataset to generate a processing status file
   - This step can be repeated as needed to update the file with newly processed subjects

*Nipoppy also provides a protocol for running processing pipelines from raw imaging data.

## Running in a Docker container

1. To get the most recent changes, pull the `neurobagel/digest` docker image tagged `nightly`:
```bash
docker pull neurobagel/digest:nightly
```

2. Currently, `digest` also relies on a local copy of the [`nipoppy-qpn`](https://github.com/neurodatascience/nipoppy-qpn) repository, which contains ready-to-use `digest` files that are automatically generated for the Quebec Parkinson Network data.
```
git clone https://github.com/neurodatascience/nipoppy-qpn.git
```

3. Run `digest` and mount the `nipoppy-qpn` directory into the container:
```bash
docker run -d -p 8050:8050 -v ${PWD}/nipoppy-qpn:/app/nipoppy-qpn neurobagel/digest:nightly
```

Now, the dashboard can be accessed at http://127.0.0.1:8050 on your local machine.

## Local development
To install `digest` from the source repository, run the following in a Python environment:
```bash
git clone https://github.com/neurobagel/digest.git
cd digest
pip install -r requirements.txt
```

To launch the app locally:
```bash
python -m digest.app
```
Once the server is running, the dashboard can be accessed at http://127.0.0.1:8050/ in your browser.

### Testing
`pytest` and `dash.testing` are used for testing dashboard functionality during development.

To run the tests, run the following command from the repository's root:
```bash
pytest tests
```
