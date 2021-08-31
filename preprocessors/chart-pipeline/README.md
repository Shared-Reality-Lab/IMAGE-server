# Chart data extraction pipeline

This pipeline is based on the DeepRule paper:

- Link to [deeprule paper](https://openaccess.thecvf.com/content/WACV2021/papers/Luo_ChartOCR_Data_Extraction_From_Charts_Images_via_a_Deep_Hybrid_WACV_2021_paper.pdf) 
- Link to [deeprule repo](https://github.com/soap117/DeepRule)


## Constituent models and structure of the pipeline

The chart processing pipeline consists of 5 CNN models. The function of each model is breifly described below.

1. The chart category classifier and common data extractor - This model identifies the chart type and extracts data like chart title, Y axis range, etc.

2. One model for processing bar charts - This model is called if the chart classifier identifies a bar chart. It extracts the location of each bar and the value represented by it.

3. One model for processing pie charts - This model is called if the classifier identifies a pie chart. For each sector, it extracts the sector area (percentage) and the sector position.

4. Two models for processing line charts - These 2 model are called in sequence if the classifier identifies a line chart. It extracts the (x, y) coordinates of each point on the line. This information is very verbose and is hence condensed into peaks and dips on the line chart. These peaks and dips and returned along with their location.


## Structure of the code

- `cloud_server.py` - Contains the code for the main pipeline. All models and post processing functions are called from here.
- `app.py` - The flask wrapper for the pipeline. Collects the input request and passes on the image to the `cloud_server.py` for processing. The output json is also returned from here.
- `data/<model-specific-folders>` - Contains the state_dict for the 5 models. 
- `nnet/py_factory.py` - Holds the definition for the neural network class. Contains functions to load the models, test batches, etc.
- `models/<model-specific-files>` - Contains the definitions for each model (including the layers, forward pass, loss, etc)
- `RuleGroup/<type-specific-files>` - Under each category, it contains functions for post processing the model output to produce interpretable data.
- `Schemas` - Contains the json schemas for validation of the model response. These schemas are category-specific.
- `testfile` - Contains the testing and inference functions for each model.
- `config` - The model configuration files are stored here.


## Setup to run the pipeline

1. Make sure you have anaconda or miniconda installed. If not, follow the instruction on [this](https://docs.conda.io/en/latest/miniconda.html) link to install it.

2. Run the below command to create a conda environment from the `environment.yml` file.
    ```
    conda env create -f environment.yml
    ```

3. Activate the conda environment
    ```
    conda activate chartenv
    ```

4. Compiling corner pooling layers
    
    The C++ implementation of the corner pooling layers (taken from the CornerNet) need to be compiled on your machine. 
    ```
    cd <deeprule_directory>/models/py_utils/_cpools/
    python setup.py build_ext --inplace
    ```

5. The NMS code also needs to be compiled (taken from the Faster R-CNN and Soft-NMS)
    ```
    cd <deeprule_directory>/external/
    make
    ```

6. Run the below command to install the MS COCO APIs

    ```
    cd <deeprule_directory>/data
    git clone git@github.com:cocodataset/cocoapi.git coco
    cd <deeprule_directory>/data/coco/PythonAPI
    make
    ```

7. Download the trained models from [here](https://drive.google.com/file/d/1qtCLlzKm8mx7kQOV1criUbqcGnNh58Rr/view?usp=sharing). Extract the zip file and move the `data` folder to the `deeprule/` directory.


## Running the pipeline for inference

The below command sets up a flask server which can then be used for inference by sending an input chart image as a request.

```
python3 -m app --mode <1/2> --empty_cache <True/False>
```

The below 2 options are availbale:

1. mode (int): The pipeline can operate in 2 modes, based on the GPU specifications and hardware constraints (the modes are explained below).
    
2. empty_cache (bool): Setting it to 'True' clears the cache and prevents PyTorch from holding on to the memory even after use. Using this option leads to low idle time GPU usage.


### Explanation of modes

Multiple modes have been implemented to allow deployment on both low end and high end systems. In both modes, the chart-type classifier is always kept loaded, while the type specific models are loaded only when required. This ensures that the type specific models occupy GPU memory only when the request contains a chart of that category.

1. Mode 1: The type specific models reside as .pt or ,pkl files and are loaded from this when needed. They don't take up any RAM or GPU memory when not being used. However, loading models from these files is quite slow which increases the processing time.

2. Mode 2: The type specific models reside in the RAM when not being used. They are simply moved from the RAM to the GPU when needed. This is much faster than loading from .pth or .pkl files, but also consumes more RAM. There also seems to be a memory leak issue with this option, where the RAM usage keeps building up until everything is exhausted. This issue is yet to be fixed.
