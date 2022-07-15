import os
import urllib.request
import time
import zipfile
import os.path
import shutil


def cbk(a,b,c):  
    '''''Callback function 
    @a:Downloaded data block 
    @b:Block size 
    @c:Size of the remote file 
    '''  
    per = 100.0*a*b/c  
    if per > 100:  
        per = 100  
    print(f'{per:6.2f}')


def is_file_older_than_x_days(file, days=1): 
    file_time = os.path.getmtime(file) 
    # Check against 24 hours 
    return ((time.time() - file_time) / 3600 > 24*days)


def gtfs_download(dir,filename,background_activity):

    while True:

        if (not os.path.isdir(dir)) or (is_file_older_than_x_days(os.getcwd()+'/'+dir+'/'+'stops.txt', days=1)):

            print("*** Downloading updated GTFS file***")

            # create temporary directory if it does not exist
            os.makedirs('dir', exist_ok=True)

            # download MTA's supplemented GTFS
            urllib.request.urlretrieve('http://web.mta.info/developers/files/google_transit_supplemented.zip', os.getcwd()+'/'+filename)
            
            print("***GTFS file downloaded***")

            # unzip the downloaded file to the temporary directory
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                zip_ref.extractall(dir)

            # delete the downloaded file and the temporary directory containing it
            shutil.rmtree('dir', ignore_errors=True)

            ## If file exists, delete it ##
            if os.path.isfile(filename):
                os.remove(filename)
            else:    ## Show an error ##
                print("Error: %s file not found" % filename)

        if background_activity:
            # next check in 1 hour
            time.sleep(3600) # 3600 seconds = 1 hours.
