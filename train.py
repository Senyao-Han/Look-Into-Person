import argparse

import keras
import tensorflow as tf
from keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau

import migrate
from config import patience, epochs, num_train_samples, num_valid_samples, batch_size
from data_generator import train_gen, valid_gen
from model import build_encoder_decoder
from utils import sparse_cross_entropy

if __name__ == '__main__':
    # Parse arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--pretrained", help="path to save pretrained model files")
    args = vars(ap.parse_args())
    pretrained_path = args["pretrained"]
    checkpoint_models_path = 'models/'

    # Callbacks
    tensor_board = keras.callbacks.TensorBoard(log_dir='./logs', histogram_freq=0, write_graph=True, write_images=True)
    model_names = checkpoint_models_path + 'model.{epoch:02d}-{val_loss:.4f}.hdf5'
    model_checkpoint = ModelCheckpoint(model_names, monitor='val_loss', verbose=1, save_best_only=True)
    early_stop = EarlyStopping('val_loss', patience=patience)
    reduce_lr = ReduceLROnPlateau('val_loss', factor=0.1, patience=int(patience / 4), verbose=1)

    if pretrained_path is not None:
        model = build_encoder_decoder()
        model.load_weights(pretrained_path)
    else:
        model = build_encoder_decoder()
        migrate.migrate_model(model)

    sgd = keras.optimizers.SGD(lr=0.001, momentum=0.9, decay=0.0005, nesterov=True)
    decoder_target = tf.placeholder(dtype='int32', shape=(None, None, None))
    model.compile(optimizer=sgd, loss=sparse_cross_entropy, target_tensors=[decoder_target])

    print(model.summary())

    # Final callbacks
    callbacks = [tensor_board, model_checkpoint, early_stop, reduce_lr]

    # Start Fine-tuning
    model.fit_generator(train_gen(),
                        steps_per_epoch=num_train_samples // batch_size,
                        validation_data=valid_gen(),
                        validation_steps=num_valid_samples // batch_size,
                        epochs=epochs,
                        verbose=1,
                        callbacks=callbacks,
                        use_multiprocessing=True,
                        workers=4
                        )
