import h5py
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import glob, os, os.path
import random
import julian
import datetime

#f = 'comap-0006296-2019-06-04-041226.hd5'
f = 'comap-0008974-2019-11-10-040750.hd5'

month = f[-21:-14]
path = '/mn/stornext/d16/cmbco/comap/pathfinder/ovro/' + month + '/'

with h5py.File(path + f, 'r') as hdf:
    obsid = f[9:13] 
    print('ObsID:', obsid)
    try:
        tod = np.array(hdf['spectrometer/band_average'])
        MJD = np.array(hdf['spectrometer/MJD'])
        feeds = np.array(hdf['spectrometer/feeds'])
    except:
        print('No band average')

    # Removing T-sys measurements                                                           
    try:
        features = np.array(hdf['spectrometer/features'])
    except:
        print('No features')

    boolTsys = (features != 8192)
    indexTsys = np.where(boolTsys==False)[0]

    if len(indexTsys) > 0 and (np.max(indexTsys) - np.min(indexTsys)) > 5000:
        boolTsys[:np.min(indexTsys)] = False
        boolTsys[np.max(indexTsys):] = False
    else:
        print('No Tsys measurements, or only one measurement.')

    try:
        tod = tod[:,:,boolTsys]
        MJD = MJD[boolTsys]
    except:
        print('Not corresponding length of boolTsys and number of samples.')


time = []
for i in range(len(MJD)):
    time.append(julian.from_jd(MJD[i], fmt='mjd'))

print(np.shape(MJD))
print(np.shape(tod))

fig = plt.figure(figsize=(7,3))
ax = fig.add_subplot(111)

"""
for i in range(np.shape(tod)[0]):
    if feeds[i] == 15:
        for j in range(4):
            plt.plot(time, tod[i][j])
"""

tod_new = np.nanmean(tod, axis=1)
#tod_new = np.nanmean(tod_new, axis=0)
#plt.plot(tod_new)
#plt.show()
#sys.exit()

for i in range(np.shape(tod_new)[0]):
    if feeds[i] == 20:
        pass
    else:
        plt.plot(time, tod_new[i])

hours = matplotlib.dates.MinuteLocator(interval = 10)
h_fmt = matplotlib.dates.DateFormatter('%H:%M:%S')
ax.xaxis.set_major_locator(hours)
ax.xaxis.set_major_formatter(h_fmt)
plt.grid()
plt.xlabel('UTC (hours)')
plt.ylabel('Power')
plt.title('ObsID: ' + obsid) #+ ', feed: 15 (weather)' )
fig.autofmt_xdate()
plt.tight_layout()
plt.savefig(obsid+'_weather.png')
plt.show()
