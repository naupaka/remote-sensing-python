
# coding: utf-8

#Check that you are using the correct version of Python (should be 3.4, otherwise gdal won't work)
import sys
sys.version
import numpy as np
import h5py
import gdal, osr
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

filename = sys.argv[1]
band_of_interest = sys.argv[2]
outfile_name = sys.argv[3]

if("--verbose" in sys.argv):
    DEBUG = True


# ## Read hdf5 file into Python
# 
# ```f = h5py.File('file.h5','r')``` reads in an h5 file to the variable f. If the h5 file is stored in a different directory, make sure to include the relative path to that directory (In this example, the path is ../data/SERC/hypserspectral)

# In[3]:

f = h5py.File(filename,'r') 

# ## Explore NEON AOP HDF5 Reflectance Files
# 
# We can look inside the HDF5 dataset with the ```h5py visititems``` function. The ```list_dataset``` function defined below displays all datasets stored in the hdf5 file and their locations within the hdf5 file:

# In[4]:

#list_dataset lists the names of datasets in an hdf5 file
def list_dataset(name,node):
    if isinstance(node, h5py.Dataset):
        print(name)

f.visititems(list_dataset)


# We can display the name, shape, and type of each of these datasets using the ```ls_dataset``` function defined below, which is also called with ```visititems```: 

# In[5]:

#ls_dataset displays the name, shape, and type of datasets in hdf5 file
def ls_dataset(name,node):
    if isinstance(node, h5py.Dataset):
        print(node)
    
f.visititems(ls_dataset)


# Now that we see the general structure of the hdf5 file, let's take a look at some of the information that is stored inside. Let's start by extracting the reflectance data, which is nested under SERC/Reflectance/Reflectance_Data.  

# In[6]:

serc_refl = f['SERC']['Reflectance']
print(serc_refl)


# The two members of the HDF5 group /SERC/Reflectance are *Metadata* and *Reflectance_Data*. Let's save the reflectance data as the variable serc_reflArray:

# In[7]:

serc_reflArray = serc_refl['Reflectance_Data']
print(serc_reflArray)


# We can extract the shape as follows: 

# In[8]:

refl_shape = serc_reflArray.shape
print('SERC Reflectance Data Dimensions:',refl_shape)


# This corresponds to (y,x,bands), where (x,y) are the dimensions of the reflectance array in pixels (1m x 1m). All NEON hyperspectral data contains 426 wavelength bands. Let's take a look at the wavelength values:

# In[9]:

#View wavelength information and values

wavelengths = serc_refl['Metadata']['Spectral_Data']['Wavelength']
print(wavelengths)
# print(wavelengths.value)
# Display min & max wavelengths
print('min wavelength:', np.amin(wavelengths),'nm')
print('max wavelength:', np.amax(wavelengths),'nm')

#show the band width 
print('band width =',(wavelengths.value[1]-wavelengths.value[0]),'nm')
print('band width =',(wavelengths.value[-1]-wavelengths.value[-2]),'nm')


# The wavelengths recorded range from 383.66 - 2511.94 nm, and each band covers a range of ~5 nm. Now let's extract spatial information, which is stored under SERC/Reflectance/Metadata/Coordinate_System/Map_Info:

# In[10]:

serc_mapInfo = serc_refl['Metadata']['Coordinate_System']['Map_Info']
print('SERC Map Info:\n',serc_mapInfo.value)


# **Notes:**
# - The 4th and 5th columns of map info signify the coordinates of the map origin, which refers to the upper-left corner of the image  (xMin, yMax). 
# - The letter **b** appears before UTM. This appears because the variable-length string data is stored in **b**inary format when it is written to the hdf5 file. Don't worry about it for now, as we will convert the numerical data we need in to floating point numbers. 
# 
# For more information on hdf5 strings, you can refer to: http://docs.h5py.org/en/latest/strings.html
# 
# Let's extract relevant information from the Map_Info metadata to define the spatial extent of this dataset:

# In[11]:

#First convert mapInfo to a string, and divide into separate strings using a comma seperator
mapInfo_string = str(serc_mapInfo.value) #convert to string
mapInfo_split = mapInfo_string.split(",") #split the strings using the separator "," 
print(mapInfo_split)


# Now we can extract the spatial information we need from the map info values, convert them to the appropriate data types (eg. float) and store it in a way that will enable us to access and apply it later: 

# In[12]:

#Extract the resolution & convert to floating decimal number
res = float(mapInfo_split[5]),float(mapInfo_split[6])
print('Resolution:',res)

#Extract the upper left-hand corner coordinates from mapInfo
xMin = float(mapInfo_split[3]) 
yMax = float(mapInfo_split[4])
#Calculate the xMax and yMin values from the dimensions
#xMax = left corner + (# of columns * resolution)
xMax = xMin + (refl_shape[1]*res[0])
yMin = yMax - (refl_shape[0]*res[1]) 

# print('xMin:',xMin) ; print('xMax:',xMax) 
# print('yMin:',yMin) ; print('yMax:',yMax) 
serc_ext = (xMin, xMax, yMin, yMax)
print('serc_ext:',serc_ext)

#Can also create a dictionary of extent:
serc_extDict = {}
serc_extDict['xMin'] = xMin
serc_extDict['xMax'] = xMax
serc_extDict['yMin'] = yMin
serc_extDict['yMax'] = yMax
print('serc_extDict:',serc_extDict)


# ## Extract a single band from the array

# In[13]:

b56 = serc_reflArray[:,:,55].astype(np.float)
print('b56 type:',type(b56))
print('b56 shape:',b56.shape)
print('Band 56 Reflectance:\n',b56)
# plt.hist(b56.flatten())


# ## Apply the scale factor and data ignore value
# 
# This array represents the unscaled reflectance for band 56. Recall from exploring the HDF5 value in HDFViewer that the Data_Ignore_Value=-9999, and the Scale_Factor=10000.0.
# 
# <p>
# <img src="hdfview_SERCrefl.png" style="width: 650px;"/>
# </p>
# 
# We can extract and apply the no data value and scale factor as follows:

# In[14]:

#View and apply scale factor and data ignore value
scaleFactor = serc_reflArray.attrs['Scale_Factor']
noDataValue = serc_reflArray.attrs['Data_Ignore_Value']
print('Scale Factor:',scaleFactor)
print('Data Ignore Value:',noDataValue)

b56[b56==int(noDataValue)]=np.nan
b56 = b56/scaleFactor
print('Cleaned Band 56 Reflectance:\n',b56)


# ## Plot histogram of reflectance data values

# In[15]:

plt.hist(b56[~np.isnan(b56)],50);
plt.title('Histogram of SERC Band 56 Reflectance')
plt.xlabel('Reflectance'); plt.ylabel('Frequency')

