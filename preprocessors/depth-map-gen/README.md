<h1>Depth Estimation</h1>

This proprocessor will take any image as an input and output the estimated depth. The goal being that the model will allow for other preprocessors to associate depth
to other components of the image, such as objects, and provide another dimension to the sound renderings. 

The chosen model is AdelaiDepth: 

[https://github.com/aim-uofa/AdelaiDepth](url)

With the assiciated paper: 

[https://paperswithcode.com/paper/learning-to-recover-3d-scene-shape-from-a](url)


<h2>Model research and choices</h2>

Looking from among the best performing Monocular ML Depth Estimation algorithms from [https://paperswithcode.com/task/monocular-depth-estimation](url) I have settled on 4 candidates. All 4 candidates are from among the best currently available algorithms which meet the following criteria: 
   1. Perform purely Monocular depth estimation (ie. Requires no additional components)
   2. Provides pretrained weights
   3. Non-prohibitive licencing 

The 4 candidates can be found here: 

**Adelai Depth:**
[https://github.com/aim-uofa/AdelaiDepth](url)

**GCN Depth:**
[https://github.com/arminmasoumian/gcndepth](url)

**Boosted Midas:**
[https://github.com/compphoto/BoostingMonocularDepth](url)

**Boosted LeRes:**
[https://github.com/compphoto/BoostingMonocularDepth](url)

In order for the depth estimator to mesh well with IMAGE, it must be able to complete its task within a reasonable amount of time (less than 3 seconds ideally) while simultaneously not overconsume available resources. After running all of the algorithms on the majority of the IMAGE test graphics available, the general resource consumption and time performance can be seen below:

| Depth Estimator  | Time Per Image (sec) | RAM (GB) | GPU (GB) | 
| ------------- | ------------- |------------- |------------- |
| **Adelai Depth**  | **0.3** | **3.7** | **0.7** |
| GCN Depth  | 3  | 4.5 | 2.5 |
| Boosted Midas  | 62 | 5.8 | 10.3  |
| Boosted LeRes  | 47 | 5.2 | 7.3  |

Adelai Depth and GCN Depth perform within the time parameters required however the Adelai Depth estimator runs incredibly quickly while also consuming the least amount of resources. Visually, Adelai Depth also preforms well, picking up a good amount of detail in arbitrary scenes. The two boosted algorithms generate the crispest depth images however provided the amount of time and resources required that is to be expected. Based on visual inspection, GCN Depth performs the worst from among the candidates. 



![depthcomp_label2](https://user-images.githubusercontent.com/25232146/216503340-0898dccf-0a46-41ff-b773-0dc27219d63b.png)

Based on these observations, I will recommend Adelai Depth estimation algorithm to be used for IMAGE. 
