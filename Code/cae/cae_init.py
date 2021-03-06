import numpy as np
import time, argparse
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras import Input, Model
from tensorflow.keras.layers import Conv2D, Conv3D, AveragePooling2D, AveragePooling3D, BatchNormalization, UpSampling2D, UpSampling3D, Flatten, Dense
from tensorflow import keras
import horovod.tensorflow.keras as hvd

args = argparse.ArgumentParser()
args.add_argument('--dataset', default='SARSMERSCOV2', type=str, help='type of data loading in')
args = args.parse_args()
datatype = args.dataset

hvd.init()
gpus = tf.config.experimental.list_physical_devices('GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)
tf.config.experimental.set_visible_devices(gpus[hvd.local_rank()], 'GPU')

def smc2_model():
    x = Input(shape=(24, 24, 1))  # 24 x 24 x 1

    # Encoder (avg pooling instead of max pooling)
    e_conv1 = Conv2D(8, (3, 3), activation='relu', padding='same')(x) # 24 x 24 x 8
    pool1 = AveragePooling2D((2, 2), padding='same')(e_conv1) # 12 x 12 x 8
    b_norm1 = BatchNormalization()(pool1)

    e_conv2 = Conv2D(16, (3, 3), activation='relu', padding='same')(b_norm1) # 12 x 12 x 16
    pool2 = AveragePooling2D((2, 2), padding='same')(e_conv2) # 6 x 6 x 16
    b_norm2 = BatchNormalization()(pool2)

    e_conv3 = Conv2D(32, (3, 3), activation='relu', padding='same')(b_norm2) # 6 x 6 x 32
    pool3 = AveragePooling2D((2, 2), padding='same')(e_conv3) # 3 x 3 x 32
    b_norm3 = BatchNormalization()(pool3)

    e_conv4 = Conv2D(64, (3, 3), activation='relu', padding='same')(b_norm3) # 3 x 3 x 64
    b_norm4 = BatchNormalization()(e_conv4)

    e_conv5 = Conv2D(128, (3, 3), activation='relu', padding='same')(b_norm4) # 3 x 3 x 128
    b_norm5 = BatchNormalization()(e_conv5)

    # Decoder
    d_conv1 = Conv2D(128, (3, 3), activation='relu', padding='same')(b_norm5) # 3 x 3 x 128
    up1 = UpSampling2D((2, 2))(d_conv1) # 6 x 6 x 128
    b_norm6 = BatchNormalization()(up1)

    d_conv2 = Conv2D(64, (3, 3), activation='relu', padding='same')(b_norm6) # 6 x 6 x 64
    up2 = UpSampling2D((2, 2))(d_conv2) # 12 x 12 x 64
    b_norm7 = BatchNormalization()(up2)

    d_conv3 = Conv2D(32, (3, 3), activation='relu', padding='same')(b_norm7) # 12 x 12 x 32
    up3 = UpSampling2D((2, 2))(d_conv3) # 24 x 24 x 32
    b_norm8 = BatchNormalization()(up3)

    d_conv4 = Conv2D(16, (3, 3), activation='relu', padding='same')(b_norm8) # 24 x 24 x 16
    b_norm9 = BatchNormalization()(d_conv4)

    d_conv5 = Conv2D(8, (3, 3), activation='relu', padding='same')(b_norm9) # 24 x 24 x 8
    b_norm10 = BatchNormalization()(d_conv5)

    d_conv6 = Conv2D(1, (1, 1), activation='relu', padding='same')(b_norm10) # 24 x 24 x 1
    b_norm11 = BatchNormalization()(d_conv6)

    f1 = Flatten()(b_norm11) # add a fully connected layer after just the autoencoder. 576 x 1
    r = Dense(3, activation='softmax')(f1) # 3 x 1

    model = Model(x, r) # compile full model
    return model

def hea_model():
    x = Input(shape=(40, 40, 40, 1))  # batch_size x 40 x 40 x 40 x 1

    # Encoder
    e_conv1 = Conv3D(8, (3, 3, 3), activation='relu', padding='same')(x) # 40 x 40 x 40 x 8
    pool1 = AveragePooling3D((2, 2, 2), padding='same')(e_conv1) # 20 x 20 x 20 x 8
    b_norm1 = BatchNormalization()(pool1)

    e_conv2 = Conv3D(16, (3, 3, 3), activation='relu', padding='same')(b_norm1) # 20 x 20 x 20 x 16
    pool2 = AveragePooling3D((2, 2, 2), padding='same')(e_conv2) # 10 x 10 x 10 x 16
    b_norm2 = BatchNormalization()(pool2)

    e_conv3 = Conv3D(32, (3, 3, 3), activation='relu', padding='same')(b_norm2) # 10 x 10 x 10 x 32
    pool3 = AveragePooling3D((2, 2, 2), padding='same')(e_conv3) # 5 x 5 x 5 x 32
    b_norm3 = BatchNormalization()(pool3)

    e_conv4 = Conv3D(64, (3, 3, 3), activation='relu', padding='same')(b_norm3) # 5 x 5 x 5 x 64
    b_norm4 = BatchNormalization()(e_conv4)

    e_conv5 = Conv3D(128, (3, 3, 3), activation='relu', padding='same')(b_norm4) # 5 x 5 x 5 x 128
    b_norm5 = BatchNormalization()(e_conv5)

    # Decoder
    d_conv1 = Conv3D(64, (3, 3, 3), activation='relu', padding='same')(b_norm5) # 5 x 5 x 5 x 64
    up1 = UpSampling3D((2, 2, 2))(d_conv1) # 10 x 10 x 10 x 64
    b_norm6 = BatchNormalization()(up1)

    d_conv2 = Conv3D(32, (3, 3, 3), activation='relu', padding='same')(b_norm6) # 10 x 10 x 10 x 32
    up2 = UpSampling3D((2, 2, 2))(d_conv2) # 20 x 20 x 20 x 32
    b_norm7 = BatchNormalization()(up2)

    d_conv3 = Conv3D(16, (3, 3, 3), activation='relu', padding='same')(b_norm7) # 20 x 20 x 20 x 16
    up3 = UpSampling3D((2, 2, 2))(d_conv3) # 40 x 40 x 40 x 16
    b_norm8 = BatchNormalization()(up3)

    d_conv4 = Conv3D(8, (3, 3, 3), activation='relu', padding='same')(b_norm8) # 40 x 40 x 40 x 8
    b_norm9 = BatchNormalization()(d_conv4)

    d_conv5 = Conv3D(1, (1, 1, 1), activation='relu', padding='same')(b_norm9) # 40 x 40 x 40 x 1
    b_norm10 = BatchNormalization()(d_conv5)

    f1 = Flatten()(b_norm10) # add a fully connected layer after just the autoencoder. 64000 x 1
    r = Dense(5, activation='softmax')(f1) # 5 x 1

    model = Model(x, r) # compile full model
    return model
    
print(str(time.ctime()) + ": Creating Classification Model...")

npzfile = None
classification_model = None
batch_step = 0
if datatype == 'SARSMERSCOV2':
    npzfile = np.load('/gpfs/alpine/gen150/scratch/arjun2612/ORNL_Coding/Code/sars_mers_cov2_dataset/smc2_dataset.npz')
    classification_model = smc2_model()
    batch_step = int(1200 / len(gpus))
else:
    npzfile = np.load('/gpfs/alpine/gen150/scratch/arjun2612/ORNL_Coding/Code/hea_dataset/hea_dataset.npz')
    classification_model = hea_model()
    batch_step = int(420 / len(gpus))
trainset = npzfile['train4D']
valset = npzfile['val4D']
lt_onehot = npzfile['ltoh']
lv_onehot = npzfile['lvoh']
label_validation = npzfile['labval']

opt = tf.keras.optimizers.Adam(0.001 * hvd.size())
opt = hvd.DistributedOptimizer(opt)
classification_model.compile(loss='categorical_crossentropy', optimizer=opt, metrics=['categorical_accuracy'])

print(str(time.ctime()) + ": Successfully created Classification Model")

print(str(time.ctime()) + ": Training Classification Model...")
model_start = time.time()

epochs = 10
# early_stop = EarlyStopping(monitor='categorical_accuracy', patience=5, restore_best_weights=True)
callbacks = [hvd.callbacks.BroadcastGlobalVariablesCallback(0)]

# if hvd.rank() == 0:
#     callbacks.append(tf.keras.callbacks.ModelCheckpoint('./best_checkpoint-{epoch}.h5', monitor='val_categorical_accuracy', mode='max', save_best_only=True))

classify_labels = classification_model.fit(trainset, lt_onehot, epochs=epochs, steps_per_epoch=batch_step, verbose=0, callbacks=callbacks)

print(str(time.ctime()) + ": Finished training!")

print(str(time.ctime()) + ": Predicting with Classification Model...")

predicted = classification_model.predict(valset)
predicted = np.argmax(np.round(predicted), axis=1)

print(str(time.ctime()) + ": Finished predictions!")
model_end = time.time()
model_diff = round(model_end - model_start, 2)
print('Total time for training and prediction: ' + str(model_diff) + ' seconds')

print(str(time.ctime()) + ": Evaluating Classification Model...")

test_eval = classification_model.evaluate(valset, lv_onehot)
print('Loss: {}'.format(test_eval[0]))
print('Accuracy: {}'.format(test_eval[1] * 100))

print(str(time.ctime()) + ": Finished evaluation!")

l = np.array([]).astype(int)
for i in range(len(lv_onehot)):
    l = np.append(l, np.argmax(lv_onehot[i]))
    
correct = np.where(predicted == l)[0]
incorrect = np.where(predicted != l)[0]
print("Number of Correct Classifications: " + str(len(correct)))
print("Number of Incorrect Classifications: " + str(len(incorrect)))

if datatype == 'SARSMERSCOV2':
    np.savez('smc2_plotting.npz', res=predicted, labval=label_validation)
elif datatype == 'HEA':
    np.savez('hea_plotting.npz', res=predicted, labval=label_validation)