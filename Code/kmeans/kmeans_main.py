import h5py
import numpy as np
import time
from sklearn.utils import shuffle
from sklearn.preprocessing import normalize
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

sarsmerscov_train = h5py.File('/gpfs/alpine/gen150/scratch/arjun2612/ORNL_Coding/Code/cvae/sars-mers-cov2_train.h5', 'r')
sarsmerscov_val = h5py.File('/gpfs/alpine/gen150/scratch/arjun2612/ORNL_Coding/Code/cvae/sars-mers-cov2_val.h5', 'r')
lt = list(open('/gpfs/alpine/gen150/scratch/arjun2612/ORNL_Coding/Code/label_train.txt', 'r'))
lv = list(open('/gpfs/alpine/gen150/scratch/arjun2612/ORNL_Coding/Code/label_val.txt', 'r')) # open all files

label_training = np.array([])
label_validation = np.array([])
        
train_size = 60000
val_size = 15000

for i in range(train_size):
    num = int(str(lt[i]).strip('\n'))
    label_training = np.append(label_training, num)

for j in range(val_size):
    num = int(str(lv[j]).strip('\n'))
    label_validation = np.append(label_validation, num)

trainset = np.array(sarsmerscov_train['contact_maps'][0:train_size]).astype(float) # 60000 x 24 x 24 x 1
valset = np.array(sarsmerscov_val['contact_maps'][0:val_size]).astype(float) # 15000 x 24 x 24 x 1

trainset, label_training = shuffle(trainset, label_training, random_state=0)
valset, label_validation = shuffle(valset, label_validation, random_state=0)

train_3D = np.tril(trainset[:, :, :, 0])
val_3D = np.tril(valset[:, :, :, 0])

lt = None
lv = None
sarsmerscov_train = None
sarsmerscov_val = None # garbage collection to free up memory

print(str(time.ctime()) + ": Successfully loaded all data sets!")
print(str(time.ctime()) + ": Implementing PCA Clustering...")
            
train_pca = np.reshape(train_3D, (train_3D.shape[0], -1))  # 60000 x 576
val_pca = np.reshape(val_3D, (val_3D.shape[0], -1))  # 15000 x 576

normalized_train_pca = normalize(train_pca, axis=1, norm='l1')
normalized_val_pca = normalize(val_pca, axis=1, norm='l1')

pca = PCA(n_components=2)  # 2 PCs
pca.fit(normalized_train_pca)
reduced_val = pca.transform(normalized_val_pca) # reduce dimensions of both sets
            
print(str(time.ctime()) + ": Finished PCA Clustering!")
print(str(time.ctime()) + ": Implementing KMeans Clustering...")

kmeans = KMeans(n_clusters=3, random_state=0)
kmeans.fit(train_pca)
labels_val = np.array(kmeans.predict(val_pca))
accuracy = (sum(labels_val == label_validation) / len(label_validation)) * 100
print('Accuracy: {}'.format(accuracy))

print(str(time.ctime()) + ": Finished KMeans Clustering!")

np.savez('plotting.npz', reslab=labels_val, lv=label_validation, redval=reduced_val)