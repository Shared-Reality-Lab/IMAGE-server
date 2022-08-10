## For a given point at a index, the function returns the number of 
## contiguous points(on the left side of the point) lower than the point value 
def getLowerPointsOnLeft(index, point, series_data):
    count = 0
    if index == 0:
        return count
    for data_point in series_data[index-1::-1]:
        if data_point['y'] < point['y']:
            count +=1
        else:
            break
    return count

## For a given point at a index, the function returns the number of 
## contiguous points(on the left side of the point) higher than the point value 
def getHigherPointsOnLeft(index, point, series_data):
    count = 0
    if index == 0:
        return count
    for data_point in series_data[index-1::-1]:
        if data_point['y'] > point['y']:
            count +=1
        else:
            break
    return count

## For a given point at a index, the function returns the number of 
## contiguous points(on the right side of the point) lower than the point value 
def getLowerPointsOnRight(index, point, series_data):
    count = 0
    if index == len(series_data) - 1:
        return count
    for data_point in series_data[index+1:]:
        if data_point['y'] < point['y']:
            count +=1
        else:
            break
    return count

## For a given point at a index, the function returns the number of 
## contiguous points(on the right side of the point) higher than the point value 
def getHigherPointsOnRight(index, point, series_data):
    count = 0
    if index == len(series_data) - 1:
        return count
    for data_point in series_data[index+1:]:
        if data_point['y'] > point['y']:
            count += 1
        else:
            break
    return count