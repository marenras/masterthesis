import numpy as np 
import h5py 
import matplotlib.pyplot as plt
import scipy.signal
import sys
from scipy.optimize import curve_fit
import scipy.stats
import matplotlib.transforms as mtransforms

class SpikeDetect:
    def __init__(self, data):
        self.data = data


def remove_elevation_gain(X, g, a, c, d, e):
    t, el, az = X
    return  g/np.sin(el*np.pi/180) + az*a + c + d*t + e*t**2


f = open('spikes.txt', 'r')
lines = f.readlines()
filename = lines[3].split()[0] #9
filename = 'comap-0006944-2019-07-17-174905.hd5'
#filename = 'comap-0007613-2019-09-10-183037.hd5'
#filename = 'comap-0011507-2020-02-21-174416.hd5'
#filename = 'comap-0011510-2020-02-21-200733.hd5'
#filename = 'comap-0011419-2020-02-12-182147.hd5'


month = filename[14:21]
obsid = int(filename[9:13])
print(obsid)

path = '/mn/stornext/d16/cmbco/comap/pathfinder/ovro/' + month + '/'

with h5py.File(path + filename, 'r') as hdf:
    tod       = np.array(hdf['spectrometer/band_average'])
    el        = np.array(hdf['spectrometer/pixel_pointing/pixel_el'][0])
    az        = np.array(hdf['spectrometer/pixel_pointing/pixel_az'][0])
    features  = np.array(hdf['spectrometer/features'])

    # Removing Tsys measurements     
    boolTsys = (features != 8192)
    indexTsys = np.where(boolTsys==False)[0]

    if len(indexTsys) > 0 and (np.max(indexTsys) - np.min(indexTsys)) > 5000:
        boolTsys[:np.min(indexTsys)] = False
        boolTsys[np.max(indexTsys):] = False

    tod       = tod[:,:,boolTsys]
    el        = el[boolTsys]
    az        = az[boolTsys]

    tod = tod[0,0]
    
    #plt.plot(tod)

    num_parts = 24
    part = int(len(el)/num_parts)

    t = np.arange(len(el))
    diff = np.zeros(len(el))
    temp = np.zeros(len(el))
    for i in range(num_parts):
        if i == num_parts-1:
            popt, pcov = curve_fit(remove_elevation_gain, (t[part*i:],el[part\
*i:], az[part*i:]), tod[part*i:])
            g = popt[0]
            a = popt[1]

            temp[part*i:] = g/np.sin(el[part*i:]*np.pi/180) + a*az[part*i:]
            diff[part*i:] = (tod[part*i-1] - temp[part*i-1]) - (tod[part*i]\
                                        - temp[part*i]) + diff[part*(i-1)]
            
        else:
            popt, pcov = curve_fit(remove_elevation_gain, (t[part*i:part*(i+1)],el[part\
                        *i:part*(i+1)], az[part*i:part*(i+1)]), tod[part*i:part*(i+1)])
            g = popt[0]
            a = popt[1]

            temp[part*i:part*(i+1)] = g/np.sin(el[part*i:part*(i+1)]*np.pi/180) + a*az[\
                                                                part*i:part*(i+1)]
            diff[part*i:part*(i+1)] = (tod[part*i-1] - temp[part*i-1]) - (tod[part*i]\
                                                - temp[part*i]) + diff[part*(i-1)]

    # Removing elevation gain                                                       
    tod = tod - temp + diff 
    tod = tod - np.mean(tod)


