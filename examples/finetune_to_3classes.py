#!/usr/bin/env python
# -*- coding: utf-8 -*-
import keras

import keras_retinanet.losses
from keras_retinanet.models.jh_resnet import ResNet50RetinaNet
from keras_retinanet.preprocessing.pascal_voc import PascalVocGenerator
from keras_retinanet.utils.keras_version import check_keras_version
from keras.callbacks import ModelCheckpoint
import tensorflow as tf
from keras.backend.tensorflow_backend import set_session

# from preprocessing.image import ImageDataGenerator

from preprocess.MyImageGenerator import MyImageDataGenerator


def get_session():
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    return tf.Session(config=config)


def create_model(weights='imagenet'):
    image = keras.layers.Input((None, None, 3))
    return ResNet50RetinaNet(
        image,
        num_classes=10,
        weights=
        '/home/xiziwang/projects/retinanet/snapshots/resnet50_05-0.39389.h5')


if __name__ == '__main__':
    set_session(get_session())

    image_data_generator = MyImageDataGenerator(
        featurewise_center=False,
        samplewise_center=False,
        featurewise_std_normalization=False,
        samplewise_std_normalization=False,
        zca_whitening=False,
        # rotation_range=8.,
        # width_shift_range=0.1,
        # height_shift_range=0.1,
        # shear_range=0.3,
        # zoom_range=0.08,
        # horizontal_flip=True,
        rescale=1. / 255)

    check_keras_version()
    # optionally choose specific GPU
    # if args.gpu:
    # os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    # keras.backend.tensorflow_backend.set_session(get_session())

    # create the model
    print('Creating model, this may take a second...')

    model = create_model()

    D7_pool = model.get_layer('D7_pool').output
    Global_cls = keras.layers.Dense(
        3, activation='softmax', name='global_3cls')(D7_pool)

    new_model = keras.models.Model(inputs=model.inputs, outputs=[Global_cls])

    for layer in new_model.layers:
        layer.trainable = False

    train_layers = ['D6', 'D7', 'D7_pool', 'global_3cls']

    for trainable_layer in train_layers:
        new_model.get_layer(trainable_layer).trainable = True

    new_model.compile(
        loss={'global_3cls': 'categorical_crossentropy'},
        optimizer=keras.optimizers.adam(lr=0.0001))

    # print model summary
    print(new_model.summary())

    # train_datagen = ImageDataGenerator(rescale=1. / 255, horizontal_flip=True)
    # test_datagen = ImageDataGenerator(rescale=1. / 255)
    # train_generator = train_datagen.flow_from_directory(
    # '/data/common/database/EroticDataset/train',
    # target_size=(299, 299),
    # batch_size=16,
    # class_mode='categorical')
    # val_generator = test_datagen.flow_from_directory(
    # '/data/common/database/EroticDataset/val',
    # target_size=(299, 299),
    # batch_size=16,
    # class_mode='categorical')

    batch_size = 16
    is_ergodic_files = None
    balance = False
    train_label_file = '/home/xiziwang/tools/freezed/labeled_freezed_train.txt'
    val_label_file = '/home/xiziwang/tools/freezed/labeled_freezed_val.txt'
    train_gen = image_data_generator.flow_from_label_file(
        train_label_file,
        batch_size=batch_size,
        is_ergodic_files=is_ergodic_files,
        balance=balance)
    train_steps = train_gen.steps_per_epoch()
    val_gen = image_data_generator.flow_from_label_file(
        val_label_file,
        phase='val',
        batch_size=batch_size,
        is_ergodic_files=is_ergodic_files,
        balance=balance)
    val_steps = val_gen.steps_per_epoch()

    new_model.fit_generator(
        train_gen,
        steps_per_epoch=train_steps // 10,
        epochs=50,
        validation_data=val_gen,
        validation_steps=val_steps,
        callbacks=[
            keras.callbacks.ModelCheckpoint(
                '/data/users/xiziwang/tools/nsp/ResNet50snapshots/finetuned-resnet50_{epoch:02d}-{val_loss:.5f}.h5',
                monitor='val_loss',
                verbose=1,
                save_best_only=False)
        ])
    new_model.save_weights('finetuned-resnet.h5')
