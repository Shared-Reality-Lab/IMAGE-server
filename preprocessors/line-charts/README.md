# Line-charts Preprocessor
## The Line-charts preprocessor extracts useful information from the given graph. 
This preprocessor is used to extract further insights from the given input graph (in the highcharts format). The additional keys added to the data include:
*lowerPointsOnLeft: number of continous points lower than the current point, lying on the left side of current point
*higherPointsOnLeft: number of continous points higher than the current point, lying on the left side of current point
*lowerPointsOnRight: number of continous points lower than the current point, lying on the right side of current point
*higherPointsOnRight: number of continous points higher than the current point, lying on the right side of current point