def highpass_filter(data, fc=0.1, b=0.08):
    """
    fc : cutoff frequency as a fraction of the sampling rate, (0, 0.5).
    b  : tramsition band as a fraction of the sampling rate, (0, 0.5).
    """

    N = int(np.ceil((4/b)))
    if not N % 2: N += 1  # Make sure that N is an odd number 
    n = np.arange(N)

    # Compute sinc filter
    h = np.sinc(2 * fc * (n - (N-1)/2))

    # Compute the Blackman window
    w = np.blackman(N)

    # Compute the windowed-sinc filter
    h = h * w
    h = h / np.sum(h)

    # Turn the low-pass filter into a high-pass filter through spectral inversion
    h = -h
    h[(N-1) // 2] += 1

    # Apply high-pass filter by convolving over the signal
    data = np.convolve(data, h, mode='same')

    return data 


def peakdetect(y, lag=5, threshold=10, influence=0):
    signal = np.zeros(len(y))
    y_filtered = np.copy(y)
    average = np.zeros(len(y))
    std = np.zeros(len(y))
    average[lag-1] = np.mean(y[:lag])
    std[lag-1] = np.std(y[:lag])

    for i in range(lag, len(y)):
        if np.abs(y[i] - average[i-1]) > threshold*std[i-1]:
                if y[i] > average[i-1]:
                    signal[i] = 1
                else:
                    signal[i] = -1
                y_filtered[i] = influence*y[i] + (1-influence)*y_filtered[i-1]
        else:
            signal[i] = 0
            y_filtered[i] = y[i]

        average[i] = np.mean(y_filtered[i-lag+1:i+1])
        std[i] = np.std(y_filtered[i-lag+1:i+1])

    peak_indices = np.nonzero(signal)[0]
    cut = []
    for i in range(1, len(peak_indices)):
        if (peak_indices[i] - peak_indices[i-1] > 1):
            cut.append(i)

    peak_indices = np.split(peak_indices, cut)
    peak_tops = []
    for i in range(len(peak_indices)):
        peak_tops.append(peak_indices[i][np.argmax(y[peak_indices[i]])])

    return peak_tops, signal


def gaussian(x, mu, sigma):
    return 1/(sigma*np.sqrt(2*np.pi)) * np.exp(-1/2 * ((x-mu)/sigma)**2)

fc = 0.001
b = 0.1

#plt.figure()
#plt.plot(tod)


tod_new = highpass_filter(tod, fc=fc, b=b)
peak_tops, signal = peakdetect(tod_new, lag=100, threshold=6, influence=0)


plt.plot(tod_new)
plt.plot(np.arange(len(tod_new))[peak_tops], tod_new[peak_tops], 'ro')
plt.show()

"""
x = np.linspace(-50, 50, 100)
cfs = [[1], gaussian(x, mu=0, sigma=1), gaussian(x, mu=0, sigma=2), gaussian(x, mu=0, sigma=5), gaussian(x, mu=0, sigma=10), np.array([0, 1, 1, 0]), np.array([0,1,2,1,0]), np.array([0,2,3,2,0])]


fig, ax = plt.subplots()
for i in range(len(cfs)):
    cs = scipy.signal.convolve(tod_new, cfs[i], mode='same')
    peaks = peakdetect(cs, lag=100, threshold=6, influence=0)
    
    peaks_bolean = (abs(peaks) > 0)
    x = np.linspace(0, len(cs), len(cs))

    ax = plt.subplot(2, 4, i+1)
    plt.plot(cs)
    trans = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
    plt.fill_between(x, 0, 1, where=peaks_bolean, alpha=0.5, color='red', transform=trans)
plt.show()

"""
"""
x = np.linspace(-50, 50, 100)
cfs = [gaussian(x, mu=0, sigma=1), gaussian(x, mu=0, sigma=2), gaussian(x, mu=0, sigma=5), gaussian(x, mu=0, sigma=10), np.array([0, 1, 1, 0]), np.array([0,1,2,1,0]), np.array([0,2,3,2,0])]


for i in range(len(cfs)):
    cfs[i] = cfs[i]/np.max(cfs[i])

for i in range(len(cfs)):
    plt.plot(cfs[i], label='%d' %(i+2))
plt.legend()
plt.show()


peaks = scipy.signal.find_peaks(tod, prominence=np.max(tod[0:60000])*2.5)
peak_heights = tod[peaks[0]]
noise_std = np.std(tod[0:60000])
sn = peak_heights/noise_std

print(sn)
#print('   %.2f          %.2f          %.2f         %.2f         %.2f' %(sn[0], sn[1], sn[2], sn[3], sn[4]))

x_tod = np.linspace(0, len(tod), len(tod))

plt.plot(x_tod, tod)
plt.plot(x_tod[peaks[0]], tod[peaks[0]], 'o')
plt.show()

factors = [1,4500,9000,2750]
i=2
for cf in cfs:
    #plt.plot(cf)
    #plt.show()

    cs = scipy.signal.convolve(tod, cf, mode='same')
    #peaks = scipy.signal.find_peaks(cs, prominence=np.max(cs[65000:90000])*2)
    peak_heights = cs[peaks[0]]
    std_noise = np.std(cs[0:60000])
    sn = peak_heights/std_noise
   
    #plt.plot(cs)
    #plt.show()
 
    #print('   %.2f          %.2f          %.2f         %.2f         %.2f' %(sn[0], sn[1], sn[2], sn[3], sn[4]))
    print(i, sn)
    i+=1
"""






"""


fcs = [0.001, 0.0005, 0.0001]
bs = [0.1, 0.5]


for fc in fcs:
    for b in bs:
        tod_new = highpass_filter(tod, fc=fc, b=b)
        peaks = scipy.signal.find_peaks(tod_new,  prominence=np.max(tod_new[25000:50000])*2.2)

        x = np.linspace(0, len(tod_new), len(tod_new))
        peak_heights = tod_new[peaks[0]]
        
        #print(peak_heights)
        if len(peak_heights) > 15:
            peak_heights = [0]
        noise_std = np.std(tod_new[25000:50000])
        sns = peak_heights/noise_std
        
        for sn in sns:
            print('fc = %.3f       b = %.3f        S/N = %.3f' %(fc, b, sn))
        print()
        
        plt.plot(x, tod_new)
        plt.plot(x[peaks[0]], tod_new[peaks[0]], 'o')
        plt.show()


print('Original tod')
print(np.max(tod[125200:125500]))
print(np.max(tod[125200:125500])/np.std(tod[6000:100000]))
print()

def gaussian(x, mu, sigma):
    return 1/(sigma*np.sqrt(2*np.pi)) * np.exp(-1/2 * ((x-mu)/sigma)**2)

x = np.linspace(0,len(tod), len(tod))

plt.figure()
plt.subplot(221)
plt.plot(tod)
#plt.plot(x[122139:122210], tod[122139:122210])
plt.title('Original tod')

print('Highpass filtered tod')
print(np.max(tod[125200:125500]))
print(np.max(tod[125200:125500])/np.std(tod[6000:100000]))
print()


#plt.figure(figsize=(4,3))
plt.subplot(222)
plt.plot(tod)
#plt.plot(x[122139:122210], tod[122139:122210])
plt.title('High-pass filtered tod')

x_cf = np.linspace(0, 2, 100)
cf = gaussian(x_cf, 1, 0.01)#0.04)
#cf = np.convolve(cf, sinc_func)

#plt.figure(figsize=(4,3))
plt.subplot(223)
plt.plot(cf)
plt.title('Convolving function')

#plt.figure(figsize=(4,3))
plt.subplot(224)
plt.plot(scipy.signal.convolve(tod, cf, mode='same'))
#plt.plot(x[122139:122210], scipy.signal.convolve(tod, cf, mode='same')[122139:122210])
plt.title('Result from convolution')
plt.tight_layout()
plt.show()

print('Convolved tod')
print(np.max(scipy.signal.convolve(tod, cf, mode='same')[125200:125500]))
print(np.max(scipy.signal.convolve(tod, cf, mode='same')[125200:125500])/np.std(tod[6000:100000]))






"""
