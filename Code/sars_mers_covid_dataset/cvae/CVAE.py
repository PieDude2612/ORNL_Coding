import os, sys, h5py
import horovod.keras as hvd
import tensorflow as tf
import keras
from keras import backend as K
import math
import numpy as np
from data_gen import CVAEGenerator
# from keras.optimizers import RMSprop
#from tensorflow_large_model_support import LMS
#lms_callback = LMS()

tf.compat.v1.disable_eager_execution()

from vae_conv import conv_variational_autoencoder
# sys.path.append('/home/hm0/Research/molecules/molecules_git/build/lib')
# from molecules.ml.unsupervised import VAE
# from molecules.ml.unsupervised import EncoderConvolution2D
# from molecules.ml.unsupervised import DecoderConvolution2D
# from molecules.ml.unsupervised.callbacks import EmbeddingCallback 

# def CVAE(input_shape, hyper_dim=3): 
#     optimizer = RMSprop(lr=0.001, rho=0.9, epsilon=1e-08, decay=0.0)

#     encoder = EncoderConvolution2D(input_shape=input_shape)

#     encoder._get_final_conv_params()
#     num_conv_params = encoder.total_conv_params
#     encode_conv_shape = encoder.final_conv_shape

#     decoder = DecoderConvolution2D(output_shape=input_shape,
#                                    enc_conv_params=num_conv_params,
#                                    enc_conv_shape=encode_conv_shape)

#     cvae = VAE(input_shape=input_shape,
#                latent_dim=hyper_dim,
#                encoder=encoder,
#                decoder=decoder,
#                optimizer=optimizer) 
#     return cvae 

def autoenc(input_shape, latent_dim=3, lr=0.001): 
    image_size = input_shape[:-1]
    channels = input_shape[-1]
    conv_layers = 4
    feature_maps = [16,16,16,16]
    filter_shapes = [(3,3),(3,3),(3,3),(3,3)]
    strides = [(2,2),(3,3),(2,2),(1,1)]
    dense_layers = 1
    dense_neurons = [32]
    dense_dropouts = [0]

    feature_maps = feature_maps[0:conv_layers]
    filter_shapes = filter_shapes[0:conv_layers]
    strides = strides[0:conv_layers]
    autoencoder = conv_variational_autoencoder(image_size,channels,conv_layers,feature_maps,
               filter_shapes,strides,dense_layers,dense_neurons,dense_dropouts,latent_dim,lr=lr)
    autoencoder.model.summary()
    return autoencoder

def run_cvae(cm_file_train, cm_file_val,
             batch_size=32, hyper_dim=3, epochs=100): 
    hvd.init()

    gen_train = CVAEGenerator(cm_file_train, hvd_size=hvd.size(), batch_size=batch_size, shuffle=True)
    gen_val = CVAEGenerator(cm_file_val, hvd_size=hvd.size(), batch_size=batch_size, shuffle=True)
    input_shape = gen_train.get_shape()
    
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    config.gpu_options.visible_device_list = str(hvd.local_rank())
    K.set_session(tf.Session(config=config))

    #epochs = int(math.ceil(epochs / hvd.size()))

    #cvae = CVAE(input_shape[1:], hyper_dim, lr=0.001*hvd.size()) 
    cvae = CVAE(input_shape[1:], hyper_dim, lr=0.001) 
    cvae.optimizer = hvd.DistributedOptimizer(cvae.optimizer)
    cvae.model.compile(optimizer=cvae.optimizer, loss=cvae._vae_loss)

    model_weight = 'cvae_weight-{epoch}.h5'
    model_file = 'cvae_model-{epoch}.h5'
    loss_file = 'loss.npz'

    resume_from_epoch = 0
    for try_epoch in range(epochs, 0, -1):
        if os.path.exists(model_weight.format(epoch=try_epoch)):
            resume_from_epoch = try_epoch
            break
    resume_from_epoch = hvd.broadcast(resume_from_epoch, 0, name='resume_from_epoch')

    if resume_from_epoch > 0:
        cvae.model.load_weights(model_weight.format(epoch=resume_from_epoch))
    
    callbacks = [hvd.callbacks.BroadcastGlobalVariablesCallback(0),]
    #callbacks.append(lms_callback)
    if hvd.rank() == 0: 
        callbacks.append(cvae.history)
        #callbacks.append(keras.callbacks.TensorBoard('./logs'))
        #callbacks.append(keras.callbacks.ModelCheckpoint('./checkpoint-{epoch}.h5'))    

#     callback = EmbeddingCallback(cm_data_train, cvae)
    cvae.train(gen_train, validation_data=gen_val, 
               batch_size=batch_size, epochs=epochs, 
               initial_epoch=resume_from_epoch, callbacks=callbacks) 
    if hvd.rank() == 0:   
        cvae.model.save_weights(model_weight.format(epoch=epochs))
        cvae.save(model_file.format(epoch=epochs))
        losses = {'loss':[], 'val_loss':[]}
        if resume_from_epoch > 0:
            losses = np.load(loss_file)
        train_losses = np.concatenate([losses['loss'], cvae.history.losses])    
        val_losses = np.concatenate([losses['val_loss'], cvae.history.val_losses])    
        np.savez(loss_file, loss=train_losses, val_loss=val_losses)
 
    return cvae 
