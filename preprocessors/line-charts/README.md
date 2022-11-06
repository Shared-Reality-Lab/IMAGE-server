# Line-charts Preprocessor
## The Line-charts preprocessor extracts useful information from the given graph. 
This preprocessor is used to extract further insights from the given input graph (in the highcharts format). The additional keys added to the data include:
*lowerPointsOnLeft: number of continous points lower than the current point, lying on the left side of current point
*higherPointsOnLeft: number of continous points higher than the current point, lying on the left side of current point
*lowerPointsOnRight: number of continous points lower than the current point, lying on the right side of current point
*higherPointsOnRight: number of continous points higher than the current point, lying on the right side of current point



*Note:* In order to facilitate further development of charts, we have done a brief literature survey of the existing charts models. The survey acts as a good starting point for creating different ML models. The survey can be found in the [wiki](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/Literature-Survey-for-charts) 
