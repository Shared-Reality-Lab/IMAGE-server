Beta quality: Useful enough for testing by end-users.

# Chart data extraction pipeline

This pipeline is based on the DeepRule paper:

- Link to [deeprule paper](https://openaccess.thecvf.com/content/WACV2021/papers/Luo_ChartOCR_Data_Extraction_From_Charts_Images_via_a_Deep_Hybrid_WACV_2021_paper.pdf) 
- Link to [deeprule repo](https://github.com/soap117/DeepRule)

`config`, `db`, `models`, and `pipeline_inference` are directly taken from the above repo. `post_processing` is a modified version of `RuleGroup`, and `pipeline.py` is a modified version of `test_pipeline.py` from the deeprule repo.


## Constituent models and structure of the pipeline

The chart processing pipeline consists of 5 CNN models. The function of each model is breifly described below.

1. The chart category classifier and common data extractor - This model identifies the chart type and extracts data like chart title, Y axis range, etc.

2. One model for processing bar charts - This model is called if the chart classifier identifies a bar chart. It extracts the location of each bar and the value represented by it.

3. One model for processing pie charts - This model is called if the classifier identifies a pie chart. For each sector, it extracts the sector area (percentage) and the sector position.

4. Two models for processing line charts - These 2 model are called in sequence if the classifier identifies a line chart. It extracts the (x, y) coordinates of each point on the line. This information is very verbose and is hence condensed into peaks and dips on the line chart. These peaks and dips and returned along with their location.


## Structure of the code

- `pipeline.py` - Contains the code for the main pipeline. All models and post processing functions are called from here.
- `app.py` - The flask wrapper for the pipeline. Collects the input request and passes on the image to the `pipeline.py` for processing. The output json is also returned from here.
- `models/py_factory.py` - Holds the definition for the neural network class. Contains functions to load the models, test batches, etc.
- `models/<model-specific-files>` - Contains the definitions for each model (including the layers, forward pass, loss, etc)
- `post_processing/<type-specific-files>` - Under each category, it contains functions for post processing the model output to produce interpretable data.
- `pipeline_inference` - Contains the testing and inference functions for each model.
- `config` - The model configuration files are stored here.


## Running the docker container

The docker container can be run using following command:

```
docker run --gpus all --publish <port>:5000 <image-name> --mode <1/2/3> --empty_cache <True/False>
```

The below 2 options are availbale:

1. mode (int): The pipeline can operate in 3 modes, based on the GPU specifications and hardware constraints (the modes are explained below). [default: 1]
    
2. empty_cache (bool): Setting it to 'True' clears the cache and prevents PyTorch from holding on to the memory even after use. Using this option leads to low idle time GPU usage. [default: True]


### Explanation of modes

Multiple modes have been implemented to allow deployment on both low end and high end systems. In both modes, the chart-type classifier is always kept loaded, while the type specific models are loaded only when required. This ensures that the type specific models occupy GPU memory only when the request contains a chart of that category.

1. Mode 1: The type specific models reside as .pt or ,pkl files and are loaded from this when needed. They don't take up any RAM or GPU memory when not being used. However, loading models from these files is quite slow which increases the processing time.

2. Mode 2: The type specific models reside in the RAM when not being used. They are simply moved from the RAM to the GPU when needed. This is much faster than loading from .pth or .pkl files, but also consumes more RAM. There also seems to be a memory leak issue with this option, where the RAM usage keeps building up until everything is exhausted. This issue is yet to be fixed.

3. Mode 3 is used when GPU memory is not a contraint. This mode loads all the models permanently on the GPU, giving the fastest response time.
