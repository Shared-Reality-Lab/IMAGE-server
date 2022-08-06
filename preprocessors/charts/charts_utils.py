def getLowerPointsOnLeft(index, point, series_data):
    count = 0
    if index == 0:
        return count
    for data_point in series_data[index-1::-1]:
        if data_point['y'] < point['y']:
            count+=1
        else:
            break
    return count

def getHigherPointsOnLeft(index, point, series_data):
    count = 0
    if index == 0:
        return count
    for data_point in series_data[index-1::-1]:
        if data_point['y'] > point['y']:
            count+=1
        else:
            break 
    return count

def getLowerPointsOnRight(index, point, series_data):
    count = 0
    if index == len(series_data) - 1:
        return count
    for data_point in series_data[index+1:]:
        if data_point['y'] < point['y']:
            count+=1
        else:
            break
    return count

def getHigherPointsOnRight(index, point, series_data):
    count = 0
    if index == len(series_data) - 1:
        return count
    for data_point in series_data[index+1:]:
        if data_point['y'] > point['y']:
            count+=1
        else:
            break
    return count