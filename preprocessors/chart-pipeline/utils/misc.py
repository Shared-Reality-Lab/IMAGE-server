import psutil
import time

# Function to read CPU and GPU mem utilization
def check_status(step, methods):

    time.sleep(4)
    
    # Model status
    for model in methods:
        is_cuda = next(methods['{}'.format(model)][1].model.parameters()).is_cuda
        if is_cuda == True:
            print("[Step {}] {}: Cuda".format(step, model))
        elif is_cuda == False:
            print("[Step {}] {}: CPU".format(step, model))


